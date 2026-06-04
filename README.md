# Exa Search + Contents

Use Exa Search on Apify to retrieve source-grounded web results with relevant highlighted content. This Actor wraps Exa's Search endpoint with `contents.highlights` enabled by default, giving you compact web search results that are easy to use in AI agents, RAG pipelines, research workflows, and data products.

## What is Exa Search + Contents?

Exa Search + Contents is an Apify Actor for running Exa web search and returning the most useful parts of each result: title, URL, metadata, highlights, highlight scores, and optional structured output.

Instead of returning full page text by default, the Actor returns highlighted excerpts from each result. This keeps outputs compact, source-grounded, and friendly for agents and downstream LLM workflows.

Use it when you need:

- Web search results with relevant page excerpts
- Source discovery for RAG and knowledge-base workflows
- AI agent search over the live web
- Market, company, news, or technical research
- Domain-filtered web search
- Deep research with structured JSON output

## Key features

- **Auto and Deep search**: use `auto` for fast general search, or `deep` for broader research and structured output.
- **Highlights by default**: every request asks Exa for highlighted content snippets.
- **Domain filters**: restrict results to trusted domains or exclude domains you do not want.
- **Highlight length control**: optionally cap highlight length with `maxCharacters`.
- **Deep structured output**: ask Exa to return JSON matching your schema.
- **Apify-native output**: results are saved to the default dataset and can be exported as JSON, CSV, Excel, XML, RSS, or HTML.
- **Agent-ready**: predictable input and output schemas make the Actor easier to call from agents and Apify MCP workflows.

## How it works

The Actor takes a search query, calls Exa Search, and stores normalized results in an Apify dataset.

Under the hood, a basic run calls Exa like this:

```json
{
  "query": "Latest research in LLM agents",
  "type": "auto",
  "numResults": 10,
  "contents": {
    "highlights": true
  }
}
```

The Actor also stores the full raw Exa response in the default key-value store as `OUTPUT`, and a compact run summary as `SUMMARY`.

## Input

The only required input is `query`.

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `query` | string | Yes | Natural-language search query. |
| `searchType` | string | No | Search depth. Use `auto` or `deep`. Defaults to `auto`. |
| `numResults` | integer | No | Maximum number of results. Defaults to `10`. |
| `includeDomains` | array | No | Only return results from these domains. |
| `excludeDomains` | array | No | Exclude results from these domains. |
| `maxCharacters` | integer | No | Maximum characters per highlight. Highlights are always returned. |
| `additionalQueries` | array | No | Deep-only query variations for broader research. |
| `systemPrompt` | string | No | Deep-only system prompt for structured output. |
| `outputSchema` | object | No | Deep-only JSON schema for structured output. |
| `extraRequestOptions` | object | No | Advanced Exa API fields to merge into the request payload. |

## Example inputs

### Basic Auto search

Use Auto search for most web search workflows.

```json
{
  "query": "Latest research in LLM agents",
  "searchType": "auto",
  "numResults": 5
}
```

### Search trusted domains

Use `includeDomains` when you want results only from specific sources.

```json
{
  "query": "Recent language agent benchmark papers",
  "searchType": "auto",
  "numResults": 5,
  "includeDomains": ["arxiv.org", "openreview.net"]
}
```

### Exclude unwanted domains

Use `excludeDomains` to remove sources that are not useful for your workflow.

```json
{
  "query": "Latest AI search API product launches",
  "searchType": "auto",
  "numResults": 5,
  "excludeDomains": ["youtube.com", "x.com", "twitter.com"],
  "maxCharacters": 300
}
```

### Deep search with structured output

Use Deep search when you want Exa to synthesize a structured answer in addition to returning source results.

```json
{
  "query": "Name two current themes in language agent research",
  "searchType": "deep",
  "numResults": 5,
  "additionalQueries": [
    "language agent research trends benchmarks tool use",
    "LLM agents planning memory tool use evaluation"
  ],
  "systemPrompt": "Return a compact answer with source URLs.",
  "outputSchema": {
    "type": "object",
    "properties": {
      "answer": {
        "type": "string"
      },
      "themes": {
        "type": "array",
        "items": {
          "type": "string"
        }
      },
      "sources": {
        "type": "array",
        "items": {
          "type": "string"
        }
      }
    },
    "required": ["answer", "themes", "sources"]
  }
}
```

