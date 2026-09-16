# Glob — A/B Results

## Bottom line

**Decision: needs engineering fixes.** Not public-beta ready; private dogfooding can continue, but no
measurement claim in the current docs should be repeated until the items in §9 are done.

- Tests, typecheck-with-types, pack, and the independent MCP client smoke all pass; the MCP wire contract works.
- The committed tool-level A/B result (4/4) does **not** reproduce: the `solve callers` expectation is a comment
  line that the hardened AST extractor correctly refuses to index (3/4, `citation-failure`).
- A real model-level A/B was run: 8 fresh-context agent runs, same prompts, same commit, with per-call token
  telemetry taken from the API usage records. **The Glob condition used more context, not less**: 1.9× total
  input tokens, 1.1× new input tokens, 1.6× wall-clock and 2.2× tool calls in aggregate, and more total input
  tokens on every one of the four tasks.
- Answer quality was similar in both conditions: citation accuracy 100% (baseline) vs 98.5% (Glob), rubric
  completeness 81.8% vs 78.2%, zero critical hallucinations in either arm. Glob did not buy accuracy either.
- Two retrieval defects were found in Glob itself: `glob_trace` silently caps at 50 references (dropping 47 of
  97 for `solve`), and keyword hits cite one line while showing a snippet from another.

Date: 2026-09-16 (validation run). Supersedes the tool-level table previously in this file; the previous
numbers are reproduced below with the one discrepancy called out.

Glob commit under test: `9bdc113266a485fa36fad19a2794d26344e13119` (Build Glob local MCP codebase context MVP).
Corpus: `corpus/supply-chain-resilience-engine` = GitHub `colegleason1-jpg/supply-chain-resilience-engine` at
commit `6f0fc8b44336324534b6f522e9a916ff6e04068f` (80 Python files, 1,131 symbols, 32,082 references indexed).
Every line number that `AGENT_BENCHMARK.md`, `DOGFOOD.md` and `benchmarks/ab-tool.ts` expect was checked
against this commit; all of them resolve, so this is the same pinned checkout the documents describe.

Runtime: Bun 1.3.11, Node 22.22.2, 4 CPUs, clean `bun install` from `bun.lock`. Nothing in `src/`, `tests/`,
`benchmarks/` or `scripts/` was modified, and nothing was committed, pushed or published.

## 1. Commands run

| Step | Command | Result |
|---|---|---|
| Install | `bun install` | 4 packages, ok |
| Index | `bun run src/index.ts index corpus/supply-chain-resilience-engine` | 80 files, 80 reindexed, 5,379 ms; re-run: 0 reindexed, 80 unchanged, 30 ms |
| Tests | `bun test` | **11 pass, 0 fail, 24 expect() calls** (2 files) |
| Typecheck (as committed) | `bunx tsc --noEmit` (TypeScript 6.0.2) | **fails: TS2688 Cannot find type definition file for 'bun'** — neither `@types/bun` nor `bun-types` is declared in `package.json` |
| Typecheck (types supplied) | `tsc --noEmit -p tsconfig.json --typeRoots <scratch>/@types` (TypeScript 5.9.3, `@types/bun` 1.4.2 installed outside the repo) | pass for `src/**` |
| Typecheck, extended | same options over `tests/*.ts benchmarks/*.ts scripts/*.ts src/*.ts` | `tests/` and `benchmarks/` pass; `scripts/mcp-client-smoke.ts` has 5× TS1375 (top-level `await` in a file with no import/export). Bun runs it fine; tsc does not. Note `tsconfig.json` includes `test/**/*.ts` but the directory is `tests/`, so the project typecheck never covers the tests. |
| Pack | `bun pm pack --dry-run` | 10 files, 35.32 KB unpacked (package.json, LICENSE, 3 docs, 5 src modules) |
| MCP client smoke | `bun run smoke:mcp` | **pass**: initialize, 4 tools listed, overview 80 files / 1,131 symbols / 32,082 refs, search cites `elasticity.py:404`, trace cites `engine_client.py:47` |
| Dogfood benchmark | `bun run bench:dogfood` | runs; **3/4 expected citation sets found** (`solve callers` false, see §3) |
| MCP-backed A/B | `bun run bench:ab` | runs; **status `citation-failure`, 3/4** (`solve callers` false, see §3) |
| CLI refusal checks | blank and `!!!` searches | `no matches`, index not enumerated |
| CLI trace | `trace … solve` | `citation=file:line` lines, 50 rows |

