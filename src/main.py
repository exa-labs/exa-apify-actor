from __future__ import annotations

import asyncio
import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from apify import Actor


EXA_API_BASE_URL = "https://api.exa.ai"
# Billing is a straight pass-through of Exa's own charge. Exa returns the exact
# cost of each request in `costDollars.total`, already reflecting its pricing
# (10 results included, per-result charges beyond 10, contents/summaries, and the
# $12/1k deep-search tier). We bill that amount in $0.00001 units, so the Apify
# pay-per-event price for CHARGE_EVENT_NAME must be set to $0.00001.
CHARGE_EVENT_NAME = "exa_api_cost"
CHARGE_UNIT_DOLLARS = 0.00001


def _cost_units(response: dict[str, Any]) -> int:
    """Exa's request cost, expressed as a count of CHARGE_UNIT_DOLLARS units."""
    cost = response.get("costDollars")
    total = cost.get("total") if isinstance(cost, dict) else cost
    try:
        total = float(total)
    except (TypeError, ValueError):
        total = 0.0
    return max(1, round(total / CHARGE_UNIT_DOLLARS))


def _compact_strings(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return [value.strip() for value in values if isinstance(value, str) and value.strip()]


def _non_empty_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) and value else {}


def _drop_empty(payload: dict[str, Any]) -> dict[str, Any]:
    clean: dict[str, Any] = {}
    for key, value in payload.items():
        if value is None or value == "" or value == [] or value == {}:
            continue
        clean[key] = value
    return clean


def _build_search_payload(actor_input: dict[str, Any]) -> dict[str, Any]:
    query = actor_input.get("query")
    if not isinstance(query, str) or not query.strip():
        raise ValueError("The 'query' input is required.")

    search_type = actor_input.get("searchType")
    payload = {
        "query": query.strip(),
        "type": search_type,
        "numResults": actor_input.get("numResults"),
        "includeDomains": _compact_strings(actor_input.get("includeDomains")),
        "excludeDomains": _compact_strings(actor_input.get("excludeDomains")),
        "contents": {"highlights": True},
    }
    if search_type == "deep":
        payload["additionalQueries"] = _compact_strings(actor_input.get("additionalQueries"))
        payload["systemPrompt"] = actor_input.get("systemPrompt")
        payload["outputSchema"] = _non_empty_dict(actor_input.get("outputSchema"))

    max_characters = actor_input.get("maxCharacters")
    if isinstance(max_characters, int) and max_characters > 0:
        payload["contents"]["highlights"] = {"maxCharacters": max_characters}

    extra_options = _non_empty_dict(actor_input.get("extraRequestOptions"))
    payload.update(extra_options)

    return _drop_empty(payload)


def _request_json(
    url: str,
    method: str = "GET",
    payload: Any | None = None,
    headers: dict[str, str] | None = None,
) -> dict[str, Any] | list[Any]:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "exa-apify-actor/0.1",
            **(headers or {}),
        },
        method=method,
    )

    with urlopen(request, timeout=180) as response:
        response_body = response.read().decode("utf-8")
        return json.loads(response_body) if response_body else {}


def _call_exa(api_key: str, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        response = _request_json(
            f"{EXA_API_BASE_URL}/search",
            method="POST",
            payload=payload,
            headers={"x-api-key": api_key},
        )
        if not isinstance(response, dict):
            raise RuntimeError("Exa API returned a non-object response.")
        return response
    except HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Exa API returned HTTP {error.code}: {body}") from error
    except URLError as error:
        raise RuntimeError(f"Could not reach Exa API: {error.reason}") from error


def _as_string(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    return None


def _normalize_search_rows(response: dict[str, Any], query: str) -> list[dict[str, Any]]:
    results = response.get("results")
    if not isinstance(results, list):
        results = []

    structured_output = response.get("output")
    rows = []
    for index, result in enumerate(results, start=1):
        raw_result = result if isinstance(result, dict) else {"value": result}
        rows.append(
            {
                "query": query,
                "rank": index,
                "title": _as_string(raw_result.get("title")),
                "url": _as_string(raw_result.get("url")),
                "id": _as_string(raw_result.get("id")),
                "publishedDate": _as_string(raw_result.get("publishedDate")),
                "author": _as_string(raw_result.get("author")),
                "image": _as_string(raw_result.get("image")),
                "favicon": _as_string(raw_result.get("favicon")),
                "highlights": raw_result.get("highlights") if isinstance(raw_result.get("highlights"), list) else None,
                "highlightScores": raw_result.get("highlightScores") if isinstance(raw_result.get("highlightScores"), list) else None,
                "score": raw_result.get("score") if isinstance(raw_result.get("score"), (int, float)) else None,
                "structuredOutput": structured_output,
                "rawResult": raw_result,
            }
        )

    if not rows and structured_output is not None:
        rows.append(
            {
                "query": query,
                "structuredOutput": structured_output,
                "rawResult": response,
            }
        )
    return rows


async def _write_outputs(rows: list[dict[str, Any]], response: dict[str, Any], summary: dict[str, Any]) -> None:
    if rows:
        await Actor.push_data(rows)

    await Actor.set_value("OUTPUT", response)
    await Actor.set_value("SUMMARY", summary)


async def main() -> None:
    async with Actor:
        actor_input = await Actor.get_input() or {}
        if not isinstance(actor_input, dict):
            raise ValueError("Actor input must be a JSON object.")

        api_key = os.getenv("EXA_API_KEY")
        if not api_key:
            raise ValueError("EXA_API_KEY must be set as an Actor environment variable.")

        payload = _build_search_payload(actor_input)
        query = payload["query"]

        Actor.log.info("Calling Exa search endpoint")
        response = await asyncio.to_thread(_call_exa, api_key, payload)
        charge = await Actor.charge(CHARGE_EVENT_NAME, count=_cost_units(response))
        rows = _normalize_search_rows(response, query)

        summary = {
            "operation": "search",
            "endpoint": "search",
            "requestId": response.get("requestId"),
            "resultCount": len(rows),
            "costDollars": response.get("costDollars"),
            "requestedSearchType": payload.get("type"),
            "resolvedSearchType": response.get("searchType"),
            "chargeEvent": {
                "eventName": CHARGE_EVENT_NAME,
                "chargedCount": charge.charged_count,
                "eventChargeLimitReached": charge.event_charge_limit_reached,
            },
        }
        await _write_outputs(rows, response, summary)
        Actor.log.info("Stored %s normalized row(s)", len(rows))


if __name__ == "__main__":
    asyncio.run(main())
