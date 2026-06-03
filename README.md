# Exa Search + Contents

Search the web with Exa and return highlighted excerpts from each result. This Actor uses Exa's Search endpoint with `contents.highlights: true` by default, so results are compact, source-grounded, and easy for agents to consume.

## What it does

- Runs Exa Search for a natural-language query.
- Supports Auto and Deep search.
- Returns highlights and highlight scores for each result.
- Supports include/exclude domain filters.
- Optionally returns Exa's combined context string with a character cap.
- Optionally requests structured output from Exa when using Deep search.
- Pushes normalized rows to the default dataset.
- Stores the full raw Exa API response in the default key-value store as `OUTPUT`.
- Stores a compact run summary as `SUMMARY`.

## Authentication

This Actor uses a managed Exa API key. Set `EXA_API_KEY` as an Actor environment variable or secret in Apify.

## Example input

```json
{
  "query": "Latest research in LLM agents",
  "searchType": "auto",
  "numResults": 10,
  "includeDomains": ["arxiv.org", "openreview.net"],
  "excludeDomains": ["youtube.com"]
}
```

## Deep search with structured output

```json
{
  "query": "Best evidence on enterprise adoption of AI coding agents",
  "searchType": "deep",
  "numResults": 10,
  "additionalQueries": [
    "AI coding agents enterprise adoption case studies",
    "AI developer tools productivity studies enterprise"
  ],
  "systemPrompt": "Return a concise evidence-backed answer with cited source URLs.",
  "outputSchema": {
    "type": "object",
    "properties": {
      "answer": {
        "type": "string"
      },
      "sources": {
        "type": "array",
        "items": {
          "type": "string"
        }
      }
    },
    "required": ["answer", "sources"]
  }
}
```

## Output

The default dataset contains one normalized row per result. The main fields are:

- `rank`
- `title`
- `url`
- `publishedDate`
- `author`
- `highlights`
- `highlightScores`
- `score`
- `structuredOutput`
- `context`
- `rawResult`

The full response is also available at `OUTPUT` in the default key-value store.

## Local development

Install the Apify CLI, then run:

```bash
apify run
```

For local runs, place test input at:

```text
storage/key_value_stores/default/INPUT.json
```

Example local input:

```json
{
  "query": "Latest research in LLM agents",
  "searchType": "auto",
  "numResults": 3
}
```

Set `EXA_API_KEY` in the environment before running locally.

## Publishing checklist

- Confirm product strategy and billing model for managed Exa API usage.
- Test Auto and Deep with Apify-provisioned credits.
- Validate input and output schemas with `apify validate-schema`.
- Run locally with `apify run`.
- Deploy with `apify push`.
- Run on Apify Console and inspect dataset, `OUTPUT`, and `SUMMARY`.
