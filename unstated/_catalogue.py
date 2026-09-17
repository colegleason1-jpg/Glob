"""The catalogue. Entries are data, so coverage grows without the code sprawling.

Each entry records what was measured when the entry was added, so a reader can see the
evidence rather than trust the claim, and so a later version of the library can be
re-measured against the same numbers.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Impact:
    """What the software told its user, and what was actually true.

    A bug is not a property of code. It is code telling its user something false about the
    world the user cares about. So an entry does not stop at "the library behaves this
    way" — it records the sentence the caller believes they are holding, the sentence they
    are actually holding, and what stops being true downstream.

    The domain is whatever the caller's domain is. A count of oranges that should be zero
    and reads two is the same failure as a revenue total that doubles: the system asserted
    a fact about the world and the fact was wrong. Money is one instance, not the measure.

    Every field must be **derivable from the measurement**. Nothing here asserts what a
    named party experienced, because nobody measured that — an invented consequence is the
    same unmeasured claim this catalogue exists to catch.
    """

    believed_claim: str   #: the sentence the caller thinks the return value asserts
    actual_claim: str     #: the sentence it actually asserts, with the measured number
    breaks: str           #: what stops being true downstream, across domains
    detection: str        #: would anyone notice, and when


@dataclass(frozen=True)
class CatalogueEntry:
    """One precondition, pinned to the versions it was measured on.

    **An entry is a claim about versions, not about a library.** That is not a formality:
    ``cryptography.Certificate.not_valid_after`` is silently naive in every release from
    3.4.8 (2021) to 41.0.7 (2023) and emits a deprecation warning from 42.0.0 — the same
    attribute, a defect on one installation and a non-event on the next.

    So a fix upstream does not delete an entry, it **bounds** it. Someone running the
    affected range still has the defect today, and ``resolved_in`` tells them exactly what
    to upgrade to. An entry that is resolved is more useful than one that is not, because
    it comes with the remedy attached.
    """

    library: str
    component: str
    versions_measured: str      #: the versions actually run, comma-separated
    assumption: str
    cost_when_violated: str     #: measured, with the number
    upstream_status: str        #: filed, documented, working-as-intended, unknown
    evidence: str               #: path to the full measurement
    impact: Impact | None = None

    # ---- prose, for a human to read -------------------------------------
    affected_versions: str = "not yet ranged"   #: the measured span, with dates
    resolved_in: str = "not resolved"           #: the verdict, with its explanation

    # ---- the same facts, as facts ---------------------------------------
    #
    # These are NOT derived from the prose above at runtime. They were read off the
    # measurement once, by hand, and are checked against the prose by
    # ``test_process.py``. An earlier version of ``tools/state.py`` recovered them with a
    # regex and a string split, and produced three wrong renderings in a row — a span of
    # "—" because the text said "2.4-year" rather than "2.4 years", and a status reading
    # "fixed in partially: 26.0". Parsing English to recover a number the writer already
    # knew is the mistake; this is the fix.
    span_years: float | None = None             #: measured affected span
    resolution: str = "open"                    #: "open" | "partial" | "fixed"
    resolved_version: str | None = None         #: the version that fixes it, if any
    check: str | None = None                    #: the callable in unstated.checks, if any

    RESOLUTIONS = ("open", "partial", "fixed")

    @property
    def is_resolved(self) -> bool:
        """True when upstream has fixed this, wholly or in part."""
        return self.resolution in ("partial", "fixed")

    @property
    def status(self) -> str:
        """One short phrase for a table cell. Never derived from prose."""
        if self.resolution == "open":
            return "open"
        if self.resolution == "partial":
            return f"PARTLY fixed {self.resolved_version or '?'}"
        return f"fixed in {self.resolved_version or '?'}"


    def __str__(self) -> str:
        span = self.affected_versions if self.affected_versions != "not yet ranged" else self.versions_measured
        tail = f", resolved in {self.resolved_in}" if self.is_resolved else ""
        return f"{self.library}.{self.component} ({span}{tail})"


CATALOGUE: tuple[CatalogueEntry, ...] = (
    CatalogueEntry(
        library="python-dateutil",
        component="parser.parse",
        versions_measured="2.9.0.post0",
        affected_versions=(
            "present in all 14 releases measured from 2.1 (2012-03-28) through 2.9.0.post0 "
            "(2024-03-01, current latest) — 12.0 years. The dayfirst=True/ISO-8601 half is "
            "narrower and is a REGRESSION: absent at 2.5.1 and every release before it "
            "(where the documented remedy genuinely works, 0/2000 wrong), introduced at "
            "2.5.2 (2016-03-27) in a partly-raising form, fully silent from 2.5.3 "
            "(2016-04-21) onward — 8.0 years"
        ),
        resolved_in=(
            "not resolved"
        ),
        assumption="month-before-day ordering, decided per string rather than per column",
        cost_when_violated=(
            "37.2% of a 2,000-row day-first column silently wrong, median 118 days off, "
            "0 exceptions and 0 warnings; one column returned under two conventions "
            "(803 month-first, 1,197 day-first). dayfirst=True fixes the slashes and "
            "transposes ISO 8601, moving the error rather than removing it: 376 -> 369."
        ),
        upstream_status="filed: dateutil/dateutil#402, open since 2017",
        evidence="docs/cold-test-dateutil.md",
        span_years=12.0,
        resolution="open",
        resolved_version=None,
        check="check_dates",
        impact=Impact(
            believed_claim="This row happened on this date.",
            actual_claim=(
                "This row happened on one of two dates, and which one was decided per "
                "string by whether the first number exceeded 12. Measured: 37.2% of a "
                "day-first column carries the other date, a median 118 days away, and "
                "95% of the rows that are right are right only by that accident."
            ),
            breaks=(
                "Anything that puts a record in a bucket by when it happened. An invoice "
                "moves between ageing brackets; a patient visit moves between reporting "
                "periods; a shipment moves between quarters; a consent record moves "
                "across a retention cut-off. The buckets do not shift together — records "
                "cross in both directions, so each bucket is contaminated by the other "
                "while the grand total still reconciles."
            ),
            detection=(
                "Poor. Every value is a valid date in the same year, so range, dtype and "
                "null checks pass and the total is unchanged. It surfaces only when a "
                "human recognises one specific date as wrong, and most of the wrong ones "
                "are perfectly plausible."
            ),
        ),
    ),
    CatalogueEntry(
        library="pandas",
        component="DataFrame.merge",
        versions_measured="3.0.5",
        affected_versions=(
            "present and silent in 12 releases sampled from 0.25.2 (2019-10-19) through 3.0.5 "
            "(2026-07-22, current latest) — 6.8 years. 12 of the 57 final releases in that "
            "range; the other 45 are bracketed, not measured. Nothing is known about 0.24.2 "
            "or earlier: no wheel installs on the oldest obtainable interpreter"
        ),
        resolved_in=(
            "not resolved"
        ),
        assumption="the join key is unique on at least one side",
        cost_when_violated=(
            "2.02x row inflation and +105.4% on the summed column, with 0 exceptions, "
            "0 warnings, no nulls introduced, dtypes preserved and every value in range. "
            "The mean moved only +1.6%, so a spot-check of the average looks clean while "
            "the total has doubled."
        ),
        upstream_status="guarded: validate= exists and defaults to None",
        evidence="docs/cold-test-pandas.md",
        span_years=6.8,
        resolution="open",
        resolved_version=None,
        check="check_merge",
        impact=Impact(
            believed_claim="There are this many of these, and they total this much.",
            actual_claim=(
                "There are this many matches multiplied by the duplicate keys on the "
                "other side. Measured: 2.02x the rows, +105.4% on the summed column, "
                "+1.6% on its mean."
            ),
            breaks=(
                "Every count and every total computed from the joined result. If the rows "
                "are oranges, you report twice the oranges you have; if they are "
                "prescriptions, twice the prescriptions; if they are transactions, twice "
                "the money. And the inverse bites just as hard — a correct denominator "
                "from elsewhere divided into the inflated total halves every per-unit "
                "figure. Anything reconciled downstream against a physical count, a bank "
                "statement or a stock take now disagrees with reality by the inflation "
                "factor."
            ),
            detection=(
                "Poor, and worse than it looks. The mean moved +1.6%, so the habitual "
                "sanity check — does the average look right — passes while the total has "
                "doubled. Caught only by reconciliation against an independent source."
            ),
        ),
    ),
    CatalogueEntry(
        library="imbalanced-learn",
        component="SMOTE",
        versions_measured="0.14.2",
        affected_versions=(
            "present, stable to four significant figures, in all 10 releases measured from 0.6.0 "
            "(2019-12-05) through 0.14.2 (2026-06-07, current latest) — 6.5 years, covering "
            "every minor series from 0.6 to 0.14. ~8 point releases inside the span are "
            "bracketed rather than measured. 0.5.0 and below could not be run (they import "
            "sklearn modules removed before the oldest available interpreter)"
        ),
        resolved_in=(
            "not resolved — and across 6.5 years and ten releases the library never added a warning, deprecation, parameter or docstring sentence about the precondition"
        ),
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
        span_years=6.5,
        resolution="open",
        resolved_version=None,
        check=None,
        impact=Impact(
            believed_claim="There is a p chance this case is positive.",
            actual_claim=(
                "There is a p chance under a training set whose positives were "
                "synthetically multiplied, so p is inflated. Measured: 0.358 predicted "
                "against a 0.015 base rate — 23.85x — while the unresampled model was "
                "accurate to within 1%. The ORDER of the cases is roughly preserved; the "
                "numbers are not."
            ),
            breaks=(
                "Everything that multiplies the number by something rather than sorting "
                "by it. Expected counts: a warehouse told 36% of pallets will spoil "
                "provisions for a loss that happens to 1.5%. Thresholds tied to a real "
                "quantity: 'act when probability exceeds 20%' fires on cases whose true "
                "probability is under 1%. Any figure reported as a rate to a committee, "
                "an auditor or a customer. Ranking survives, so a review queue ordered by "
                "score is unaffected — which is why the damage is invisible to teams that "
                "only ever look at the ordering."
            ),
            detection=(
                "Poor. ROC-AUC is unchanged and PR-AUC moves single digits, so the "
                "reported metrics look fine. Calibration is rarely monitored, and the "
                "probabilities stay in [0,1] and sum sensibly."
            ),
        ),
    ),
    CatalogueEntry(
        library="optuna",
        component="pruners.MedianPruner",
        versions_measured="5.0.0",
        affected_versions=(
            "present in all 5 releases measured from 1.0.0 (2020-01-14) through 5.0.0 "
            "(2026-09-07, current latest) — 6.6 years"
        ),
        resolved_in=(
            "not resolved"
        ),
        assumption="early rank predicts final rank",
        cost_when_violated=(
            "+6379% quality cost on 12/12 seeds when eventual winners look worst early, "
            "while saving MORE compute than in the favourable case (63% vs 51%). "
            "n_warmup_steps=15 recovers full quality and still saves 24%; the "
            "constructor default is 0."
        ),
        upstream_status="unstated: the docstring gives no precondition",
        evidence="docs/cold-test-optuna.md",
        span_years=6.6,
        resolution="open",
        resolved_version=None,
        check=None,
        impact=Impact(
            believed_claim="This is the best configuration found in the search.",
            actual_claim=(
                "This is the best of the trials that survived early stopping, which "
                "selected on a signal uncorrelated with the outcome. Measured: +6379% on "
                "the objective, 12 of 12 seeds, while saving MORE compute than in the "
                "favourable case (63% vs 51%)."
            ),
            breaks=(
                "The claim that a search space was explored. The write-up says 200 "
                "candidates were tried; at the measured prune rate 126 were discarded on "
                "evidence that did not predict the result, so the search that happened "
                "was over 74. Whatever the configuration controls — a routing policy, a "
                "dosing schedule, a picking order in a warehouse — the deployed one is "
                "not the best one searched, and the record says it is."
            ),
            detection=(
                "Only by re-running without the pruner and comparing, which nobody does: "
                "the run completed, reported a best value, and was faster."
            ),
        ),
    ),
    CatalogueEntry(
        library="scikit-learn",
        component="model_selection.train_test_split",
        versions_measured="1.9.1",
        affected_versions=(
            "present in all 8 releases measured from 0.22.2.post1 (2020-03-04) through 1.9.1 "
            "(2026-09-10, current latest) — 6.5 years, plus 5 further in-span releases "
            "confirmed independently. What is invariant is the ABSENCE of group support, of "
            "any warning, and of the words group/independent/leak/subject/cluster in the "
            "docstring — not the code, which changed signature at 0.24.2 and grew its "
            "docstring from 2,904 to 4,997 characters. Versions before 0.22.2.post1 could "
            "not be installed"
        ),
        resolved_in=(
            "not resolved"
        ),
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
        span_years=6.5,
        resolution="open",
        resolved_version=None,
        check="check_split",
        impact=Impact(
            believed_claim="This model gets it right this often on cases it has not seen.",
            actual_claim=(
                "This model gets it right this often on cases from subjects it trained "
                "on. Measured: 92% of subjects present in both splits with zero identical "
                "rows, accuracy overstated 14.8% and ROC-AUC 9.5%, on 12 of 12 trials."
            ),
            breaks=(
                "Every downstream commitment made against the number. A staffing level "
                "sized to the reported error rate; a threshold chosen to hold a "
                "false-positive rate; an acceptance gate a model passed; a claim to a "
                "regulator, a customer or a committee that the system performs at a "
                "stated level. The shortfall appears only after deployment, at roughly "
                "the measured gap, and arrives looking like drift."
            ),
            detection=(
                "The failure looks like SUCCESS, which is the worst case in this "
                "catalogue. A model scoring 0.95 instead of 0.83 does not get "
                "investigated. It surfaces as unexplained underperformance in production, "
                "usually blamed on the data."
            ),
        ),
    ),
    CatalogueEntry(
        library="boto3",
        component="list/scan/query operations",
        versions_measured="1.43.96",
        affected_versions=(
            "present at all 11 releases sampled from 1.4.4 (2017-01-16) through 1.43.96 "
            "(2026-09-16, current latest) — 9.7 years. 11 of 2,078 releases in that range "
            "(0.53%), largest untested gap 416 consecutive releases. The truncation is "
            "server-side and the backend was held fixed, so what the sweep establishes is "
            "the negative result: boto3 never grew a call-site signal. The exact row counts "
            "are harness-dependent and are not version-range constants"
        ),
        resolved_in=(
            "not resolved"
        ),
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
        span_years=9.7,
        resolution="open",
        resolved_version=None,
        check="check_paginated",
        impact=Impact(
            believed_claim="These are the things that are there.",
            actual_claim=(
                "These are the first page of things that are there, and the page size is "
                "not a property you chose. Measured: 1,000 of 2,500 S3 objects (40%), and "
                "49 of 400 DynamoDB rows (12%) once rows widened to 20 KB — the same code "
                "against the same table."
            ),
            breaks=(
                "Any statement of completeness. A backup that reports success holds 40% "
                "of the files. A stock take enumerating bins counts the first thousand "
                "and reports a total. A retention sweep deletes a page, leaves the rest, "
                "and looks idempotent while never converging. A compliance scan attests "
                "that every object was checked, having checked 40% — and the attestation "
                "is the product. The DynamoDB form is worse: the coverage moves when "
                "someone adds a column, so a job that was complete last quarter is not "
                "this quarter, with no change to the code."
            ),
            detection=(
                "Very poor, and there is no ceiling to learn: S3 stops at a round 1,000 "
                "that someone might eventually recognise, DynamoDB stops at 1 MB so the "
                "count varies with row width. Nothing raises, the exit status is zero, "
                "and the job reports completion."
            ),
        ),
    ),
    CatalogueEntry(
        library="packaging",
        component="SpecifierSet",
        versions_measured="24.0",
        affected_versions=(
            "present from 14.3 (2014-11-20) — the first release that shipped packaging.specifiers "
            "at all, so the defect has existed for the entire lifetime of the API — through "
            "25.0 (2025-04-19) for the full 18-of-60 behaviour, measured at 24 releases. "
            "The exact-pin-accepts-a-local-build half survives the fix and is still present "
            "and still silent at 26.3 (2026-08-04, current latest): 11.7 years unresolved"
        ),
        resolved_in=(
            "partially: 26.0 (2026-01-21), already in 26.0rc1 — the pre-release default flips and 16 of the 18 disagreements disappear, measured at all seven 26.x releases (2 of 60, 3.3%). The remaining 2 of 60, which this entry rates the more severe direction, are NOT resolved. The 26.x change is itself silent (0 warnings), so upgrading past 25.0 reverses the pre-release behaviour without saying so"
        ),
        assumption=(
            "the caller cares only about ordering — not whether a candidate is a "
            "pre-release, or carries a local build segment"
        ),
        cost_when_violated=(
            "30% of 60 specifier/version pairs disagree with plain ordering, in both "
            "directions. 16 too strict: '>=1.0' rejects 2.0rc1, 2.0b2, 2.0a1 and "
            "2.0.dev1, all of which order above 1.0. 2 too loose: '==2.0' accepts "
            "2.0+local and 2.0+ubuntu1 — and 2.0+patched.by.vendor. 0 exceptions, 0 "
            "warnings; every answer is a plain True or False and both are plausible."
        ),
        upstream_status=(
            "specified: both behaviours are PEP 440 and documented, and prereleases= "
            "exists. Nothing at the call site says the constraint does not mean what it "
            "reads as."
        ),
        evidence="docs/cold-test-packaging.md",
        span_years=11.7,
        resolution="partial",
        resolved_version="26.0",
        check="check_specifier",
        impact=Impact(
            believed_claim="I pinned this to exactly version 2.0.",
            actual_claim=(
                "I pinned this to 2.0 or any local build labelled 2.0+anything. Measured: "
                "SpecifierSet('==2.0') accepts 2.0+local, 2.0+ubuntu1 and "
                "2.0+patched.by.vendor. Separately, '>=1.0' rejects 2.0rc1 and 2.0.dev1, "
                "which order above 1.0 — 30% of 60 pairs depart from ordering."
            ),
            breaks=(
                "Two different things, in opposite directions. The loose direction breaks "
                "any statement that a specific artifact is what runs: an exact pin is "
                "what people write when they mean this build and no other, and it accepts "
                "a rebuilt or vendor-patched one carrying the same base version. An "
                "attestation that the audited artifact is deployed does not hold. The "
                "strict direction breaks availability of anything published as a "
                "pre-release: a fix shipped as 2.0rc1 does not satisfy '>=1.0', so a "
                "resolver reports no matching version while one orders above the bound, "
                "and a team concludes the fix is unavailable."
            ),
            detection=(
                "Poor in both directions. The result is a boolean, and False reads as "
                "'no such version' rather than 'excluded by a rule you did not state'. "
                "The loose direction is worse still: the pin resolves, the install "
                "succeeds, and the version string in the lockfile is the one you asked "
                "for."
            ),
        ),
    ),
    CatalogueEntry(
        library="idna",
        component="encode vs the stdlib 'idna' codec",
        versions_measured="idna 3.11, CPython 3.11 codec",
        affected_versions=(
            "present, with all 12 per-domain outputs byte-for-byte identical, in every one of the "
            "34 releases that install on CPython 3.11 — 0.6 (2014-04-29), 1.1 (2015-01-27), "
            "and every release from 2.0 (2015-05-30) through 3.20 (2026-09-17, current "
            "latest) — measured exhaustively, not sampled. 12.4 years. Eight releases "
            "(0.2-0.5, 0.7-1.0) will not install on a modern interpreter, so 0.6 is an "
            "install island rather than a contiguous floor. The uts46=True sub-claim holds "
            "from 2.0 onward; the kwarg does not exist at 0.6 or 1.1"
        ),
        resolved_in=(
            "not resolved — upstream treats the divergence as by design"
        ),
        assumption="encoding a domain name is deterministic — one input, one host",
        cost_when_violated=(
            "7 of 12 internationalised domains (58%) encode differently under the two "
            "standards, and 5 of those produce two separately registrable names: "
            "'strasse.de' encodes as 'xn--strae-oqa.de' under IDNA 2008 and as "
            "'strasse.de' under IDNA 2003. Two cases split further — one encoder accepts "
            "and the other refuses. Umlauts, accents and CJK are unaffected, so a test "
            "suite using 'bucher.de' or a CJK name sees nothing. uts46=True does not "
            "reconcile them. 0 exceptions on the paths that disagree, 0 warnings."
        ),
        upstream_status=(
            "by design: the two standards differ deliberately and both packages document "
            "which they implement. Neither says the other is also installed and reachable "
            "from the same interpreter."
        ),
        evidence="docs/cold-test-idna.md",
        span_years=12.4,
        resolution="open",
        resolved_version=None,
        check="check_domain_encoding",
        impact=Impact(
            believed_claim="I am talking to the domain the user gave me.",
            actual_claim=(
                "I am talking to one of two different domains, decided by which code path "
                "encoded it. Measured: 7 of 12 names disagree, and for 5 of them both "
                "results are valid registrable hosts — the German sharp s yields "
                "'xn--strae-oqa.de' or 'strasse.de', which are not the same place."
            ),
            breaks=(
                "Anything that encodes a name in one place and uses it in another. An "
                "allowlist or blocklist checked with one encoder and dereferenced with "
                "the other compares two different hosts, so a name can be absent from the "
                "list that was checked and present in the request that was sent. A log or "
                "audit trail records a host that was not the one contacted. Deduplication "
                "counts one domain as two, or two as one. Certificate matching, mail "
                "routing and cache keys all inherit the same split. The ligature and "
                "dotted-capital cases go further: one encoder refuses the name outright "
                "while the other resolves it, so a validation step and a fetch step "
                "disagree about whether the input is a domain at all."
            ),
            detection=(
                "Very poor, and the usual test data hides it. Umlauts, accents and CJK "
                "encode identically under both standards, so a suite exercising "
                "'bucher.de', 'cafe.fr' or a Japanese name passes. Only the handful of "
                "characters the standards changed expose it, and both outputs are "
                "well-formed names that resolve."
            ),
        ),
    ),
    CatalogueEntry(
        library="urllib3",
        component="util.retry.Retry",
        versions_measured="2.6.3",
        affected_versions=(
            "present at 11 releases measured (plus 5 added by independent re-measurement) from "
            "1.9 (2014-07-07, the release that introduced util.retry.Retry) through 2.8.0 "
            "(2026-09-15, current latest) — 12.2 years. Behaviourally unchanged, but NOT "
            "byte-identical: retry.py has ~20 distinct revisions over the span and grew "
            "9,549 to 20,151 bytes. check_retry's third gap cannot fire before 1.26.0, "
            "where allowed_methods did not yet exist"
        ),
        resolved_in=(
            "not resolved — though 2.8.0 is the first release ever to attach a deprecation to Retry.__init__ (a FutureWarning that an empty allowed_methods will skip retries for all verbs in v3.0). The three gaps this entry measures still emit nothing"
        ),
        assumption=(
            "the caller wants connection-level retries only, spaced by nothing, on "
            "methods the library judged idempotent"
        ),
        cost_when_violated=(
            "Measured on the wire against a local server returning 503 and counting the "
            "requests that arrive: Retry(total=3) sends 1 request. No retry at all — "
            "status_forcelist is empty by default, so HTTP statuses are not retried. "
            "Adding status_forcelist=[503] gives 4 requests in 0.00 seconds, because "
            "backoff_factor defaults to 0. Setting allowed_methods=None to make a POST "
            "retry replays the non-idempotent request 4 times. 0 exceptions on the first "
            "configuration, 0 warnings on any of them."
        ),
        upstream_status=(
            "documented: every default is in the Retry docstring and the defaults are "
            "defensible in isolation. Nothing at the call site says that Retry(total=3) "
            "and 'retry on failure' are different things."
        ),
        evidence="docs/cold-test-urllib3.md",
        span_years=12.2,
        resolution="open",
        resolved_version=None,
        check="check_retry",
        impact=Impact(
            believed_claim="I configured retries, so transient failures are handled.",
            actual_claim=(
                "I configured retries for connection and read errors. Measured: against a "
                "503, Retry(total=3) sent 1 request and returned the error. Once statuses "
                "are added, the 4 attempts arrive within 0.00 seconds. Once methods are "
                "opened up so a POST retries, the POST is sent 4 times."
            ),
            breaks=(
                "Three different things, and fixing the first tends to cause the others. "
                "A service that reports it has retries surfaces every upstream 503 as a "
                "hard failure, so an operator tunes timeouts and capacity against a "
                "resilience layer that was never engaged. Once statuses are retried with "
                "no backoff, a struggling dependency receives four times the traffic in "
                "the instant it is least able to serve it — the retry layer amplifies the "
                "outage it was added to survive. And once methods are opened up, a "
                "non-idempotent request is replayed: an order placed four times, a stock "
                "movement recorded four times, a payment instruction submitted four "
                "times. The server saw four valid requests and has no way to know three "
                "were the same intent."
            ),
            detection=(
                "Poor for the first, and inverted for the third. A retry that never "
                "happened looks exactly like one that did not help, so the missing "
                "retries surface as an error rate nobody attributes to configuration. The "
                "duplicate-POST case is worse: nothing fails at all. Every request "
                "returned 2xx, the client is satisfied, and the duplicates are discovered "
                "later by whoever reconciles the records."
            ),
        ),
    ),
    CatalogueEntry(
        library="requests",
        component="Response.text",
        versions_measured="2.33.1",
        affected_versions=(
            "present, silent, and identical on every defect-specific measure in all 9 releases "
            "sampled from 2.2.0 (2014-01-09) through 2.34.2 (2026-05-14, current latest) — "
            "12.4 years. The source line `if \"text\" in content_type: return \"ISO-8859-1\"` "
            "is byte-identical in 82 of the 83 non-prerelease 2.x releases. The remedy is "
            "weaker on older versions than the headline suggests: apparent_encoding scores "
            "12/12 on 2.31+ but degrades to 9/12 at 2.18.4-2.25.1 and 7/12 at 2.9.2. The "
            "application/json row is not invariant — it returned None before 2.25.1"
        ),
        resolved_in=(
            "not resolved"
        ),
        assumption=(
            "a text/* response that omits charset is Latin-1, per RFC 2616 §3.7.1 — a "
            "default RFC 7231 removed in 2014"
        ),
        cost_when_violated=(
            "Over 12 UTF-8 bodies served as text/plain with no charset, measured on the "
            "wire: r.text was correct 0/12, r.apparent_encoding was correct 12/12. All "
            "35 non-ASCII characters in the corpus were mangled, len(r.text) was wrong on "
            "12/12 bodies (+43 characters over-counted in total), and there were 0 "
            "exceptions and 0 warnings. The same rule is a substring test, so "
            "application/x-subrip-text is treated as legacy text, and it is "
            "case-sensitive, so 'text/plain' mojibakes while 'TEXT/PLAIN' — the same media "
            "type, case-insensitive per RFC 9110 §8.3.1 — decodes correctly."
        ),
        upstream_status=(
            "working-as-intended and documented: Response.text says 'following RFC 2616 to "
            "the letter'. The letter of RFC 2616 was superseded in 2014. Nothing at the "
            "call site distinguishes a charset the server declared from one requests "
            "assumed."
        ),
        evidence="docs/cold-test-requests.md",
        span_years=12.4,
        resolution="open",
        resolved_version=None,
        check="check_response_encoding",
        impact=Impact(
            believed_claim="This is the text the server sent.",
            actual_claim=(
                "This is the body reinterpreted under a 1999 default the server never "
                "asked for. Measured: 0 of 12 UTF-8 bodies served as text/plain came back "
                "correct, every one of the 35 non-ASCII characters was replaced by two or "
                "three others, and len() was wrong on all 12."
            ),
            breaks=(
                "Two things, and the second is worse than the mojibake. Anything that "
                "matches a string stops matching: a product name, a supplier, a city, a "
                "patient surname read back from an API no longer equals the record it was "
                "written from, so a lookup returns nothing and the caller handles a "
                "missing row rather than a wrong one. And anything that counts characters "
                "counts wrong — 'café' arrives as 5 characters instead of 4. A column "
                "width, a field limit, a per-character price, a quantity parsed out of a "
                "text response: the number is off by exactly the number of accented "
                "characters upstream, which is data-dependent and nobody's constant. If "
                "the inflated string is then truncated to a stored width the damage stops "
                "being recoverable: of 37 truncation points on one 33-character string, 4 "
                "raise on repair and 31 repair to different content than the original "
                "prefix. r.json() inherits it whenever the server labels JSON as "
                "text/plain or text/json, so structured data is affected too."
            ),
            detection=(
                "Worst case, and the reason it reaches production. An ASCII body decodes "
                "identically under both encodings, so every test written against ASCII "
                "fixtures passes. Latin-1 maps all 256 byte values, so the decode cannot "
                "raise — there is no byte sequence that signals the guess was wrong. The "
                "failure appears only when real data carries an accent, and it appears as "
                "cosmetic 'weird characters' that get patched at the display layer while "
                "the counts and the lookups stay wrong."
            ),
        ),
    ),
    CatalogueEntry(
        library="charset-normalizer",
        component="detect / from_bytes(...).best()",
        versions_measured="3.4.6",
        affected_versions=(
            "present in all 16 releases measured from 0.3.0 (2019-09-12) through 3.5.1 "
            "(2026-08-15, current latest) — 6.9 years, always silent, 0 exceptions and 0 "
            "warnings, with 45-65% of a clean legacy-encoded corpus round-tripping to a "
            "different string at every version. The confidence field became harder to guard "
            "against at 2.0.0 (2021-07-02): at 1.4.1 wrong answers span 0.849-1.000 against "
            "0.966-1.000 for correct ones (already overlapping), and from 2.0.0 every answer "
            "on clean text is exactly 1.000. Versions below 0.3.0 were not tested"
        ),
        resolved_in=(
            "not resolved — the underlying ambiguity is genuinely unfixable, so the entry is about silent unqualified reporting, not detection accuracy"
        ),
        assumption=(
            "a successful decode is evidence the encoding is right — true for UTF-8, "
            "false for every single-byte encoding, where all 256 byte values decode"
        ),
        cost_when_violated=(
            "20 sentences in 20 legacy encodings: 8 round-trip to a DIFFERENT string "
            "(40%) and only 6 of 20 named the right encoding, with 0 exceptions and 0 "
            "warnings. The same 20 texts encoded UTF-8 instead: 20/20 correct. "
            "detect() reports confidence = 1.0 - chaos, and chaos measures whether the "
            "output looks like text, which a wrong single-byte decode also does: 7 of "
            "the 8 wrong answers came back at confidence 1.000, and no threshold "
            "separates right from wrong (wrong 0.900-1.000, correct 0.938-1.000). "
            "On 40 European surnames misread iso-8859-1 as cp1250, 14 (35%) were "
            "silently altered and 0 of the 14 changed length."
        ),
        upstream_status=(
            "the ambiguity is genuine and unfixable — single-byte encodings really are "
            "indistinguishable at the byte level. What is reported is not: confidence is "
            "computed as 1.0 - chaos in legacy.detect, which measures legibility rather "
            "than correctness, and upstream has already patched one symptom of this "
            "(a -0.2 adjustment below 32 bytes, jawah/charset_normalizer#391) without "
            "changing what the number means above it."
        ),
        evidence="docs/cold-test-charset-normalizer.md",
        span_years=6.9,
        resolution="open",
        resolved_version=None,
        check="check_detected_encoding",
        impact=Impact(
            believed_claim="I decoded this file, and the detector was 100% confident.",
            actual_claim=(
                "I picked one of several readings that all decode without error, and the "
                "confidence number reports that the result looks like text — not that it "
                "is the right text. Measured: 8 of 20 legacy-encoded sentences decoded to "
                "a different string, 7 of those 8 at confidence 1.000."
            ),
            breaks=(
                "Identity, quietly, and it is the same character count either way. A name "
                "read in from a legacy CSV, an older system's export or an uploaded file "
                "arrives altered but well-formed: Muñoz becomes Muńoz, João becomes Joăo, "
                "Bjørn becomes Bjřrn. 35% of a 40-name European surname sample was changed "
                "this way and NONE of them changed length, so every field-width check, "
                "every truncation check and every not-null check passes. Downstream, the "
                "altered value no longer matches the record it belongs to, so a customer "
                "is created rather than found, a duplicate ledger is opened under a name "
                "that differs by one diacritic, a de-duplication pass leaves both rows, "
                "and a search for the real name returns nothing. Nothing reconciles to the "
                "wrong total — the totals are fine. The join is what is broken."
            ),
            detection=(
                "Effectively none, and the confidence field actively misdirects. There is "
                "no exception, no warning, and the number the caller would check reads "
                "1.000 on the wrong answers. Worse, whether a given text survives depends "
                "on which characters it happens to contain: iso-8859-1 and cp1250 agree on "
                "177 of 256 byte values, so a German sentence read as cp1250 changes 0 "
                "characters and the Spanish sentence next to it changes 3. German test "
                "fixtures pass while Spanish production data is altered."
            ),
        ),
    ),
    CatalogueEntry(
        library="cryptography",
        component="x509.Certificate.not_valid_after",
        versions_measured="3.4.8, 36.0.2, 39.0.2, 41.0.7, 42.0.8, 43.0.3, 45.0.7, 50.0.1",
        affected_versions=(
            "silent in every release measured from 3.4.8 (2021-08-24) through 41.0.7 "
            "(2023-11-28) — a 2.4-year span, and the range Debian stable ships"
        ),
        resolved_in="42.0.0 (2024-01-23)",
        assumption=(
            "the caller will compare this naive UTC value against another UTC value — not "
            "against datetime.now(), which is naive local time"
        ),
        cost_when_violated=(
            "The error equals the host's UTC offset, up to 14 hours in either direction. "
            "Measured on 41.0.7 across 10 real timezones with the comparison every "
            "monitoring script writes (cert.not_valid_after < datetime.now()): a "
            "certificate that expired 6 hours ago READS AS VALID in 3 of 10 "
            "(America/Los_Angeles, Pacific/Honolulu, Pacific/Midway), and one with 6 hours "
            "left reads as expired in 3 others (Kiritimati, Auckland, Tokyo). 0 exceptions "
            "and 0 warnings on any release before 42.0.0. From 42.0.0 the attribute emits "
            "CryptographyDeprecationWarning and not_valid_after_utc exists, so the same "
            "code is LOUD there — measured at 42.0.8, 43.0.3, 45.0.7 and 50.0.1."
        ),
        upstream_status=(
            "resolved: deprecated in 42.0.0 in favour of not_valid_after_utc. The entry "
            "stays because the affected range is still widely installed, and because the "
            "fix is the answer a reader on that range needs."
        ),
        evidence="docs/cold-test-cryptography.md",
        span_years=2.4,
        resolution="fixed",
        resolved_version="42.0.0",
        check="check_certificate_dates",
        impact=Impact(
            believed_claim="This certificate has not expired yet.",
            actual_claim=(
                "This certificate has not expired, in a timezone that may not be the one "
                "issuing the certificate. Measured across 10 deployment timezones on "
                "41.0.7: the answer is wrong in 6 of them, by exactly the host's UTC "
                "offset, and wrong in the unsafe direction in 3."
            ),
            breaks=(
                "An expiry gate, in both directions, and the two failures land on "
                "different people. Fail-open — anywhere west of about UTC-5 — a "
                "certificate that has already expired is accepted for up to 11 more "
                "hours, so a service keeps trusting a credential past its stated life and "
                "an audit that asks 'were any expired certificates accepted' answers no "
                "from the same broken comparison. Fail-closed — anywhere east of about "
                "UTC+7 — renewal alarms fire up to 14 hours early, every time, until "
                "someone widens the threshold to silence them and the real warning window "
                "goes with it. The same line of code does both, and which one you get "
                "depends on where the host is, not on what you wrote."
            ),
            detection=(
                "None on the affected range, and the naive comparison is the one that "
                "reads correctly. Both operands are naive so Python compares them without "
                "complaint — there is no TypeError, which is the error Python raises when "
                "you mix aware and naive values and the reason this looks safe. It is also "
                "invisible in CI, because build hosts run at UTC, which is the one offset "
                "where the comparison is right."
            ),
        ),
    ),
)