Structured output is only sent to Exa when `searchType` is `deep`. If you include `systemPrompt` or `outputSchema` with Auto search, the Actor ignores them.

## Output

The results are saved to the default Apify dataset. Each dataset item represents one Exa result.

Example output item:

```json
{
  "query": "Latest research in LLM agents",
  "rank": 1,
  "title": "Learning to Learn-at-Test-Time: Language Agents with Learnable Adaptation Policies",
  "url": "https://arxiv.org/pdf/2604.00830",
  "id": "https://arxiv.org/pdf/2604.00830",
  "publishedDate": null,
  "author": null,
  "image": "https://arxiv.org/html/2604.00830v2/x1.png",
  "favicon": "https://arxiv.org/static/browse/0.3.4/images/icons/favicon-32x32.png",
  "highlights": [
    "Test-Time Learning (TTL) enables language agents to iteratively refine their performance through repeated interactions with the environment at inference time..."
  ],
  "highlightScores": [],
  "score": null,
  "structuredOutput": null,
  "rawResult": {
    "title": "Learning to Learn-at-Test-Time: Language Agents with Learnable Adaptation Policies",
    "url": "https://arxiv.org/pdf/2604.00830"
  }
}
```

When using Deep structured output, `structuredOutput` is attached to each result row and the full response is also available in the key-value store.

Example structured output:

```json
{
  "structuredOutput": {
    "content": {
      "answer": "Two current themes in language agent research are agent architectures and evaluation, and long-horizon tool use and orchestration.",
      "themes": [
        "Agent architectures and evaluation",
        "Long-horizon tool use and orchestration"
      ],
      "sources": [
        "https://arxiv.org/pdf/2601.12560",
        "https://arxiv.org/pdf/2603.22862v1"
      ]
    },
    "grounding": []
  }
}
```

## How to use Exa Search + Contents

1. Open the Actor in Apify Console.
2. Enter a search query.
3. Choose `Auto` or `Deep`.
4. Optionally add domain filters, highlight length, or Deep structured output settings.
5. Click **Start**.
6. Download results from the dataset or call the Actor via API.

## API usage

You can run the Actor from the Apify API and retrieve dataset items directly:

```bash
curl -X POST \
  "https://api.apify.com/v2/acts/exa-labs~exa-search-and-contents/run-sync-get-dataset-items?token=YOUR_APIFY_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Latest research in LLM agents",
    "searchType": "auto",
    "numResults": 5
  }'
```

The API response is an array of dataset rows.

## Using this Actor with AI agents

This Actor is designed to be useful as an agent tool. Agents can provide a query and receive compact, highlighted web results with predictable fields.

Use Auto search when the agent needs fast source discovery. Use Deep search when the agent needs broader research or a structured JSON answer with grounding.

Because the Actor has explicit input, dataset, and output schemas, it can be easier for agents to inspect, call, and reason about through Apify APIs and MCP integrations.

## When should I use Auto vs Deep?

Use **Auto** for:

- General web search
- Source discovery
- Faster, cheaper runs
- Domain-filtered lookup
- Agent workflows that need result snippets

Use **Deep** for:

- Broader research questions
- Query expansion through `additionalQueries`
- Structured JSON output
- Evidence-backed summaries
- Workflows where recall matters more than latency

## FAQ

### Does this return full page text?

No. This Actor returns Exa highlights by default rather than full page text. Highlights are compact excerpts selected for relevance to the query.

### Can I limit highlight length?

Yes. Set `maxCharacters` to cap the length of each returned highlight.

### Can I use structured output with Auto search?

No. Structured output is Deep-only in this Actor. `systemPrompt`, `outputSchema`, and `additionalQueries` are only sent to Exa when `searchType` is `deep`.

### Where are results stored?

Normalized result rows are stored in the default Apify dataset. The full raw Exa response is stored in the default key-value store as `OUTPUT`, and a compact run summary is stored as `SUMMARY`.

### Do users need to provide an Exa API key?

No. This Actor is configured for managed Exa API access. Set `EXA_API_KEY` as an Actor environment variable or secret in Apify.

## Local development

Set `EXA_API_KEY` in the environment and run:

```bash
apify run --input '{
  "query": "Latest research in LLM agents",
  "searchType": "auto",
  "numResults": 3
}'
```

Validate schemas with:

```bash
apify validate-schema
```
