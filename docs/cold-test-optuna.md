# Cold test: the method on a public library

2026-09-17 · Optuna 5.0.0, installed from PyPI. No prior familiarity with its source.

The one claim left untested was whether the ablation method works on code the agent has
not read, written by people it has never worked with. Optuna was chosen because its
central premise is itself an ablatable claim: that its TPE sampler beats random search.

Note on scope: the public repo was cloned only as a pip package (a git clone was blocked
by the sandbox). Nothing was copied into any GitHub account — the test does not need it,
and forking someone else's library is a licensing decision for its owner to make.

## Ablation 1 — TPESampler vs RandomSampler: SOUND

Three 10-dimensional objectives, 15 seeds per cell, same seed both arms, minimising.

| budget | TPE wins (of 45) | median gain |
| --- | --- | --- |
| 20 trials | 31 | 24.1% |
| 50 trials | 41 | 70.5% |
| 100 trials | 43 | 83.2% |
| 200 trials | 43 | 90.5% |

By objective at 200 trials: sphere 15/15 (+97.0%), rosenbrock 15/15 (+90.5%),
rastrigin 13/15 (+25.0%). The hard multimodal case is where the advantage is thinnest,
which is the expected shape and a sign the measurement is behaving.

The library's central claim holds. This is a clean pass, and clean passes are what make
the other verdicts worth anything.

## Ablation 2 — MedianPruner: SOUND ON ONE ASSUMPTION, CATASTROPHIC OFF IT

Pruning is a trade — compute bought with quality — so both sides were measured, on two
curve shapes:

* **predictive**: early rank matches final rank. The case pruning is sold on.
* **deceptive**: the eventual winners look worst early. Real pattern: warmup schedules,
  annealing, regularisation that bites late.

60 trials x up to 30 steps, 12 seeds, TPE sampler held fixed.

| curve | compute saved | quality cost | seeds worse |
| --- | --- | --- | --- |
| predictive | 51% | **0.0%** | 0/12 |
| deceptive | **63%** | **+6379%** | **12/12** |

On the deceptive shape it saves *more* compute while destroying the answer, and nothing
in the library says which shape you have.

**The remedy exists and the default is the worst setting for it.** `n_warmup_steps`
defaults to 0, so pruning can begin at the first reported step:

| curve | warmup 0 (default) | 5 | 15 | 30 (the docstring's own example) |
| --- | --- | --- | --- | --- |
| predictive quality | +0% | +0% | +0% | +0% |
| predictive saved | 51% | 42% | 24% | 0% |
| deceptive quality | **+6379%** | **+6379%** | **+0%** | +0% |
| deceptive saved | 63% | 55% | 24% | 0% |

`n_warmup_steps=15` — half the curve — recovers full quality on the deceptive shape while
still saving 24%. The default of 0 is optimal on the predictive shape and ruinous on the
other.

## Claims audit

`MedianPruner`'s docstring describes what it does ("prune if worse than the median at the
same step") and how it handles NaN. It states **no precondition**: nothing about early
rank needing to predict final rank, and no caution about when the rule misleads. Grepping
the pruners package for any such warning returns nothing.

Meanwhile the safe setting appears in the docstring's worked example (`n_warmup_steps=30`)
while the constructor default is 0. A reader who copies the example is protected; a reader
who takes the defaults is not.

This is not a bug. It is an unstated precondition with a measured magnitude nobody had
published, which is the same shape as most of this session's findings elsewhere.

## Verdict on the cold test

Kill criterion set beforehand: more than a day to instrument, or nothing but "everything
is load-bearing". Neither triggered. One session segment, two ablations, one sound
component, one conditionally sound component with a quantified failure mode and a
quantified remedy.

One caught error worth recording, because it nearly became a false finding: the first
deceptive curve evaluated to `1.6*final + 20` at step 0 — still increasing in `final`, so
it ranked trials exactly as the predictive curve did. Both arms returned byte-identical
results (same best value, same 886 steps), which is what gave it away. The corrected curve
was sanity-checked to rank oppositely at step 0 *before* the run was trusted.
