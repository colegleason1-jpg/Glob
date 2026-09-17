# Cold test 2: SMOTE (imbalanced-learn 0.14.2)

2026-09-17 · installed from PyPI, no prior familiarity with the source.

A second public library, chosen from a different field than the first, to see whether the
defect class found four times already holds a fifth: a component that works under an
assumption, with nothing in the library signalling when the assumption does not hold.

SMOTE is among the most-used tools in applied machine learning. Its claim is that
synthetic oversampling of the minority class improves performance on imbalanced data.
"Performance" is the word doing the work.

Method: 6,000 synthetic samples, 20 informative-ish features, logistic regression, 20
seeds per imbalance ratio, 30% held out. Resampling runs inside `imblearn`'s own Pipeline
so it touches training folds only — doing that by hand is the standard way to measure your
own mistake instead of the library's behaviour.

## Ranking: no real gain, and a consistent loss on the metric that matters

| positives | metric | no SMOTE | with SMOTE | change | SMOTE wins |
| --- | --- | --- | --- | --- | --- |
| 1% | ROC-AUC | 0.7131 | 0.7031 | −1.4% | 10/20 |
| 1% | **PR-AUC** | 0.1157 | 0.0882 | **−23.8%** | **3/20** |
| 5% | ROC-AUC | 0.8288 | 0.8352 | +0.8% | 18/20 |
| 5% | **PR-AUC** | 0.3416 | 0.3121 | **−8.6%** | **0/20** |
| 10% | ROC-AUC | 0.8617 | 0.8703 | +1.0% | 16/20 |
| 10% | **PR-AUC** | 0.4784 | 0.4437 | **−7.3%** | **0/20** |
| 20% | ROC-AUC | 0.8526 | 0.8558 | +0.4% | 12/20 |
| 20% | **PR-AUC** | 0.6342 | 0.6154 | **−3.0%** | **0/20** |

ROC-AUC moves by under a point either way. PR-AUC — the ranking metric normally
recommended for exactly this problem — is worse at every ratio tested, and worse on 20 of
20 seeds at three of the four.

## Calibration: destroyed, at every ratio, on every seed

| positives | Brier, no SMOTE | Brier, SMOTE | change | SMOTE wins |
| --- | --- | --- | --- | --- |
| 1% | 0.0139 | 0.1849 | **+1232%** | **0/20** |
| 5% | 0.0435 | 0.1544 | +255% | 0/20 |
| 10% | 0.0708 | 0.1449 | +105% | 0/20 |
| 20% | 0.1073 | 0.1512 | +41% | 0/20 |

The mean predicted probability against the true base rate is the plainer statement of it:

| positives | true base rate | mean predicted, plain | mean predicted, SMOTE | inflation |
| --- | --- | --- | --- | --- |
| 1% | 0.0150 | 0.0148 (**0.99x**) | 0.3578 | **23.85x** |
| 5% | 0.0544 | 0.0543 (1.00x) | 0.3205 | 5.89x |
| 10% | 0.1042 | 0.1040 (1.00x) | 0.3355 | 3.22x |
| 20% | 0.2033 | 0.2038 (1.00x) | 0.3799 | 1.87x |

At 1% prevalence the SMOTE model reports a 36% chance of an event that happens 1.5% of
the time. The plain model is accurate to within 1%. Anything downstream that reads those
numbers as probabilities — an expected-value calculation, a cost-weighted threshold, a
reported risk — is wrong by a factor of 24 and nothing says so.

## The steelman, tested

SMOTE's usual defence is that it fixes recall at a fixed threshold: at 1% prevalence the
plain model predicts no positives at all. That is true, and measured:

| positives | model | recall | precision | F1 |
| --- | --- | --- | --- | --- |
| 1% | plain @ 0.5 | 0.000 | 0.000 | 0.000 |
| 1% | SMOTE @ 0.5 | 0.589 | 0.032 | 0.060 |
| 1% | **plain, threshold moved to match** | 0.589 | **0.034** | **0.064** |
| 5% | plain @ 0.5 | 0.148 | 0.811 | 0.252 |
| 5% | SMOTE @ 0.5 | 0.731 | 0.162 | **0.268** |
| 5% | plain, threshold moved to match | 0.735 | 0.141 | 0.240 |
| 10% | SMOTE @ 0.5 | 0.787 | 0.306 | **0.440** |
| 10% | plain, threshold moved to match | 0.787 | 0.283 | 0.412 |

Read honestly, both ways: at 1% the entire benefit is available by moving the threshold,
which costs nothing and keeps calibration intact — and threshold-moving is slightly
better. At 5% and 10% SMOTE keeps a real edge of about +0.03 F1 over pure
threshold-moving.

So it is a trade, not a free win. The bill for that +0.03 F1 is 7–9% of PR-AUC and a
3–6x inflation of every probability the model reports.

## Claims audit

Grepping the entire `over_sampling` package — every SMOTE variant, ADASYN, the random
over-sampler — for `calibrat`, `probabilit`, `overestimat`, `inflat`, `base rate` or
`prior shift` returns **nothing**. The `SMOTE` class docstring mentions neither
calibration nor probabilities.

The distortion is not a bug: resampling changes the training base rate, so a shifted
intercept is the arithmetic working correctly. It is an unstated precondition — this is
safe when you consume rankings and unsafe when you consume probabilities — with a
magnitude that had not been put in front of the user.

## Verdict

The class holds a fifth time. Two public libraries, cold, in one session:

| library | component | verdict |
| --- | --- | --- |
| Optuna | TPESampler | sound — 43/45 at 100+ trials |
| Optuna | MedianPruner | conditionally sound: 51% compute saved on predictive curves, +6379% quality cost on deceptive ones, precondition unstated |
| imbalanced-learn | SMOTE | conditionally sound: small F1 gain at moderate imbalance, bought with PR-AUC and a 24x probability inflation, precondition unstated |

Note the shape of both failures: not wrong code, but a silent dependence on a property of
your data that the library never checks and never mentions, with the safe path costing
something real.
