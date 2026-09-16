# Glob — Market Placement

## Position

Glob is **local context infrastructure for AI coding agents**, not another hosted chat
assistant and not a generic code-search dashboard.

The wedge is simple: give an agent a precise repository map and cited answers without making
the developer upload their code or pay for a permanent backend. The product is a shovel: a
small tool that improves every agent a developer already uses.

## Product ladder

### 1. Free local MCP (the product now)

- Bun CLI + stdio MCP server
- Gitignore-aware incremental index
- Python symbol extraction first; TypeScript/JavaScript next
- Four stable tools: overview, search, find-symbol, trace
- No account, API key, hosted database, telemetry, or always-on server

This gives the broadest usability with essentially zero backend cost. The user's machine
pays the compute cost, and the privacy story is a real technical property rather than a
marketing claim.

### 2. Paid team layer (only after repeated demand)

Add collaboration around the local core, not a replacement for it:

- shared repository maps and saved query packs
- CI indexing and pull-request context reports
- organization policy controls and usage visibility
- optional hosted embeddings, disabled by default

The local index remains useful if the team layer disappears. This avoids turning an OSS
search utility into a cloud bill before product-market fit exists.

### 3. Optional HTTP API (fast follow, not the foundation)

Expose the same stable tool schemas over HTTP only when a real integration needs it:

- stateless `overview`, `search`, `find-symbol`, and `trace` requests
- versioned JSON schemas
- bounded repository and result sizes
- no repository persistence by default
- scale-to-zero/serverless or one small container before adding queues

The HTTP API is an integration surface for agent orchestrators and CI, not the main consumer
product. A hosted API should never be required for the local MCP experience.

## Cost discipline

- **MVP backend:** $0 recurring backend requirement.
- **Early hosted beta:** one small service or scale-to-zero deployment, with no database unless
  a customer explicitly needs shared indexes.
- **First paid feature:** team/CI coordination, because that is where a hosted control plane
  creates value. Do not charge for local search or add metered API pricing before usage and
  support costs are understood.
- **Operational guardrails:** request size limits, timeout budget, bounded result count, and
  explicit refusal when the index is missing or evidence is weak.

## Market message

> **Glob gives coding agents a cited map of your repository without sending your code away.**
>
> Install it in a minute. Keep the index local. Use the same MCP tools in any compatible
> agent. Upgrade only when your team needs shared context or CI automation.

## What we are deliberately not doing yet

- no hosted code ingestion
- no embeddings API dependency
- no auth or billing system
- no queue or multi-tenant database
- no generic AI chat UI
- no separate connector product competing with model routers

The next proof point is not infrastructure. It is measured improvement: fewer tokens and
faster correct answers on the supply-chain corpus, with citations that can be checked.
