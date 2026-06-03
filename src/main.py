from __future__ import annotations

import json
import os
from typing import Any
from urllib.parse import urlencode
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


EXA_API_BASE_URL = "https://api.exa.ai"
APIFY_API_BASE_URL = os.getenv("APIFY_API_BASE_URL", "https://api.apify.com")


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

    search_type = actor_input.get("searchType", "auto")
    payload = {
        "query": query.strip(),
        "type": search_type,
        "numResults": actor_input.get("numResults", 10),
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


def _local_storage_dir() -> str:
    return os.getenv("APIFY_LOCAL_STORAGE_DIR") or os.path.join(os.getcwd(), "storage")


def _read_local_input() -> dict[str, Any]:
    key = os.getenv("ACTOR_INPUT_KEY") or os.getenv("APIFY_INPUT_KEY") or "INPUT"
    path = os.path.join(_local_storage_dir(), "key_value_stores", "default", f"{key}.json")
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as file:
        data = json.load(file)
    return data if isinstance(data, dict) else {}


def _apify_token_param() -> str:
    token = os.getenv("APIFY_TOKEN")
    if not token:
        raise ValueError("APIFY_TOKEN is required when running on the Apify platform.")
    return urlencode({"token": token})


def _read_cloud_input() -> dict[str, Any]:
    store_id = os.getenv("ACTOR_DEFAULT_KEY_VALUE_STORE_ID") or os.getenv("APIFY_DEFAULT_KEY_VALUE_STORE_ID")
    key = os.getenv("ACTOR_INPUT_KEY") or os.getenv("APIFY_INPUT_KEY") or "INPUT"
    if not store_id:
        return {}
    response = _request_json(
        f"{APIFY_API_BASE_URL}/v2/key-value-stores/{store_id}/records/{key}?{_apify_token_param()}",
    )
    return response if isinstance(response, dict) else {}


def _get_input() -> dict[str, Any]:
    if os.getenv("APIFY_IS_AT_HOME") == "1":
        return _read_cloud_input()
    return _read_local_input()


def _write_local_outputs(rows: list[dict[str, Any]], response: dict[str, Any], summary: dict[str, Any]) -> None:
    storage_dir = _local_storage_dir()
    dataset_dir = os.path.join(storage_dir, "datasets", "default")
    kvs_dir = os.path.join(storage_dir, "key_value_stores", "default")
    os.makedirs(dataset_dir, exist_ok=True)
    os.makedirs(kvs_dir, exist_ok=True)

    for index, row in enumerate(rows, start=1):
        with open(os.path.join(dataset_dir, f"{index:09d}.json"), "w", encoding="utf-8") as file:
            json.dump(row, file, ensure_ascii=False, indent=2)

    for key, value in {"OUTPUT": response, "SUMMARY": summary}.items():
        with open(os.path.join(kvs_dir, f"{key}.json"), "w", encoding="utf-8") as file:
            json.dump(value, file, ensure_ascii=False, indent=2)


def _write_cloud_outputs(rows: list[dict[str, Any]], response: dict[str, Any], summary: dict[str, Any]) -> None:
    dataset_id = os.getenv("ACTOR_DEFAULT_DATASET_ID") or os.getenv("APIFY_DEFAULT_DATASET_ID")
    store_id = os.getenv("ACTOR_DEFAULT_KEY_VALUE_STORE_ID") or os.getenv("APIFY_DEFAULT_KEY_VALUE_STORE_ID")
    token_param = _apify_token_param()

    if rows and dataset_id:
        _request_json(
            f"{APIFY_API_BASE_URL}/v2/datasets/{dataset_id}/items?{token_param}",
            method="POST",
            payload=rows,
        )

    if store_id:
        for key, value in {"OUTPUT": response, "SUMMARY": summary}.items():
            _request_json(
                f"{APIFY_API_BASE_URL}/v2/key-value-stores/{store_id}/records/{key}?{token_param}",
                method="PUT",
                payload=value,
            )


def _write_outputs(rows: list[dict[str, Any]], response: dict[str, Any], summary: dict[str, Any]) -> None:
    if os.getenv("APIFY_IS_AT_HOME") == "1":
        _write_cloud_outputs(rows, response, summary)
    else:
        _write_local_outputs(rows, response, summary)


def main() -> None:
    actor_input = _get_input()
    api_key = os.getenv("EXA_API_KEY")
    if not api_key:
        raise ValueError("EXA_API_KEY must be set as an Actor environment variable.")

    payload = _build_search_payload(actor_input)
    query = payload["query"]

    print("Calling Exa search endpoint")
    response = _call_exa(api_key, payload)
    rows = _normalize_search_rows(response, query)

    summary = {
        "operation": "search",
        "endpoint": "search",
        "requestId": response.get("requestId"),
        "resultCount": len(rows),
        "costDollars": response.get("costDollars"),
        "requestedSearchType": payload.get("type"),
        "resolvedSearchType": response.get("searchType"),
    }
    _write_outputs(rows, response, summary)
    print(f"Stored {len(rows)} normalized row(s)")


if __name__ == "__main__":
    main()
