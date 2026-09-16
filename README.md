# Glob

*Context infrastructure for AI coding agents. A local-first shovel for the gold rush.*

> **Status: working local MVP.** Glob indexes a repository, searches symbols and file contents,
> and exposes the same cited results through a stdio MCP server. It is not hosted yet, by design.

## Why Glob

Models are commoditizing; context is the bottleneck. Every agent session burns tokens and time
re-discovering the same codebase structure. Glob gives Claude Code, Cursor, or any MCP client a
local repository map and precise answers with `file:line` citations.

Glob borrows two ideas from its dogfood corpus, the supply-chain resilience engine:

1. **Provenance.** Every result identifies its file, line, evidence source, and ranking score.
   AST-derived symbol evidence and fuzzy keyword evidence are labeled differently.
2. **Refusal over hallucination.** No result is returned when the index has no signal. Glob
   says `not enough signal` instead of inventing an answer.

## Try it in 60 seconds

Glob currently runs from a checkout and requires Bun:

```bash
bun install
bun run src/index.ts index /path/to/your/repo
bun run src/index.ts search /path/to/your/repo "pricing"
```

Example output:

```text
citation=src/pricing.py:42  source=symbol  kind=def  name=calculate_price  score=3
```

The index lives at `/path/to/your/repo/.glob/index.db`. Re-run the index command after code
changes; unchanged files are skipped. Nothing is uploaded.

## Connect an agent with MCP

Add this to your MCP configuration, replacing the path with the Glob checkout path:

```json
{
  "mcpServers": {
    "glob": {
      "command": "bun",
      "args": ["run", "/absolute/path/to/glob/src/mcp.ts"]
    }
  }
}
```

Before the first query, index the target repository once:

```bash
bun run src/index.ts index /path/to/your/repo
```

The stdio server exposes four tools:

- `glob_overview` — indexed file, symbol, and reference counts
- `glob_search` — hybrid symbol + full-text search
- `glob_find_symbol` — definition lookup with citations
- `glob_trace` — lightweight reference lookup

MCP search responses are structured with `citation`, `source` (`symbol` or `keyword`), `kind`,
`name`, and `score` fields. The server needs no account or API key and sends no repository data
to Glob.

## What it is not

Glob is not a chat product, IDE, hosted SaaS, or embeddings service. The MVP is intentionally
local and small: SQLite + FTS5 for storage, tree-sitter WASM for Python symbols, and Bun for
the runtime. TypeScript/JavaScript parsing and richer AST call graphs come later.

## Development

```bash
bun install
bun test
bun run src/index.ts index corpus/supply-chain-resilience-engine
```

The test suite covers parsing, references, incremental storage, symbol search, FTS search,
tracing, refusal behavior, and the MCP transport.

## Roadmap

See [`PLAN.md`](PLAN.md) for the thesis, architecture, metrics, and market placement.The next proof point is measured answer quality and token reduction — not a hosted backend.
The reproducible A/B protocol is in [`AGENT_BENCHMARK.md`](AGENT_BENCHMARK.md).

| Milestone | Status |
|---|---|
| M0 — parser and walk spikes | Complete |
| M1 — local indexing and search engine | Complete |
| M2 — stdio MCP server | Complete |
| M3 — first dogfood run | Complete with measurement gate still open |
| M4 — public beta | Packaging underway; launch assets next |

Dogfood corpus: [supply-chain-resilience-engine](https://github.com/colegleason1-jpg/supply-chain-resilience-engine)
— a real two-layer codebase whose philosophy Glob borrows: separate what was measured from
what was asserted, and refuse when the evidence is thin.