## 2. Tool-level A/B (actual stdio MCP process, `benchmarks/ab-tool.ts`)

This is a retrieval-size comparison, not model telemetry: the baseline is every Python file containing the
query terms, approximate tokens are characters ÷ 4, and the Glob column is the byte size of the real MCP
`tools/call` response.

| Task | Tool / query | Baseline files | Baseline approx. tokens | Glob MCP approx. tokens | Retrieval reduction | Expected citations |
|---|---|---:|---:|---:|---:|---|
| Provenance | `glob_search provenance` | 25 | 87,893 | 900 | 99.0% | found |
| Calibration | `glob_search calibrate_elasticity` | 6 | 21,977 | 469 | 97.9% | found |
| Solve callers | `glob_trace solve` | 44 | 157,860 | 1,354 | 99.1% | **not found** (`app/adapters.py:725` missing) |
| Capacity | `glob_search capacity` | 8 | 51,357 | 601 | 98.8% | found |

Result: `citation-failure`, 3/4. The previously committed `AB_RESULTS.md`/`AB_RESULTS.json` (4/4 pass, solve
payload 1,329 tokens) does **not** reproduce from a clean index with the committed code. `app/adapters.py:725`
is a comment (`# Per-node market exposure is a solve-time overlay…`) and `adapters.py` contains no `solve`
identifier at all; the hardened AST-based reference extractor correctly excludes comments, so this expectation
can only have been met by an index built with an earlier keyword-based extractor. `src/store.ts` only wipes an
old index when the `content` or `refs` tables are empty, so a stale index built by older code survives a code
upgrade unchanged. The same applies to `DOGFOOD.md`'s `app/copilot.py:340` and `app/main.py:215`, which are a
docstring and a comment.

## 3. Tool-level findings on Glob itself (corpus commit 6f0fc8b)

1. **`glob_trace` truncates silently at 50.** The index holds 97 references to `solve` (82 calls) across 16
   files; the MCP tool has no `limit` argument, returns the first 50 ordered by path, and gives no truncation
   signal. For `solve` that drops every reference in `engine/tests/test_objective_units.py`, `test_parity.py`,
   `test_properties.py`, `test_resources.py` and `legacy/`. The CLI has the same cap.
2. **Keyword hits cite one line and show another.** For a keyword hit `searchSymbols` reports the first line in
   the file containing the term, but the snippet comes from SQLite's FTS `snippet()` over the whole file body.
   Example: `optimizer.py:471` is cited with the snippet `checks.append("resource_[capacity]")`, which is line
   773; `network.py:157` (a docstring line) is cited with the text of line 174. An agent that trusts the
   snippet will attach the wrong line.
3. **The benchmark rubric lines are partly derived from Glob's own output.** `network.py:157`, `optimizer.py:471`
   and `diagnostics.py:199` are exactly the first lines containing "capacity" in those files. Two of the three
   are real mechanism lines by luck; `network.py:157` is docstring text and was graded *not relevant evidence*
   by the independent ground-truth pass (§7).
4. **"Expected citation found" is a weak success test.** The single canned query `glob_search provenance`
   returns 20 hits of which 9 are test functions, reaches 5 of the 12 files in the verified provenance rubric,
   and never surfaces `engine/src/scrcae/audit.py`, where the hashing is actually created. The needle check
   `"provenance"` passes trivially. Coverage figures for all four tasks are in §7.
5. **Trace does not distinguish definitions from references.** `glob_trace solve` labels the `def solve` line
   (`optimizer.py:279`) and the import line (`engine_client.py:24`) as `identifier`, and also returns PuLP's
   `problem.solve(` (`optimizer.py:480`) and legacy `prob.solve(` calls, because tracing is by bare name.
6. **Index side effect.** Indexing writes `.glob/index.db` (3.9 MB here) inside the target repository and does
   not add it to that repository's `.gitignore`; the corpus shows `?? .glob/` afterwards.
7. Minor: `package.json` declares no `typescript`, `@types/bun` or `bun-types`, so `bun tsc --noEmit` as
   described in `HARDENING.md` cannot run from a clean checkout; `tsconfig.json` never covers `tests/`.

## 4. Model-level A/B — protocol actually used

`AGENT_BENCHMARK.md` was followed with these concrete choices, and two deviations that are stated plainly:

