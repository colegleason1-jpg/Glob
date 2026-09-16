# Glob — Plan

*Context infrastructure for AI coding agents. Shovels for the gold rush.*

---

## Thesis

Models are commoditizing; the bottleneck is context. Every agent session burns tokens and
time re-discovering the same codebase structure — grepping, reading files one at a time,
rebuilding a mental map that gets thrown away. That waste is real money and real latency.

Glob is the layer underneath the agents: a local-first codebase search engine exposed as an
MCP server. Plug it into Claude Code, Cursor, or any MCP client and ask
*"where is auth handled?"*, *"what touches pricing?"* — get precise, token-budgeted answers
with `file:line` citations in seconds.

Two principles carry over deliberately from the supply-chain engine:

1. **Provenance.** Every answer cites `file:line`. If Glob can't cite it, it says so.
   You cannot grep your way to the word "verified" — an AST fact and a fuzzy keyword match
   are labeled differently, just like `2 calibrated` vs `2 asserted`.
2. **Refusal over hallucination.** A thin evidence base returns "not enough signal",
   not a confident guess.

---

## What it is / what it is not

**Is:**
- A local CLI (`glob`) + MCP server (stdio) — zero config, nothing leaves the machine
- Hybrid search: ripgrep-speed keyword layer + tree-sitter symbol layer (Python first, TS/JS next)
- A repo map: entry points, top-level structure, dependency edges, hot files
- Token-budgeted: every tool returns ranked, truncated results sized for an agent's context

**Is not:**
- A chat product, an IDE, or a hosted SaaS (MVP)
- An embeddings/semantic-search engine by default (optional later; needs an API key, breaks
  the zero-config/privacy story, so it stays off by default)
- A git-intelligence tool (blame/history/PR analysis — later, separate surface)

---

## Product surface (MCP tools)

| Tool | Input | Returns |
|---|---|---|
| `glob_overview` | repo path | Repo map: structure, entry points, key modules, dep edges |
| `glob_search` | query, budget | Ranked hybrid results (keyword + symbols), cited snippets |
| `glob_find_symbol` | name | All definitions/references with `file:line` |
| `glob_trace` | symbol | Callers, callees, importers |

Four tools, stable schemas, boring on purpose. The agent-facing surface must never churn.

---

## Architecture

- **Runtime:** TypeScript on Bun. npm distribution, first-class MCP SDK, tree-sitter bindings mature.
- **Indexer pipeline:** file walk (gitignore-aware) → language detect → tree-sitter parse →
  symbol table + references → SQLite (`<repo>/.glob/index.db`, FTS5 for keyword layer).
- **Freshness:** mtime+hash invalidation; `glob index` incremental by default; optional git
  post-commit hook. Indexing is in-process and fast — no queue, no daemon needed for MVP.
- **Ranking:** symbol matches > exact string > fuzzy keyword; recency and file centrality
  (who references it) as boosters.
- **No cloud, no accounts, no telemetry** in MVP. Privacy story is free because it's true.

---

## Dogfooding

Corpus #1 is `colegleason1-jpg/supply-chain-resilience-engine` — a real two-layer codebase
(engine / app, ADRs, 672 tests) that I already know well. Corpus #2 is Glob itself.

The dogfood checklist (asked via an agent, answers verified by hand):

- "Where does provenance/audit hashing happen?" (expect `app/storage`, `scrcae/audit`)
- "What fits the elasticity and when does it refuse?" (expect `calibration/elasticity`)
- "What does `solve()` depend on and who calls it?" (expect `optimization/*`)
- "Where are resource capacities constrained?" (the merged resource family)

**Success metrics (M3 gate):**

- ≥95% citation accuracy on the checklist (human-verified)
- ≥40% fewer tokens to correct answer vs naive grep+read baseline
- Index time: scrcae (<100 files) <5s; a ~3–5k-file repo <30s

---

## Milestones

| Milestone | Scope | Exit criteria |
|---|---|---|
| **M0 — Spikes** (days) | tree-sitter + ripgrep-in-TS spike; index scrcae and Glob | Corpus #1 indexed; rough timing numbers on a larger clone |
| **M1 — Engine MVP** | Indexer + 4 query tools, CLI only | Dogfood checklist passes by hand; baseline token comparison recorded |
| **M2 — MCP server** | stdio MCP, config snippets for Claude Code/Cursor | "Works in Claude Code in 60 seconds" demo, one take |
| **M3 — Hard dogfood** | Use Glob-equipped agent for real work on scrcae and Glob | Metrics above met; numbers captured for the post |
| **M4 — Public beta** | npm publish, README+GIF, engineering post, Show HN | Post published with real numbers; HN launch |

