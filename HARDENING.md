# Glob — Hardening Pass

Date: 2026-09-16

## Checks completed

- `bun test`: **10 pass, 0 fail, 22 expectations**
- `bun tsc --noEmit`: **pass**
- `bun pm pack --dry-run`: **pass**; package contains only the five active runtime modules plus docs and metadata
- Corpus CLI smoke test: **80 files, 0 reindexed, 80 unchanged**
- Blank CLI search: returns `no matches`, does not enumerate the whole index
- Trace CLI output: returns explicit `citation=file:line` values
- MCP protocol harness: fragmented input, multiple messages, initialize, tool listing, search call, malformed JSON, invalid JSON-RPC version, unknown methods, and refusal responses all pass
- Independent MCP client smoke: **pass** against the real stdio process; overview, search citation, and trace citation verified on the corpus

## Bugs found and fixed

1. Blank symbol searches could match every symbol because SQL `instr(name, '')` is true.
2. Punctuation-only and malformed FTS queries could reach SQLite MATCH unsafely.
3. Search, symbol lookup, and trace limits were not bounded.
4. The CLI trace path used an older non-citation output format.
5. The symbol parser's nullable tree result was caught by typechecking.
6. The package previously included inactive experimental modules; the publish list now names
   only the active CLI/MCP/index modules.

## Not launch blockers, but still explicit risks

- Python references in the active MVP now come from tree-sitter AST identifiers/calls, so
  comments and strings are excluded. Imports are cited, but names are not yet resolved across
  modules; the alternate full call-graph modules remain outside the active CLI path.
- The MCP transport is intentionally dependency-free newline-delimited JSON-RPC. It now has
  protocol-conformance coverage, but compatibility with every MCP client still needs a real Claude Code/client test, but the
  independent client now proves the wire contract works end-to-end.
- M3's model-token reduction and citation-accuracy measurements remain open. No public launch
  claim should say those thresholds passed.
- The package is Bun-first and is not yet published to npm.
- Deterministic retrieval benchmark: all four expected citation sets found, with 98.6–99.5%
  reduction in retrieval-context proxy size versus sending every matching file. This is not
  model-token telemetry; see [`BENCHMARK.md`](BENCHMARK.md).
- Actual MCP-client tool A/B: **pass**, 4/4 citation sets found, with 97.9–99.2% retrieval
  reduction; see [`AB_RESULTS.md`](AB_RESULTS.md).

## Launch decision

**Hardening pass: green for continued private dogfooding. Not public-launch ready yet.**
The next high-value test is a real MCP client session plus the repeatable agent token/citation
A/B benchmark in [`AGENT_BENCHMARK.md`](AGENT_BENCHMARK.md), not more backend infrastructure.
The deterministic retrieval proxy is now in place but does not replace that test.