- **Fresh context per run.** Each of the 8 runs (4 tasks × 2 conditions) was a separate subagent with an empty
  conversation, the same model and settings, and the exact task wording from `AGENT_BENCHMARK.md`; the only
  text that differed between conditions was the tool-access preamble.
- **Condition A (baseline)** explored a separate clean checkout of the corpus at the same commit
  (`/home/user/colegleason1-jpg/supply-chain-resilience-engine`, no `.glob/` index, no Glob code nearby) with
  ordinary tools: file-pattern search, grep, file reads and shell (`ls`, `grep`, `sed`, `find`).
- **Condition B (Glob)** discovered code only through the four Glob MCP tools. *Deviation 1:* this session
  cannot register a new MCP server into a running Claude Code session, so each tool call went through a
  one-shot stdio client (`glob-mcp-call.ts`, kept outside the repo) that spawns the real `src/mcp.ts` server,
  sends `initialize` + `tools/call`, and prints the tool result verbatim. The agent invoked it via Bash and was
  allowed to open files only at locations Glob had cited, with a read window (as the protocol permits).
- *Deviation 2:* per-agent tool allow-lists could not be enforced by the harness, so discipline was enforced by
  instruction and **audited from the raw transcripts afterwards**: in the Glob arm 100% of Bash calls were the
  MCP client (61 of 61) and 100% of file reads (54 of 54) targeted a file a previous Glob result had cited; the
  baseline arm never touched the Glob index, client or repository. No violations in any of the 8 runs.
- **Telemetry is real.** Input, output, cache-creation and cache-read token counts are summed from the API
  `usage` records of every model call in each subagent's JSONL transcript; tool calls and wall-clock come from
  the same transcripts. Nothing was estimated. "New input tokens" = uncached input + cache-creation tokens (the
  context each run added); "total input tokens" additionally counts cache reads (what the model actually
  processed across all turns). Raw transcripts stay outside the repository.
- **Grading** (§6) used a ground-truth rubric per question built by an independent agent from the corpus alone,
  attacked by a completeness critic and a citation refuter, and synthesised into a final rubric; each answer was
  then graded by a citation checker and a rubric judge, and both grades were re-verified by an adversarial
  auditor whose final numbers are the ones reported. A deterministic script independently confirmed every cited
  file/line exists and every quoted line matches.

## 5. Model-level A/B — telemetry

### Model-level telemetry (fresh context per run, same model and settings, corpus commit 6f0fc8b)

| Task | Arm | Turns | Tool calls | New input tokens | Cache-read tokens | Total input tokens | Output tokens | Wall-clock s | Tool-result chars | Glob MCP calls | Glob payload chars |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Provenance | baseline | 27 | 16 | 116,374 | 1,106,024 | 1,222,398 | 2,222 | 90.9 | 54,223 | — | — |
| Provenance | glob | 46 | 33 | 156,577 | 1,821,841 | 1,978,418 | 2,526 | 161.2 | 42,463 | 19 | 11,403 |
| Calibration | baseline | 13 | 7 | 108,416 | 506,647 | 615,063 | 1,719 | 77.3 | 71,753 | — | — |
| Calibration | glob | 24 | 14 | 87,072 | 847,388 | 934,460 | 8,661 | 108.4 | 43,774 | 8 | 6,972 |
| Solve path | baseline | 30 | 17 | 111,997 | 1,148,657 | 1,260,654 | 5,050 | 102.5 | 42,604 | — | — |
| Solve path | glob | 35 | 24 | 122,853 | 1,439,388 | 1,562,241 | 3,509 | 103.3 | 48,346 | 7 | 17,888 |
| Capacity | baseline | 21 | 13 | 121,794 | 893,114 | 1,014,908 | 2,501 | 93.2 | 68,646 | — | — |
| Capacity | glob | 66 | 44 | 141,251 | 3,206,309 | 3,347,560 | 3,912 | 203.6 | 71,068 | 27 | 17,310 |
| **Total** | **baseline** | 91 | 53 | 458,581 | 3,654,442 | 4,113,023 | 11,492 | 363.9 | 237,226 | | |
| **Total** | **glob** | 171 | 115 | 507,753 | 7,314,926 | 7,822,679 | 18,608 | 576.5 | 205,651 | | |

