# Kill God — audit

Repo: colegleason1-jpg/silent-fantasy-evolution... @ claude/gracious-mendel-du15pv
(`main` is stale — Aug 26, 3 files; the live branch is Sep 15, ~2,600 lines of Python.)
Read-only. 1,970 lines of Python across engine, combat, content, state, tests.

This is the third domain for the same engine interface, and the furthest from supply
chain. That makes it the cold-system test, better than one I would have designed.

## What holds up

**The MILP is genuinely load-bearing** — the opposite of the routing MILP measured in
Chat-Johnson. This one has real coupling: a shared budget net of bundle discounts,
pairwise dependencies, and a cardinality cap. Measured against the built-in greedy
fallback across all 100 quests:

| | result |
| --- | --- |
| encounters identical in units, HP and attack | **9/100** |
| MILP objective better / worse / equal | 90 / 2 / 8 |
| median relative objective gain | **+24.84%** |
| total enemy HP, MILP vs greedy (median) | 906 vs 698 |
| total enemy attack, MILP vs greedy (median) | 110 vs 92 |
| budget utilisation, both | 100% |

A player on the greedy path meets a materially easier game — roughly 30% less enemy HP
and attack. `scipy>=1.11` is in requirements.txt so the fallback should not normally
fire, but the difficulty curve is tuned against one solver and the README frames the
fallback only as "says so".

**The verification is real, not F4.** `_verify` recomputes budget, dependencies, bundle
validity, per-node funding and the active count from the returned allocation, each with
its own slack. That is the thing the acquired system faked; here it is genuine.

## Findings

### 1. "Swap the package for the real engine and the game keeps working" is false

The README's boldest claim. Tested against the real `scrcae`:

* `OptimizationResult` and `ConstraintReport` are not at `scrcae`'s top level — they live
  in `scrcae.optimization`. Cosmetic: an import path.
* `Intervention` differs: the game passes `description`; scrcae takes `action`,
  `min_funding_scale`, `max_funding_scale`, `usage`. The game puts minimum funding on the
  response instead. Constructor calls would not transfer.
* **`min_active_nodes` / `max_active_nodes` do not exist in scrcae at all.** Confirmed
  against its full parameter list. The game's formulation includes
  `min_active <= sum_i x_i <= max_active`, so a swap silently drops that row.

Measured cost of dropping it, across 100 quests:

| | with cap | cap dropped |
| --- | --- | --- |
| enemies per encounter (median / max) | 3 / 3 | **6 / 9** |
| total enemy HP (median) | 906 | **1288** (+42%) |
| total enemy attack (median) | 110 | **182** (+65%) |
| encounters with more enemies | — | 89/100 |

The game would run. It would be a different, much harder game. "Keeps working" is not
the right description of that.

This is useful in the other direction too: a cardinality constraint ("fund at most N
projects") is standard for a portfolio optimizer, and scrcae does not have one. The game
found a real feature gap in the engine, not just a shim mismatch.

### 2. The solver docstring's "exact" overreaches, negligibly

`solver.py` documents the piecewise-linear response as "exact for a maximized concave
term". That is the standard convex-combination result and it is true **at** the
breakpoints. The formulation permits scales between them, where the value is the chord,
which under-reports a concave function.

Measured: on quest 85 the MILP scored 7210.38 against greedy's 7212.94 — a 0.035% loss to
a heuristic, which an optimal solver should not suffer. Cause confirmed: the MILP chose
scales of 0.9469 and 0.6750, both strictly between breakpoints on the grid
[0.35, 0.48, 0.61, 0.74, 0.87, 1.0], where the chord under-reports by 0.029% and 0.059%.
Greedy evaluates the exact response and landed on 1.0, a breakpoint.

Same family as scrcae's chord/tangent issue, but benign here: the breakpoints are dense
relative to the curvature. Worth a docstring correction, not a code change.

### 3. `main` is stale

Same pattern as Chat-Johnson: `main` carries a 996-line single `app.py` from Aug 26, while
the real work is on a branch. Anyone cloning the default branch gets the wrong thing.

## Is this on plan or a pivot?

On plan, and it is the test that was next. The open question was whether the method works
on a system it was not built around. A dark-fantasy RPG is about as far from supply-chain
capital allocation as the interface can travel, and the audit produced three findings in
well under a day — including one (the cardinality gap) that is real product intelligence
about the engine rather than a bug in the game.

The kill criterion stated beforehand was: more than a day to instrument, or nothing but
"everything is load-bearing". Neither triggered.
