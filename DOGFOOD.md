# Glob — First Dogfood Run

Corpus: `corpus/supply-chain-resilience-engine` (80 Python files, 1,131 symbols).

This is a discovery run, not a claim that the M3 success gate has passed. The tool surfaced
useful citations quickly; the answers still need source reading and a real token-count
comparison before the 95% / 40% gate can be judged.

## Checklist

| Question | Glob surfaced | Initial answer path | Status |
|---|---|---|---|
| Where does provenance/audit hashing happen? | `app/services/macro.py:44`, `engine/src/scrcae/calibration/elasticity.py:259`, `engine/src/scrcae/optimization/objectives.py:303`, `app/storage/models.py:45` | Provenance is represented in the engine and app storage/presenter layers; inspect the cited definitions to separate hash generation from display. | Candidate citations found; verify manually |
| What fits elasticity and when does it refuse? | `engine/src/scrcae/calibration/elasticity.py:404` (`calibrate_elasticity`), `:431` (`refuse`), plus refusal tests | Calibration and refusal are colocated in the engine; thin-history and low-evidence refusal behavior is explicitly tested. | Candidate citations found; verify manually |
| What does `solve()` depend on and who calls it? | `app/engine_client.py:47` (call), `app/adapters.py:725`, `app/copilot.py:340`, `app/main.py:215` | The app client is the boundary; adapters, copilot, and UI paths reference solve. | Candidate citations found; lightweight trace, not AST-resolved |
| Where are resource capacities constrained? | `engine/src/scrcae/domain/network.py:157`, `engine/src/scrcae/optimization/diagnostics.py:199`, `engine/src/scrcae/optimization/optimizer.py:471` | Capacity is modeled in the domain and checked in optimization/diagnostics; resource tests cover binding and zero capacity. | Candidate citations found; verify manually |

## M3 decision

**Proceed, but do not declare the gate passed yet.** The search product is useful enough to
continue. The next dogfood improvement is a citation-focused result format and a repeatable
baseline measurement, not a hosted backend.

Current market conclusion: keep Glob local-first and free at the individual level. The
lowest-cost route to broad adoption is MCP compatibility, not an API service. Add HTTP only
for CI/team integrations after repeated demand for shared or automated context.
