# Glob — Retrieval Benchmark

Date: 2026-09-16

This benchmark compares the size of Glob's cited retrieval payload with a naive baseline that
would pass every matching Python file to an agent. Approximate tokens are `characters / 4`.
This is a retrieval-context proxy, not model-token telemetry and not an answer-quality score.

Corpus: `corpus/supply-chain-resilience-engine` (80 Python files).

| Question | Glob approx. tokens | Naive approx. tokens | Context reduction | Expected citations |
|---|---:|---:|---:|---|
| provenance / audit | 444 | 87,893 | 99.5% | found |
| elasticity fit and refusal | 300 | 21,977 | 98.6% | found |
| solve callers (trace) | 736 | 157,860 | 99.5% | found |
| resource capacity | 367 | 51,357 | 99.3% | found |

## Interpretation

The local retrieval layer is dramatically smaller than sending matching files wholesale. This
supports the product thesis that Glob can reduce exploration context. It does **not** prove a
model uses fewer tokens or reaches a correct answer faster: those require the same agent,
prompt, and task run with and without Glob.

The benchmark also caught an important usage distinction: `solve callers` should use
`glob_trace`, not generic search. The benchmark now exercises the purpose-built trace tool.

The next measurement remains an agent-level A/B run that records actual input/output tokens and
whether each answer cites the correct source locations.
