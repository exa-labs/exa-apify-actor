# Exa Search + Contents

Use Exa Search on Apify to retrieve source-grounded web results with highlights. The Actor wraps Exa's Search endpoint with `contents.highlights` enabled by default, giving compact results for agents, RAG, research, and data products.

## What it does

- Runs Exa Search from a natural-language query
- Supports `auto` and `deep` search
- Returns titles, URLs, metadata, highlights, and scores
- Supports include/exclude domain filters
- Lets you cap highlight length with `maxCharacters`
- Supports Deep-only structured JSON output
- Stores normalized rows in the Apify dataset
- Stores the full Exa response as `OUTPUT`

## Input

Required: `query`.

Optional: `searchType` (`auto` or `deep`, default `auto`), `numResults`, `includeDomains`, `excludeDomains`, `maxCharacters`, and `extraRequestOptions`.

Deep-only: `additionalQueries`, `systemPrompt`, `outputSchema`.

## Example

```json
{
  "query": "Latest research in LLM agents",
  "searchType": "auto",
  "numResults": 5,
  "includeDomains": ["arxiv.org", "openreview.net"]
}
```

## Deep structured output example

```json
{
  "query": "Name two current themes in language agent research",
  "searchType": "deep",
  "systemPrompt": "Return a compact answer with source URLs.",
  "outputSchema": {
    "type": "object",
    "properties": {
      "answer": { "type": "string" },
      "sources": { "type": "array", "items": { "type": "string" } }
    },
    "required": ["answer", "sources"]
  }
}
```

## Output

Each dataset row is one Exa result:

```json
{
  "rank": 1,
  "title": "Example result",
  "url": "https://example.com",
  "highlights": ["Relevant excerpt..."],
  "highlightScores": [0.92],
  "structuredOutput": null
}
```

For Deep structured output, `structuredOutput` is attached to result rows. The raw response is stored as `OUTPUT`; run metadata is stored as `SUMMARY`.

This Actor uses managed Exa API access. Set `EXA_API_KEY` as an Apify environment variable or secret.