Reading the table: the Glob condition needed more of everything except tool-result characters. Ratios,
Glob ÷ baseline, aggregate over the four tasks: turns 1.88×, tool calls 2.17×, new input tokens 1.11×, total
input tokens 1.90×, output tokens 1.62×, wall-clock 1.58×, tool-result characters 0.87×. Per task, total
input tokens were 1.62× (provenance), 1.52× (calibration), 1.24× (solve) and 3.30× (capacity); the only
per-task win for Glob was new input tokens on calibration (−20%), which the other three tasks reversed
(+35%, +10%, +16%).

Why: a Glob call returns a short cited list (61 calls, 53,573 characters in total, about 880 characters per
call, roughly 13k tokens across all four runs) that names definitions and first-occurrence lines but rarely the
mechanism line an answer has to quote, so the agent then reads a window of every cited file. Those reads were
152,078 of the Glob arm's 205,651 tool-result characters; the small payloads did not remove the reading, they
added a discovery turn in front of it. The baseline batched grep and `sed -n` ranges into single shell calls
and received the evidence lines directly. The retrieval-size reduction in §2 is real, but it measures the wrong
thing: the cost that matters is turns × context, and Glob added turns.

Against the `AGENT_BENCHMARK.md` launch gate, "lower input-token count with no material accuracy regression"
is **not met** on any task for total input tokens and met on one task of four for new input tokens.

## 6. Citation accuracy, completeness and unsupported claims

### Citation and completeness grading (adversarially audited final verdicts)

| Task | Arm | Citations supplied | Citations correct | Citation accuracy | Rubric facts present | Fact completeness | Factual claims | Unsupported claims | Unsupported rate | Critical hallucinations | Complete? |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Provenance | baseline | 41 | 41 | 100.0% | 11/13 | 84.6% | 36 | 4 | 11.1% | 0 | yes |
| Provenance | glob | 32 | 32 | 100.0% | 10/13 | 76.9% | 28 | 1 | 3.6% | 0 | no |
| Calibration | baseline | 41 | 41 | 100.0% | 12/14 | 85.7% | 41 | 2 | 4.9% | 0 | yes |
| Calibration | glob | 35 | 33 | 94.3% | 10/14 | 71.4% | 36 | 1 | 2.8% | 0 | no |
| Solve path | baseline | 26 | 26 | 100.0% | 9/14 | 64.3% | 26 | 4 | 15.4% | 0 | no |
| Solve path | glob | 24 | 24 | 100.0% | 10/14 | 71.4% | 28 | 2 | 7.1% | 0 | no |
| Capacity | baseline | 49 | 49 | 100.0% | 13/14 | 92.9% | 41 | 1 | 2.4% | 0 | yes |
| Capacity | glob | 39 | 39 | 100.0% | 13/14 † | 92.9% | 33 | 1 | 3.0% | 0 | yes |
| **Aggregate** | **baseline** | 157 | 157 | 100.0% | 45/55 | 81.8% | 144 | 11 | 7.6% | 0 | 3/4 |
| **Aggregate** | **glob** | 130 | 128 | 98.5% | 43/55 | 78.2% | 125 | 5 | 4.0% | 0 | 1/4 |

### Mechanical citation floor (deterministic: file exists, line exists, verbatim quote matches)

| Task | Arm | JSON citations | Line exists | Quote matches | Inline-only citations |
|---|---|---:|---:|---:|---:|
| Provenance | baseline | 41 | 41 | 41 | 0 |
| Provenance | glob | 32 | 32 | 32 | 0 |
| Calibration | baseline | 41 | 41 | 41 | 0 |
| Calibration | glob | 35 | 35 | 34 | 0 |
| Solve path | baseline | 26 | 26 | 26 | 0 |
| Solve path | glob | 22 | 22 | 22 | 2 |
| Capacity | baseline | 48 | 48 | 48 | 0 |
| Capacity | glob | 39 | 39 | 39 | 0 |

### Unsupported or incorrect claims found by the graders

