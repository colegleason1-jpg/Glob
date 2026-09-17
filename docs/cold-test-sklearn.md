# Cold test 6: train_test_split (scikit-learn 1.9.1)

2026-09-17 · **audited: scikit-learn 1.9.1, `sklearn.model_selection.train_test_split`**

The assumption: rows are independent. When several rows share a subject — repeated
measurements, sessions per user, images per patient, many rows per customer — a random
split puts the same subject on both sides and the score reports memorisation.

## Measured

150 subjects at 8 rows each, 12 features, random forest, 12 trials:

| split | accuracy | ROC-AUC |
| --- | --- | --- |
| `train_test_split` (what almost everyone writes) | 0.9472 | 0.9910 |
| `GroupShuffleSplit` (no subject on both sides) | 0.8250 | 0.9047 |
| **overstatement** | **+0.1222 (+14.8%)** | **+0.0863 (+9.5%)** |

Overstated on **12 of 12 trials**. Zero exceptions, zero warnings.

## Signal

`train_test_split` has no `groups` argument at all. Its docstring contains none of:

| word | present |
| --- | --- |
| group | no |
| independent | no |
| leak | no |
| subject | no |
| cluster | no |

The docstring does not have vocabulary for the hazard. This is the strongest "no signal"
result of the six: in the other cases a flag or a parameter at least gestured at the
assumption.

The remedy — `GroupShuffleSplit`, `GroupKFold` — ships in the same module under a name
you only find if you already know to look for it.

## Class

Sixth confirmation:

> A component that works under an assumption, with nothing signalling when the assumption
> does not hold, and a failure that passes every ordinary check.

Here the failure is worse than silent: it looks like **success**. A model that scores 0.95
instead of 0.83 does not get investigated.