---

## Track B — scrcae connector (side experiment, separate business)

The supply-chain engine gets a thin HTTP wrapper (solve / simulate / calibrate) hosted under
Glob tooling — `scrcae` imported as a **pinned dependency, never forked**, so the 672 tests
keep guarding the math upstream and the original repo stays untouched.

- **Architecture:** versioned JSON schema tied to `ENGINE_VERSION`; task queue for CBC
  subprocess runs; size bounds; stateless. Chat Johnson is User Zero (token treasury).
- **Pricing reality:** infra is ~$15–65/mo and irrelevant. List price: Sandbox $0–49,
  Pro $299–499, Enterprise $1,200+. First five customers are design partners at $0–300 —
  the true year-one cost is schema churn and the enterprise tax (security questionnaires,
  SOC 2, SLAs), not hosting.
- **Sequencing:** Glob is the main build; Track B is a fast-follow revenue experiment that
  reuses the same launch assets. Do not run both at full throttle at once.

---

## Go-to-market (ordered, not parallel)

1. **Engineering post** (the durable asset): "How supply-chain math routes my router's
   token budget" + Glob dogfood numbers. Written *after* M3 so every claim is measured.
2. **Show HN:** "Show HN: Glob — local-first codebase search for AI agents (MCP)" linking the post.
3. **npm + GitHub** with 60-second setup as the first thing a visitor sees.
4. **Discords** (OpenRouter, LangChain, MCP) for feedback loops only — not launch channels.
5. **Product Hunt** only after self-serve signup exists.

---

## Risks and kill criteria

- **Platforms absorb it.** Cursor/Anthropic build codebase search in. Hedge: tiny surface,
  client-agnostic, local-first (their built-ins won't be). If the wedge stalls, the symbol
  index still powers Track B and the post still lands.
- **Embeddings competitors** (Cody et al.). Differentiation: zero-config, citations, no cloud.
- **Kill criteria:** if M3 can't hit ≥40% token reduction at ≥95% citation accuracy, the
  agent-search wedge fails — stop, publish the post anyway as a negative result, redirect.

---

## M0 spike result (2026-09-16) — GO

- Stack: Bun + `web-tree-sitter` (WASM) + `tree-sitter-python` (WASM). The native
  `tree-sitter` binding failed on this sandbox (GLIBCXX_3.4.31); WASM sidesteps it and is
  portable everywhere — the right default anyway.
- Parse correctness verified on `calibration/elasticity.py`: 16 defs/classes extracted with
  correct line numbers (`calibrate_elasticity`, `refuse`, `FitQuality`, …).
- Walk: 109 tracked files, 80 Python — clean, gitignore-aware via `git ls-files`.
- **Timing: 80 files / 848 KB parsed in ~240 ms (~3 ms/file), zero parse errors.**
  Far under the <5 s M0 target; extrapolates to a 3–5k-file repo well under 30 s.
- Go/no-go: **GO**. Proceed to M1 engine (SQLite schema next, step 2.1 in TASKS.md).

## Market placement decision (2026-09-16)

The product route is **local-first MCP first, hosted API second**. The local tool maximizes
usability and keeps recurring backend cost at effectively zero: the developer's machine
indexes the repository, and no code leaves it. A paid team layer and optional HTTP API come
only after demand for shared indexes, CI reports, or orchestrator integration is demonstrated.
See [`MARKET_POSITION.md`](MARKET_POSITION.md) and [`DOGFOOD.md`](DOGFOOD.md).

Do not add auth, billing, queues, hosted embeddings, or a multi-tenant database to the MVP.
The next proof point is measured answer quality and token reduction, not more infrastructure.

## Open decisions (user)

1. **Name:** Glob — keep? (collision risk with shell globbing; it's also the joke)
2. **License:** MIT vs Apache-2.0 for the OSS core
3. **Embeddings:** if/when to add, and provider choice (deferred until there's demand)
4. **Track B timing:** after M2 lands, or fully parallel
