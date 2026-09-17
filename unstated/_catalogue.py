"""The catalogue. Entries are data, so coverage grows without the code sprawling.

Each entry records what was measured when the entry was added, so a reader can see the
evidence rather than trust the claim, and so a later version of the library can be
re-measured against the same numbers.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Impact:
    """What the wrong answer does to the people downstream of the library.

    A bug is not a property of software; it is software not giving its users the correct
    thing. So every entry records who gets the wrong thing and what they do with it.

    The discipline here matters as much as anywhere else in this catalogue. ``mechanism``
    is *derived* from the measurement and is not negotiable. ``scenario`` is arithmetic
    the reader can redo with their own numbers, and its inputs are labelled illustrative —
    it never asserts what a given company loses, because nobody measured that. An invented
    dollar figure would be exactly the unmeasured claim this whole exercise exists to
    catch, and it would collapse the first time somebody checked it.
    """

    mechanism: str        #: what the wrong number does downstream, derived from the measurement
    lands_on: str         #: the function or role that receives it
    scenario: str         #: parameterised arithmetic; inputs illustrative, method exact
    detection: str        #: would anyone notice, and when


@dataclass(frozen=True)
class CatalogueEntry:
    library: str
    component: str
    versions_measured: str
    assumption: str
    cost_when_violated: str     #: measured, with the number
    upstream_status: str        #: filed, documented, working-as-intended, unknown
    evidence: str               #: path to the full measurement
    impact: Impact | None = None

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
        impact=Impact(
            mechanism=(
                "37.2% of rows carry a date a median 118 days from the truth, and every "
                "one is a valid date in the right year. Anything bucketed by time is "
                "therefore built on rows that landed in the wrong bucket: ageing "
                "brackets, cohort membership, reporting periods, retention windows, "
                "anything with a cut-off date."
            ),
            lands_on=(
                "receivables and ageing reports, SLA and breach calculations, cohort and "
                "retention analysis, and any regulatory return defined over a period"
            ),
            scenario=(
                "Arithmetic: with an ambiguity rate r on N dated rows, r*N rows move by "
                "the day/month gap. At the measured r=0.372, a 50,000-row ledger "
                "(illustrative) puts roughly 18,600 rows in the wrong period, median 118 "
                "days out. A receivable dated 10/03 read as 03/10 moves between ageing "
                "brackets in both directions, so the buckets do not merely shift — they "
                "cross-contaminate, and the totals still sum to the correct grand total."
            ),
            detection=(
                "Poor. Every value is a valid date in the same year, so range, dtype and "
                "null checks all pass and the grand total reconciles. It surfaces only "
                "when a human recognises one specific date as wrong, and most of the "
                "wrong ones are plausible."
            ),
        ),
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
        impact=Impact(
            mechanism=(
                "Row count multiplies by the product of duplicate keys on each side, so "
                "every SUM and COUNT over the joined frame inflates by the same factor "
                "while every MEAN stays close to correct. The measured case was 2.02x "
                "rows and +105.4% on the summed column against +1.6% on its mean."
            ),
            lands_on=(
                "any reported aggregate: revenue and bookings, exposure and position "
                "totals, headcount, claim volumes, units shipped — and anything computed "
                "from them, including per-unit costs and ratios whose numerator and "
                "denominator inflate unequally"
            ),
            scenario=(
                "Arithmetic: reported total = true total x (rows_out / matching_rows_in). "
                "At the measured 2.02x, a reported figure of any size is roughly double "
                "the truth. The inverse matters as much: a team that trusts the total and "
                "divides by a correct row count elsewhere gets a per-unit figure half what "
                "it should be. Plug in your own rows_out and matching_rows_in — both come "
                "out of check_merge before the join runs."
            ),
            detection=(
                "Poor, and worse than it looks. The mean moved only +1.6%, so the usual "
                "sanity check — does the average look right — passes while the total has "
                "doubled. Caught only by reconciliation against an independent source, "
                "if one exists."
            ),
        ),
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
        impact=Impact(
            mechanism=(
                "Resampling changes the training base rate, so the fitted intercept "
                "shifts and every predicted probability is inflated. Measured: 0.358 "
                "predicted against a 0.015 base rate, a 23.85x overstatement, while the "
                "unresampled model was accurate to within 1%. Ranking is roughly "
                "preserved; the numbers are not."
            ),
            lands_on=(
                "anything that consumes the probability rather than the ranking: expected "
                "loss and expected value calculations, cost-weighted decision thresholds, "
                "capacity planning from expected volumes, and any figure reported as a "
                "risk or a rate to a committee or a regulator"
            ),
            scenario=(
                "Arithmetic: expected value = p x outcome. An inflation factor of f "
                "multiplies every expected-value figure by f. At the measured f=23.85 "
                "(1% prevalence), a book of 100,000 cases (illustrative) with a true "
                "expected event count of 1,500 is reported as roughly 35,800. A threshold "
                "chosen to act above a 20% probability fires on cases whose true "
                "probability is under 1%."
            ),
            detection=(
                "Poor. ROC-AUC is unchanged and PR-AUC moves only single digits, so the "
                "metrics normally reported look fine. Calibration is rarely monitored, "
                "and the probabilities remain in [0,1] and sum sensibly."
            ),
        ),
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
        impact=Impact(
            mechanism=(
                "Pruning kills trials on early performance. When early rank does not "
                "predict final rank the surviving trials are the wrong ones, so the "
                "selected configuration is not the best one searched. Measured: +6379% on "
                "the objective, on 12 of 12 seeds, while saving MORE compute than in the "
                "favourable case."
            ),
            lands_on=(
                "model selection — the configuration that gets deployed. Also anyone "
                "reading a tuning run as evidence that a search space was explored"
            ),
            scenario=(
                "Arithmetic: the reported best is the best of the SURVIVING trials, not "
                "of those started. With a prune rate q on T trials, the search that "
                "actually happened is over (1-q)T candidates, chosen by a criterion "
                "uncorrelated with the objective. At the measured q=0.63 on 200 trials "
                "(illustrative), 126 candidates were discarded on a signal that did not "
                "predict the outcome, and the search space is smaller than the number in "
                "the write-up."
            ),
            detection=(
                "Only by re-running without the pruner and comparing — which nobody does, "
                "because the run completed, reported a best value, and was faster."
            ),
        ),
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
        impact=Impact(
            mechanism=(
                "A random split puts the same subject on both sides, so the test set "
                "measures memorisation. Measured: accuracy overstated 14.8% and ROC-AUC "
                "9.5%, on 12 of 12 trials, with 92% of subjects present in both splits "
                "and zero identical rows."
            ),
            lands_on=(
                "every reported model performance number: validation reports, model risk "
                "documentation, go/no-go deployment decisions, vendor and internal "
                "benchmarks, and anything a regulator is shown as evidence a model works"
            ),
            scenario=(
                "Arithmetic: the reported score is on a test set whose subjects the model "
                "trained on. The measured gap is the overstatement — 0.9472 reported "
                "against 0.8250 real. A threshold set to hold a false-positive rate at "
                "the reported performance will miss it in production by roughly that "
                "margin, and the shortfall arrives as a slow drift that gets attributed "
                "to the data rather than the split."
            ),
            detection=(
                "The failure looks like SUCCESS, which is the worst case in this "
                "catalogue. A model scoring 0.95 instead of 0.83 does not get "
                "investigated. It surfaces as unexplained underperformance after "
                "deployment, usually blamed on drift."
            ),
        ),
    ),
    CatalogueEntry(
        library="boto3",
        component="list/scan/query operations",
        versions_measured="1.43.96",
        assumption="the caller's result set fits in one page",
        cost_when_violated=(
            "list_objects_v2 returned 1,000 of 2,500 objects — 40% of the truth, 1,500 "
            "silently missing, 0 exceptions and 0 warnings, HTTP 200 and a well-formed "
            "list. DynamoDB scan is worse: it truncates on response size, so the same "
            "code against the same 400-row table returned 100% at 200-byte rows and 12% "
            "(49 rows) at 20,000-byte rows. The cutoff moves when someone adds a column, "
            "and the count returned is never a round number anyone would recognise as a "
            "ceiling."
        ),
        upstream_status=(
            "documented: IsTruncated/LastEvaluatedKey are in the response and "
            "get_paginator exists — but nothing at the call site says the default is a "
            "first page"
        ),
        evidence="docs/cold-test-boto3.md",
        impact=Impact(
            mechanism=(
                "The first page is returned and the job succeeds. Measured: 1,000 of "
                "2,500 S3 objects (40%), and 49 of 400 DynamoDB rows (12%) once rows "
                "widened to 20 KB. Every downstream step then runs to completion over a "
                "subset, reporting success."
            ),
            lands_on=(
                "backup and archival jobs, retention and deletion sweeps, cost and "
                "inventory reporting, data pipelines enumerating their own input, and "
                "compliance scans that enumerate objects to attest they were checked"
            ),
            scenario=(
                "Arithmetic: coverage = page_size / true_count for S3, and for DynamoDB "
                "coverage = (1 MB / mean_item_bytes) / true_count, which moves whenever "
                "the rows get wider. A scan attesting that every object in a bucket was "
                "checked, run against 2,500 objects (illustrative), checked 1,000 and "
                "reported completion. A retention sweep deletes the first page and leaves "
                "the rest, so the job looks idempotent and never converges."
            ),
            detection=(
                "Very poor, and the DynamoDB case has no learnable ceiling: the count "
                "returned moves with row width, so the same code silently degrades when "
                "someone adds a column. Nothing raises, the exit status is zero, and a "
                "compliance attestation of completeness is produced over 40% of the data."
            ),
        ),
    ),
)
