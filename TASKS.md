# Glob — Task Breakdown

Small steps. One step per working session unless trivial. Every step ends with a command
that passes — that's the definition of done. If a step is bigger than ~1 focused hour,
split it before starting.

## Ground rules

- No step starts until the previous one's "Done" command passes.
- Nothing gets fancy ahead of schedule: no abstractions, no extra deps, no config files
  beyond what the step names.
- Progress is visible here as checkboxes. Update this file at the end of every step.
- Plan and context live in [`PLAN.md`](PLAN.md).

## 0. Decisions (blocking, ~5 min, user)

- [x] D1: Keep the name **Glob**? (yes/no) — **kept**
- [x] D2: License for OSS core — **MIT** or **Apache-2.0**? — **MIT**
- [x] D3: Confirm corpus #1 = `supply-chain-resilience-engine` clone path. — **cloned to `corpus/supply-chain-resilience-engine`**

*No code until D1–D3 are answered.*

## 1. M0 — Spike: can we parse and index? (target: 1 session)

- [x] 1.1 deps installed (`web-tree-sitter` + `tree-sitter-python`, WASM; the native `tree-sitter` binding hit a GLIBCXX wall in this sandbox — see M0 note). Done = import works.
- [x] 1.2 `scratch/parse.ts` prints defs for `calibration/elasticity.py` — 16 defs incl. `calibrate_elasticity`, `refuse`, `FitQuality`. Done.
- [x] 1.3 `scratch/walk.ts` — 109 files (80 py), no junk dirs. Done.
- [x] 1.4 `scratch/timeit.ts` — **~240 ms for all 80 py files (~3 ms/file)**. Done.
- [x] **M0 exit:** timings + GO decision appended to PLAN.md.

## 2. M1 — Engine MVP (target: 1 session per step)

- [x] 2.1 `src/index.ts` CLI skeleton with one command: `glob index <path>`. Done = `bun run src/index.ts index ./corpus` prints "indexed N files". → **426 ms first pass, 80 files**
- [x] 2.2 SQLite schema + write path: `files`, `symbols` tables (refs deferred to 2.5 — no consumer yet). Done = `glob index` twice → second run incremental: **80 unchanged, 0 reindexed, 19 ms**; after `touch`: **1 reindexed**. 1,131 symbols in corpus.
- [x] 2.3 `glob search <root> <query>`: `instr()` over symbols, exact > prefix > substring ranking. Done = searching `refuse` returns exact hit at `elasticity.py:431` first; empty query refuses with "no matches".
  - Note: task said `fit_elasticity` — real symbol is `calibrate_elasticity` (`elasticity.py:404`); found correctly.
- [x] 2.4 Add FTS5 keyword layer over file contents; merge + rank (symbol > keyword). Done = `glob search "audit hash"` returns cited engine/app/test call sites; keyword hits are ranked below symbol hits and include line numbers.
- [x] 2.5 `glob find-symbol <root> <name>` and `glob trace <root> <name>` (refs table lookups). Done = `find-symbol calibrate_elasticity` returns `elasticity.py:404`; `trace solve` lists references across `app/` and engine callers. Tree-sitter-backed Python identifier refs are labeled `call` or `identifier`; cross-module symbol resolution is deferred.
- [x] 2.6 Tests: `tests/core.test.ts` with 6 focused tests (symbols, refs, exact search, FTS citation, trace, empty-result refusal). Done = `bun test` → **11 pass, 0 fail** after AST trace, hardening, and MCP protocol coverage.

## 3. M2 — MCP server (target: 2 steps)

- [x] 3.1 stdio MCP server exposing the 4 tools over the same internals. Done = `bun run src/mcp.ts` handles initialize, tools/list, and tools/call; smoke-tested in `tests/mcp.test.ts`.
- [x] 3.2 Claude Code config snippet + README "60-second" section. Done = README documents install, index, MCP config, and all four tools; smoke coverage is in `tests/mcp.test.ts`.

## 4. M3 — Dogfood (target: 1 session)

- [x] 4.1 Run the 4-question checklist using Glob tools; candidate citations and answer paths recorded in [`DOGFOOD.md`](DOGFOOD.md). Token comparison remains open because this CLI run does not yet instrument model-token usage.
- [x] 4.2 Go/adjust decision: **proceed with local-first MCP; improve citation-focused output and measure before hosting**. The ≥95% / ≥40% gate is not yet claimed as passed.
- [x] 4.3 Create the reproducible agent A/B protocol in [`AGENT_BENCHMARK.md`](AGENT_BENCHMARK.md). Done = four exact tasks, baseline/Glob conditions, scoring rubric, and results template exist; actual client runs remain pending.

| Question | Tokens (Glob) | Tokens (baseline) | Correct? |
|---|---|---|---|
| 1. provenance/audit hashing | | | |
| 2. elasticity fit + refusal | | | |
| 3. solve() deps + callers | | | |
| 4. resource capacity constraints | | | |

## 5. M4 — Public beta (target: 1 session per step)

- [x] 5.1 Package for npm/Bun (`bin`, files, engines). Done = `bun pm pack --dry-run` lists a focused 10-file, 34.14 KB package with `glob` and `glob-mcp` executables; full tests remain green.
- [x] 5.2 README polish + first-run demo. Done = README reflects the working local MVP, includes a runnable CLI example, MCP setup, tool descriptions, development commands, and an honest roadmap. A GIF is deferred until there is a stable interactive client flow.
- [x] 5.3 Engineering post draft (private). Done = [`ENGINEERING_POST.md`](ENGINEERING_POST.md) contains verified implementation/results and explicitly leaves the token-reduction gate open.
- [ ] 5.4 Publish + Show HN. **Blocked pending real MCP-client compatibility testing and the M3 token/citation benchmark.** See [`HARDENING.md`](HARDENING.md).

## Track B (parked — do not start before M2)

- [ ] B1: `scrcae` pinned as dep, thin FastAPI wrapper (solve/simulate/calibrate), schema versioned to `ENGINE_VERSION`.
- [ ] B2: Chat Johnson as User Zero; capture real request/response traces.
