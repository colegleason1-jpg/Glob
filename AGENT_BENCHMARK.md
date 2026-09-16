# Glob — Agent A/B Benchmark

## Purpose

Measure whether Glob helps an agent answer repository questions more accurately and with less
context than ordinary file search. This is the launch gate; the deterministic retrieval proxy
in `BENCHMARK.md` is not a substitute for this test.

## Corpus

Use the pinned local checkout:

```text
corpus/supply-chain-resilience-engine
```

Do not change the corpus between baseline and Glob runs. Record the commit before starting.

## Four tasks

Use the exact same prompt wording in both conditions:

1. **Provenance:** Where is provenance or audit hashing created, stored, and presented? Name
   the relevant modules and explain the data flow.
2. **Calibration:** How is elasticity calibrated, and what evidence causes the system to
   refuse a fit instead of guessing? Cite the estimator and refusal tests.
3. **Solve path:** What calls `solve()`? Identify the application boundary, important callers,
   and the engine optimization path. Distinguish definitions from references.
4. **Capacity:** Where are resource capacities modeled, enforced, diagnosed, and tested?

Require every answer to include `file:line` citations and a short confidence note.

## Conditions

### A — Baseline

Give the agent only its normal repository exploration tools. Do not provide Glob, its index,
its MCP configuration, `DOGFOOD.md`, or any benchmark results.

### B — Glob

Give the agent only the Glob MCP tools:

- `glob_overview`
- `glob_search`
- `glob_find_symbol`
- `glob_trace`

The agent may open files at Glob's cited locations to verify context, but it must not use a
second search/index tool during discovery.

Use a fresh conversation and equal model/settings for each task. Randomize the order of the
four questions between conditions if the client supports it.

## Record for each task

| Field | A baseline | B Glob |
|---|---:|---:|
| Input tokens | | |
| Output tokens | | |
| Wall-clock seconds | | |
| Tool calls | | |
| Correct citations | | |
| Required facts present | | |
| Unsupported claims | | |
| Complete answer? | | |

Save the raw transcripts outside the repository if they contain repository source. Commit only
an aggregate results table, not private transcripts.

## Scoring

A citation is correct only when its file and line point to evidence supporting the sentence it
follows. Score each task independently:

- **Citation accuracy:** correct citations / citations supplied
- **Fact completeness:** required facts present / required facts in the rubric
- **Unsupported-claim rate:** unsupported factual claims / all factual claims
- **Context efficiency:** input tokens used before the final answer

Suggested launch gate:

- ≥95% citation accuracy
- ≥90% required-fact completeness
- lower input-token count with no material accuracy regression
- zero critical hallucinations about the optimizer or its refusal semantics

Do not use the 40% reduction target as a pass/fail claim until input-token accounting is
available from the actual agent client.

## Task rubrics

### 1. Provenance

Expected areas include `app/storage/models.py`, app presenter/service provenance paths, and
engine objective/calibration provenance definitions. The answer must distinguish creation,
storage, and presentation rather than naming one file as the whole flow.

### 2. Calibration

Expected citations include:

- `engine/src/scrcae/calibration/elasticity.py:404` (`calibrate_elasticity`)
- `engine/src/scrcae/calibration/elasticity.py:431` (`refuse`)
- refusal tests under `engine/tests/test_elasticity_calibration.py`

The answer must explain that thin or inadequate evidence is refused rather than silently
converted into a fit.

### 3. Solve path

Expected areas include `app/engine_client.py`, `app/adapters.py`, `app/copilot.py`, and the
engine optimization modules. The answer must distinguish the `solve` call at
`app/engine_client.py:47` from references elsewhere.

### 4. Capacity

Expected areas include:

- `engine/src/scrcae/domain/network.py:157`
- `engine/src/scrcae/optimization/optimizer.py:471`
- `engine/src/scrcae/optimization/diagnostics.py:199`
- resource tests under `engine/tests/test_resources.py`

The answer must cover modeling, enforcement, diagnostics, and tests.

## Results

| Task | Baseline input tokens | Glob input tokens | Baseline citation accuracy | Glob citation accuracy | Complete? |
|---|---:|---:|---:|---:|---|
| Provenance | | | | | |
| Calibration | | | | | |
| Solve path | | | | | |
| Capacity | | | | | |
| **Aggregate** | | | | | |

**Decision:** pending actual agent-client runs.
