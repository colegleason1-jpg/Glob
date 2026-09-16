# Glob — Tool-Level A/B Results

Date: 2026-09-16

This is a controlled retrieval experiment. The Glob condition uses the actual stdio MCP
process through `benchmarks/ab-tool.ts`; it does not call the index library directly. The
baseline reads every Python file containing the task terms. Approximate tokens are characters
 divided by four.

| Task | Baseline approx. tokens | Glob MCP approx. tokens | Retrieval reduction | Expected citations |
|---|---:|---:|---:|---|
| Provenance | 87,893 | 900 | 99.0% | Found |
| Calibration | 21,977 | 469 | 97.9% | Found |
| Solve callers | 157,860 | 1,329 | 99.2% | Found |
| Capacity | 51,357 | 601 | 98.8% | Found |

**Result: pass — 4/4 expected citation sets found through the actual MCP client process.**

## What this establishes

- The MCP wire path works for the four dogfood tasks.
- Glob returns dramatically smaller, cited retrieval payloads than sending matching files
  wholesale.
- The tool choice matters: the solve task uses `glob_trace`, while the others use
  `glob_search`.

## What this does not establish

This is not an agent/model A/B experiment. It does not measure model input/output tokens,
answer correctness, reasoning time, or whether a model can synthesize the cited evidence into
a complete answer. Those measurements still require the same external agent client and model
run under both conditions.