- **Provenance / baseline** (minor): Objectives contribute readable pricing provenance via a `provenance` property (engine/src/scrcae/optimization/objectives.py:303). — Verified: `class MonetaryNPVObjective` starts at objectives.py:255 and the next class (`MinimizeCapitalObjective`) at 342, so line 303 is the only `provenance` property among the objective classes; …
- **Provenance / baseline** (minor): elasticity fits expose a JSON-safe `provenance` hashable by `canonical_json` (engine/src/scrcae/calibration/elasticity.py:260). — The docstring says this and the body (261-274) returns a flat dict of primitives, so the literal claim holds. But grep of app/ and engine/src (excluding legacy) for `.provenance()` finds no production caller; the method is not wired into build_audit_record at this commit. …
- **Provenance / baseline** (minor): `app/views/audit.py` renders them ... with a caption about recomputation (app/views/audit.py:64). — The caption at audit.py:63-66 reads 'Hashes are computed from the actual inputs and outputs of this run. Two runs with the same input hash and the same engine version will agree.' It is about where the hashes come from and reproducibility, not recomputation; the JSON citation's claim is accurate but the prose paraphrase is loose.
- **Provenance / baseline** (minor): CONFIDENCE section: 'the call graph from `solve` through `RunProvenance` to the audit tab is verified end to end.' — RunProvenance is not on the path to the audit tab. The Verification tab (app/main.py:349-352 -> app/views/audit.py:51-58 -> app/presenters.py:374) reads `result.audit` directly; RunProvenance (app/storage/models.py:45) only feeds PortfolioService.save (portfolios.py:101-102), the SQLite columns, and the sidebar notice in account.py:216-243. …
- **Provenance / glob** (minor): The Audit tab view renders those rows as a dataframe under a "Provenance" subheader — Mechanism verified (app/views/audit.py:50-62), and the code's own identifiers are audit_tab/audit_view (app/main.py:339, 350), but the user-visible tab label is 'Verification' (main.py:339 st.tabs(["Plan", "Sensitivity", "Verification"])); a reader looking for an 'Audit' tab in the UI would not find one. …
- **Calibration / baseline** (minor): Four hard gates fire before any fit: ... and a non-positive fitted intercept, which makes the ratio undefined (engine/src/scrcae/calibration/elasticity.py:454). — Confirmed by printing 441-455: the first three gates (441, 443, 447) precede the regression, but `fit = _ols(xs, ys)` is at line 450 and `if intercept <= 0.0` at 454 tests the fitted intercept, so it cannot fire 'before any fit' (the sentence contradicts itself by saying 'fitted'). The answer also omits the fifth refuse() path at 451-452 (`if fit is None: …
- **Calibration / baseline** (minor): I inferred (not verified by execution) that the stated coverage numbers in the docstring match the measured test floors. — Explicitly hedged, but the wording is inaccurate as written: the module docstring (elasticity.py:64-66) states about 91% and about 88%, whereas the test floors asserted at test_elasticity_calibration.py:493 and 511 are 0.85 and 0.80; the test docstrings (484-489, 504-507) say the floors are deliberately set below the measured values. …
- **Calibration / glob** (minor): "a fixed seed so the interval is reproducible for the audit ledger (engine/src/scrcae/calibration/elasticity.py:413)" — Substance verified: seed default 20260825 at line 409 and the docstring at 417-419 says the seed makes the interval reproducible as a precondition for the audit ledger. But line 413 is a blank line inside the docstring, and the answer reuses that same :413 for a different sentence ('Always returns a fit...', which is at 414); …
- **Solve path / baseline** (minor): It is re-exported from the optimization package (optimization/__init__.py:18) and from the top-level package (scrcae/__init__.py:22), which is how every caller reaches it. — Verified: the engine-internal callers bypass the package re-exports and import directly from the module (sweep.py:138 'from .optimizer import solve'; diagnostics.py:155 and :229 'from .optimizer import OptimizationRequest, solve'), which the answer itself cites two paragraphs later. …
- **Solve path / baseline** (minor): Three engine-internal call sites re-enter solve(), all via deferred local imports to avoid circular imports. — Two imprecisions. (a) There are four engine-internal call lines (sweep.py:148, diagnostics.py:157, :241, :332) in three functions; the answer's own enumeration lists four lines. (b) The circular-import rationale is documented and real only for diagnostics.py (comment at 153-154; optimizer.py imports diagnostics at 558 with the comment at 556-557). …
- **Solve path / baseline** (minor): A structural test pins engine_client.py as a headless module (app/tests/test_pipeline.py:135) ... reinforcing that the boundary is a single file. — Verified: line 135 is an entry in HEADLESS_MODULES (132-145), and test_no_streamlit_import_is_required_to_compute_anything (148) walks those modules' ASTs for Streamlit imports only. It says nothing about which modules call solve, so it does not evidence a single-file engine boundary; rubric caution 5 explicitly says not to accept it as proof. …
- **Solve path / baseline** (minor): The Streamlit app never calls solve() directly. — Internally inconsistent: app/engine_client.py is part of the app package and the answer's next sentence identifies engine_client.py:47 as the app-side call. The intended meaning (no UI/render module calls solve; only the headless engine_client does) is correct per grep -w solve under app/, which finds engine_client.py:24/47 as the only non-comment hits.
- **Solve path / glob** (minor): "the Streamlit app reaches the engine only through `app/engine_client.py`" (restated from the module docstring at engine_client.py:3) — Overbroad as a code fact: app/services/calibration.py:20-26 imports calibrate_elasticity from scrcae.calibration and calls it at line 245, and adapters.py:36-51, presenters.py:21, services/pricing.py:60 and views/sidebar.py:17 import scrcae types directly. …
- **Solve path / glob** (minor): "diagnostics imports `solve` locally rather than at module scope to avoid a circular import (engine/src/scrcae/optimization/diagnostics.py:155, engine/src/scrcae/optimization/sweep.py:138)" — The circular-import rationale is documented only at diagnostics.py:153-154 and optimizer.py:556-558. optimizer.py never imports sweep (grep hits only comments at lines 5 and 288), and sweep.py:138 carries no stated reason, so grouping sweep.py:138 under the circular-import explanation is unsupported. …
- **Capacity / baseline** (minor): The verifier `_verify` ... raising a `Violation` past a scaled tolerance (engine/src/scrcae/optimization/optimizer.py:779) — Nothing is raised. `Violation` is a frozen record dataclass (engine/src/scrcae/optimization/result.py:34-43) and optimizer.py:780-787 does `violations.append(Violation("resource_capacity", ...))`; `grep -rn 'raise .*Violation' engine/src/` returns no hits. …
- **Capacity / glob** (minor): The independent verifier `_verify` ... raises a `resource_capacity` `Violation` when usage exceeds capacity beyond a magnitude-scaled tolerance (optimizer.py:782). — Nothing is raised. optimizer.py:780-786 does `violations.append(Violation("resource_capacity", ...))` and the list is returned as ConstraintReport.violations at 789-794; `grep -n 'raise ' optimizer.py` shows the only raises are request validation at 193-221. …

† The Glob/capacity auditor confirmed the judge's per-fact verdicts and flipped none, but reported a 13-fact
denominator against the 14-fact rubric; the judge's confirmed 13/14 is used.

Reading the tables:

- **Citation accuracy** clears the ≥95% gate in both conditions: 157/157 (baseline) and 128/130 (Glob). The two
  Glob misses are in one answer and are both off-by-one: `elasticity.py:413` is a blank line inside the
  docstring whose sentence is at 414, and `app/services/calibration.py:274` is the continuation of a sentence
  that starts at 273. The deterministic floor agrees: every cited file and line exists in all 8 answers, and
  283 of 284 JSON quotes match their line verbatim. This is a property of the agent and the corpus, not of
  Glob: the baseline reached 100% with grep alone.
- **Completeness** clears the ≥90% gate in **neither** condition against the independently built rubrics (45/55
  vs 43/55). The rubrics are stricter than the hints in `AGENT_BENCHMARK.md`: they include app-side wiring,
  the user-facing summary strings, and the app-level tests. Per task Glob was ahead on solve (10 vs 9), level on
  capacity (13 vs 13), and behind on provenance (10 vs 11) and calibration (10 vs 12). Three baseline answers
  and one Glob answer met the "complete" bar (every sub-part addressed, ≥80% of facts).
- **Unsupported claims** were all graded *minor* (imprecise wording such as calling a recorded `Violation`
  "raised", or an over-broad "the app only reaches the engine through engine_client.py"); none were *material*
  or *critical*, and **no answer in either arm hallucinated anything about the optimizer or the refusal
  semantics**. The Glob arm had fewer (5 vs 11) while also making fewer claims (125 vs 144).
- **The trace cap showed up in the answers.** The Glob solve answer lists the engine test files that call
  `solve` as `test_diagnostics`, `test_node_exposure`, `test_parity` and `test_properties`; the baseline lists
  all seven. The two files missing from the Glob answer, `test_objective_units.py` and `test_resources.py`, are
  exactly the ones the 50-row cap dropped (§3.1). The Glob answer also carried two citations it admitted came
  "from trace output, not read"; both happened to be correct.

## 7. Expected citations from the benchmark documents

All 19 expected citations resolve at the corpus commit. Five of them are not evidence for their question: the
three `DOGFOOD.md` solve-path lines (`app/adapters.py:725`, `app/copilot.py:340`, `app/main.py:215`) are a
comment, a docstring and a comment; `app/copilot.py` as an "expected area" cannot reach `solve` by design
(its tests assert it imports neither `scrcae` nor `app.engine_client`); and `network.py:157` is a docstring
line inside the `Resource` class, not the field or validator. The remaining 14 are definitions, calls,
constraints, checks or test modules and are correct anchors.

### Benchmark-document expected citations, verified at commit 6f0fc8b

| Task | Expected citation | Present | Relevant evidence | Line text / note |
|---|---|---|---|---|
| Provenance | `app/storage/models.py:45` | yes | yes | class RunProvenance: |
| Provenance | `app/services/macro.py:44` | yes | yes |     def provenance(self) -> str: |
| Provenance | `engine/src/scrcae/calibration/elasticity.py:259` | yes | yes |     def provenance(self) -> dict[str, object]: |
| Provenance | `engine/src/scrcae/optimization/objectives.py:303` | yes | yes |     def provenance(self) -> dict[str, object]: |
| Provenance | `app/storage/models.py (file-level: provenance storage)` | yes | yes | Defines RunProvenance (line 45) and SavedPortfolio.provenance (line 119); module docstring lines 18-21 explain |
| Provenance | `app/presenters.py (file-level: provenance presentation paths)` | yes | yes | Defines provenance_rows (line 360) reading result.audit (line 374) into Item/Value rows including Network/Inpu |
| Calibration | `engine/src/scrcae/calibration/elasticity.py:404` | yes | yes | def calibrate_elasticity( |
| Calibration | `engine/src/scrcae/calibration/elasticity.py:431` | yes | yes |     def refuse(quality: FitQuality) -> ElasticityFit: |
| Calibration | `engine/tests/test_elasticity_calibration.py (file-level: refusal tests)` | yes | yes | class TestTheEstimatorRefusesRatherThanGuesses: |
| Solve path | `app/engine_client.py:47` | yes | yes |     return solve(request) |
| Solve path | `app/adapters.py:725` | yes | **no** | Verified: a comment inside the OptimizationRequest(...) constructor kwargs within build_optimization_request() |
| Solve path | `app/copilot.py:340` | yes | **no** | Verified: a docstring line of _rule_question() (def 335). copilot.py's only project import is `from app import |
| Solve path | `app/main.py:215` | yes | **no** | Verified: a comment inside the `if network is None:` early-return branch (214-225). The real app-level reach t |
| Solve path | `app/adapters.py (file-level: expected area)` | yes | yes | 1235-line adapter module; build_optimization_request() at line 685 assembles the OptimizationRequest passed to |
| Solve path | `app/copilot.py (file-level: expected area)` | yes | **no** | Verified: wc -l = 890; only project import is line 48; test_copilot.py:106-107 enforce the no-scrcae/no-engine |
| Capacity | `engine/src/scrcae/domain/network.py:157` | yes | **no** | Draft and refuter agree, and I confirmed: this is line 5 of the `Resource` class docstring (153-164) inside th |
| Capacity | `engine/src/scrcae/optimization/optimizer.py:471` | yes | yes |         problem += expr <= resource.capacity, f"resource_{index}" |
| Capacity | `engine/src/scrcae/optimization/diagnostics.py:199` | yes | yes |         if result.resource_use.get(resource.name, 0.0) >= resource.capacity - 1e-9 |
| Capacity | `engine/tests/test_resources.py (file-level: resource tests)` | yes | yes | 137-line test module with 8 test functions: no-resource parity and hashes (47), shared capacity binds (59), ze |

### Tool-level coverage of the verified rubrics by the benchmark's canned queries

The deterministic benchmarks judge success by a substring needle. Measured against the independently
verified rubrics instead, one canned Glob query surfaces this much of what a complete answer needs:

| Task | Canned query | Citations returned | Rubric files reached | Rubric lines reached exactly | Returned hits that are test files | Rubric files never surfaced |
|---|---|---:|---:|---:|---:|---|
| Provenance | `glob_search provenance` | 20 | 5 / 12 | 4 / 42 | 9 | `engine/src/scrcae/audit.py` (hash creation), `optimizer.py`, `result.py`, `sqlite_store.py`, `views/audit.py`, `services/portfolios.py`, `engine_client.py` |
| Calibration | `glob_search calibrate_elasticity` | 7 | 4 / 7 | 1 / 52 | 2 | `app/views/calibration_panel.py`, `app/tests/test_calibration.py` |
| Solve path | `glob_trace solve` (capped at 50) | 50 | 6 / 15 | 13 / 53 | 33 | `app/main.py`, `app/adapters.py`, `streamlit_app.py`, `result.py`, app tests, `views/sweep.py` |
| Capacity | `glob_search capacity` | 10 | 5 / 6 | 5 / 43 | 4 | `engine/src/scrcae/audit.py` |

The agents in the Glob arm compensated by issuing 7 to 27 MCP calls per task and then reading windows of the
cited files, which is exactly where the extra turns and tokens in §5 come from.

## 8. Limitations of this run

- One run per task per condition, one model, one day. The direction of the token and wall-clock result is
  consistent across all four tasks, but the magnitudes are single samples; they are not a statistical claim.
- The Glob condition reached the MCP server through a per-call stdio client launched from Bash, not through a
  natively registered MCP tool, so each query cost a shell round trip and a fresh server process. A native MCP
  integration would remove the process spawn but not the per-call turn, the small payloads, or the follow-up
  reads, which are what drive the token totals.
- Tool discipline was enforced by instruction and verified from transcripts rather than by a hard allow-list.
  The audit found no violations, so the conditions were clean, but a harness-level restriction would be stronger.
- Grading is by model agents (rubric builder, two critics, synthesiser, checker, judge, auditor per answer),
  with a deterministic script confirming file/line/quote existence. Judgements of whether a line "supports" a
  sentence are still model judgements; the adversarial audit pass is what limits their drift.
- The baseline agent had Bash and could batch several greps and reads into one call; this is normal Claude Code
  behaviour and is the comparison `AGENT_BENCHMARK.md` asks for, but it means "tool calls" are not directly
  comparable across arms. Turns and tokens are.
- The corpus is a single Python repository of 80 files. Nothing here says how Glob behaves on a large or
  multi-language repository.

## 9. Launch recommendation

**Needs engineering fixes.** Ranked by what blocks a credible claim:

1. **Make the retrieval tools complete and honest.** `glob_trace` must accept a limit, paginate or at least
   report `truncated: true` with the total count (97 for `solve`); the CLI has the same cap. Keyword hits must
   cite the line the snippet came from (or return one hit per matching line) instead of the first line in the
   file that contains the term.
2. **Fix the benchmark so it fails for the right reasons.** Replace `app/adapters.py:725` in
   `benchmarks/ab-tool.ts` and the comment/docstring lines in `DOGFOOD.md` with real evidence lines; stamp the
   index with an extractor/schema version in `src/store.ts` so an index built by older code is rebuilt instead
   of silently reused; regenerate `AB_RESULTS.json` from a clean index and commit only what reproduces.
3. **Return evidence, not pointers.** The model-level result says the cited list is too thin to answer from:
   the agent reads the file anyway. Returning the cited line with a few lines of context, marking definitions
   vs calls vs imports in trace output, and excluding `legacy/` and test files by default (or grouping them)
   are the changes most likely to turn the retrieval-size win into a context win.
4. **Make the repo checkable from a clean clone.** Declare `@types/bun` (or `bun-types`) and `typescript` as
   dev dependencies, point `tsconfig.json` at `tests/`, and add `export {}` (or an import) to
   `scripts/mcp-client-smoke.ts`.
5. **Then re-run this protocol.** Same four tasks, same corpus commit, fresh contexts, telemetry from usage
   records, ground-truth rubrics. The gate to advance to a public beta is the one already written in
   `AGENT_BENCHMARK.md`, with "lower input-token count" measured as total input tokens per task.

What is fine to say today: the MCP server speaks the wire protocol correctly to an independent client, the
index is incremental and refuses blank queries, cited payloads are 98–99% smaller than sending matching files,
and an agent working through Glob produced answers of the same accuracy as one working with grep. What is not
supported by any measurement in this repository: that Glob reduces the tokens or time an agent spends.

## 10. What this run did not do

Nothing was committed, pushed, or published; no source file, test, benchmark or script was modified; the
only file written in the repository is this one. Raw transcripts, rubrics and grading records were kept
outside the repository.
