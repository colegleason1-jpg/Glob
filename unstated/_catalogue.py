"""The catalogue. Entries are data, so coverage grows without the code sprawling.

Each entry records what was measured when the entry was added, so a reader can see the
evidence rather than trust the claim, and so a later version of the library can be
re-measured against the same numbers.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CatalogueEntry:
    library: str
    component: str
    versions_measured: str
    assumption: str
    cost_when_violated: str     #: measured, with the number
    upstream_status: str        #: filed, documented, working-as-intended, unknown
    evidence: str               #: path to the full measurement

    def __str__(self) -> str:
        return f"{self.library}.{self.component} ({self.versions_measured})"


CATALOGUE: tuple[CatalogueEntry, ...] = (
    CatalogueEntry(
        library="python-dateutil",
        component="parser.parse",
        versions_measured="2.9.0.post0",
        assumption="month-before-day ordering, decided per string rather than per column",
        cost_when_violated=(
            "37.2% of a 2,000-row day-first column silently wrong, median 118 days off, "
            "0 exceptions and 0 warnings; one column returned under two conventions "
            "(803 month-first, 1,197 day-first). dayfirst=True fixes the slashes and "
            "transposes ISO 8601, moving the error rather than removing it: 376 -> 369."
        ),
        upstream_status="filed: dateutil/dateutil#402, open since 2017",
        evidence="docs/cold-test-dateutil.md",
    ),
    CatalogueEntry(
        library="pandas",
        component="DataFrame.merge",
        versions_measured="3.0.5",
        assumption="the join key is unique on at least one side",
        cost_when_violated=(
            "2.02x row inflation and +105.4% on the summed column, with 0 exceptions, "
            "0 warnings, no nulls introduced, dtypes preserved and every value in range. "
            "The mean moved only +1.6%, so a spot-check of the average looks clean while "
            "the total has doubled."
        ),
        upstream_status="guarded: validate= exists and defaults to None",
        evidence="docs/cold-test-pandas.md",
    ),
    CatalogueEntry(
        library="imbalanced-learn",
        component="SMOTE",
        versions_measured="0.14.2",
        assumption="the caller consumes rankings, not probabilities",
        cost_when_violated=(
            "PR-AUC down 3-24% (0/20 seeds winning at three of four ratios) and "
            "calibration destroyed at every ratio on every seed: Brier +41% to +1232%. "
            "At 1% prevalence the model reports 0.358 for a 0.015 base rate, a 23.85x "
            "inflation, while the unresampled model is accurate to within 1%."
        ),
        upstream_status=(
            "unstated: the whole over_sampling package mentions neither calibration "
            "nor probabilities"
        ),
        evidence="docs/cold-test-smote.md",
    ),
    CatalogueEntry(
        library="optuna",
        component="pruners.MedianPruner",
        versions_measured="5.0.0",
        assumption="early rank predicts final rank",
        cost_when_violated=(
            "+6379% quality cost on 12/12 seeds when eventual winners look worst early, "
            "while saving MORE compute than in the favourable case (63% vs 51%). "
            "n_warmup_steps=15 recovers full quality and still saves 24%; the "
            "constructor default is 0."
        ),
        upstream_status="unstated: the docstring gives no precondition",
        evidence="docs/cold-test-optuna.md",
    ),
    CatalogueEntry(
        library="scikit-learn",
        component="model_selection.train_test_split",
        versions_measured="1.9.1",
        assumption="rows are independent — that no two rows share a subject",
        cost_when_violated=(
            "accuracy overstated by 14.8% and ROC-AUC by 9.5% on 12 of 12 trials "
            "(0.9472 vs 0.8250, 0.9910 vs 0.9047) with 150 subjects at 8 rows each, "
            "0 exceptions and 0 warnings. The remedy, GroupShuffleSplit, ships in the "
            "same module."
        ),
        upstream_status=(
            "unstated: train_test_split takes no groups argument, and its docstring "
            "contains none of 'group', 'independent', 'leak', 'subject', 'cluster'"
        ),
        evidence="docs/cold-test-sklearn.md",
    ),
)
