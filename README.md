# Supply Chain Resilience & Capital Allocation Engine

[![tests](https://github.com/colegleason1-jpg/supply-chain-resilience-engine/actions/workflows/tests.yml/badge.svg)](https://github.com/colegleason1-jpg/supply-chain-resilience-engine/actions/workflows/tests.yml)

Decides how to spend a fixed resilience budget across supply chain interventions, and — the
part that matters — is able to show why. Every currency figure traces to a stated input,
every assumption that is an assumption says so on screen, and the numbers that were measured
are separated from the numbers somebody typed.

It replaces an acquired single-file system whose eighteen catalogued defects included a
solver that reported an infeasible problem as optimal, a correlation repair that silently
rescaled every simulated node, and a market mapping that matched everything when a column
was missing. All eighteen are now pinned by tests. The reasoning is in
[`engine/docs/ADR-001-objective-reformulation.md`](engine/docs/ADR-001-objective-reformulation.md).

## Two pieces

| | What it is | Depends on Streamlit? |
| --- | --- | --- |
| [`engine/`](engine/README.md) | `scrcae` — the headless optimiser, simulator, and calibration estimators. Importable, installable, testable without a UI. | no |
| [`app/`](app/README.md) | The Streamlit client. Editors, presenters, persistence, auth, and the audit ledger. A consumer of the engine. | yes |

The separation is not decoration. It is what makes the solver exercisable headlessly, and it
is why there are 700 tests instead of a manual checklist.

## Running it

```bash
pip install -r requirements-dev.txt
python -m pytest -q                     # 700 tests
python -m streamlit run app/main.py
```

Installing `requirements.txt` puts `engine/` on the path as a real package, so `import
scrcae` works without `PYTHONPATH`. Needs Python 3.12 or newer.

## Seeing the interesting part

Market exposure adjusts an intervention's effectiveness by how far a commodity has moved
from its anchor price. That adjustment needs a risk elasticity, and an elasticity somebody
typed into a box is an assumption wearing the costume of a measurement.

So the app fits it from delivery history, and refuses to when the history cannot support it:

```
Entered 0.30, fitted 1.21 — the entered value is 0.25× the fit, below it.
Elasticity 1.21 (95% interval 1.03 to 1.44), R² 0.73, from 60 periods of which 30 above anchor.
```

Adopting that fit moves the audit ledger's provenance row from `2 asserted` to
`2 calibrated`, and the count is derived by matching each exposure against a stored fit —
overtype the number, or move the anchor, and it reverts to asserted on the next run.

The precise claim, which is what the tests prove: there is no free-text "source" column to
type "calibrated" into, and a label cannot outlive the evidence behind it. It is a control
against the *accidental* version — a stale fit still vouching for a number somebody has
since changed. It is **not** a security control. The stored-fit table is an unsigned local
file, so anyone who can write it can enter a matching row and earn the label; the test that
pins this says so in as many words (`app/tests/test_calibration.py`,
`test_a_forged_calibration_row_cannot_bless_an_arbitrary_number`). Making it tamper-evident
against intent rather than accident needs the evidence store to be somewhere the
application cannot write.

Screenshots of the whole path are in [`app/docs/walkthrough/`](app/docs/walkthrough/), and
`tools/` holds the scripts that produced them, so it is reproducible rather than a one-off.

## Where the old system went

[`legacy/`](legacy/README.md) holds the acquired single-file system and the forensic audit of
it. Nothing there is imported by the app or the engine — it is kept because the **F1–F13**
defect citations in ADR-001 point into it, and a claim about fixed defects is worth more when
the code that contained them is still readable. F14 onward do not point into it: ADR-001 files
those under "found by testing, not by reading", and F16 and F19 are defects in a concave
linearisation the acquired system never had. That distinction is in
[`legacy/README.md`](legacy/README.md), because the version of this sentence that claimed all
eighteen was flattering the rebuild.

## Deploying

See [`DEPLOYING.md`](DEPLOYING.md). Short version: it is a Streamlit server, so the host must
be able to upgrade WebSockets; GitHub → Streamlit Community Cloud with `app/main.py` as the
main file and Python 3.12 is the fast path. Read the three warnings about ephemeral storage,
default-off authentication, and the default market provider before sharing a public link.

## The method, turned on the agent that was applying it

The discipline this repository is built around — separate what was measured from what was
asserted, refuse rather than hedge, make every number trace to a stated input — is not
supply-chain-specific. The strongest evidence for that is not any finding in this codebase.
It is what happened when an AI agent adopted the discipline and then applied it to its own
claims over one long working session.

**The limit, stated first:** the session began with this repository, so there is no clean
before. This is not a controlled experiment. It is a record of unmeasured claims being
caught, and of what caught them.

| # | The claim, as made | What measurement found |
| --- | --- | --- |
| 1 | Token routing saves ~51% | 21.6% once decisions were made on *believed* quality and graded on *true* quality. The gap was the optimizer's curse, not a result. |
| 2 | Agent workflows will escape the allocation degeneracy | 99% pure allocations at 200 decisions — identical to routing. Prediction failed. |
| 3 | "Confidence language is stripped at the first summarization step" | Wrong mechanism. Nothing is stripped, because nothing is attached. Provenance dies at the serialization boundary. |
| 4 | The false-positive rate comes from the bootstrap block being shorter than the session | Forcing the block to session length moved 12.0% → 12.3%. Not the mechanism. The cause was heteroskedasticity from the rate denominator. |
| 5 | "The min-calls fix is free — no vendors lost" | True only at the density assumed. At 2–10 calls/hour a flat floor makes *every* vendor unfittable. The first version broke an existing test. |
| 6 | An entropy term can flip 0 of 6 routing decisions | Analytical bound too coarse. The direct test found 3 changed in 1,500. |
| 7 | Build the custody API first — it has the moat | Sequencing on defensibility before demand is backwards, two sections after writing "the market is asserted, not measured". |
| 8 | A solver-vs-fallback comparison showing 400/400 agreement | **Vacuous.** SciPy was absent, so both arms ran the same code. |
| 9 | Two measured columns reading zero | Wrong dict keys. Caught before reporting, because two zeros in a row were implausible. |
| 10 | `AttainabilityReport.more_capital_would_help` | Does not exist; it is `is_budget_limited`. **Made twice in one session**, caught by a test both times. |

Nine of ten were caught by running something, not by thinking harder. In every case the
analytical argument was clean and the conclusion was wrong. Rows 4 and 6 are the sharpest:
correct-sounding mechanical explanations that survived scrutiny and died on contact with a
measurement that took under a minute to write.

Row 10 is what keeps it honest. The discipline does not prevent ordinary errors. It catches
them. So the defensible claim is narrower than "it makes the reasoner right":

> **It makes being wrong survivable and visible, fast enough to matter.**

Every other finding recorded here is this method applied to code, where there was every
incentive to find something. That table is the method applied to the agent's own output,
where there was every incentive to find nothing — and it found ten.

The full record is in [`docs/method-applied-to-the-agent.md`](docs/method-applied-to-the-agent.md),
with the downstream measurements that produced rows 3–9 in
[`docs/downstream-measurement-log.md`](docs/downstream-measurement-log.md).

## Two defects this repository's own tests could not see

Recorded here rather than only in the log, because how they were found matters more than
what they were. Both were fixed in `engine/` and both are pinned by tests. The full suite
passed over both of them the whole time.

They surfaced when the engine was applied to a domain it was not built for. A separate
project imports `scrcae` and feeds its estimator LLM request logs — load against service
failures, in place of commodity price against delivery disruption. Neither defect is
reachable from supply-chain-shaped data, which is why 700 passing tests said nothing.

**`limited_by` named the wrong remedy when items are indivisible.** `attainable_frontier`
counted a resource as tight only when usage *reached* capacity. That is right for
continuous funding. When `min_funding_scale == max_funding_scale` — an all-or-nothing item
— usage lands on a multiple of one node's demand, so unless capacity is an exact multiple
there is stranded headroom no node can use, the row never reads as tight, and the report
falls through to `budget`. The function's own comment says "more capital is the wrong
remedy" for a supply bound, and the fall-through recommended exactly that.

> Measured on five indivisible nodes with the budget set high enough that supply was the
> only possible constraint: across **400 random capacities the supply bound was real 400
> times and named 0 times**. It fired only on exact multiples of node demand, which is
> measure-zero for real capacities. After the fix, 400/400.

**`WRONG_SIGN` was decided before the interval was consulted.** `calibrate_elasticity`
tested the point estimate's sign first, so an estimate that merely landed negative on noise
was told "a market above anchor went with fewer disruptions… that is a hedge claim and
needs a mechanism before it is used" — a statement about data that establishes nothing.
Under a true null the sign is a coin flip.

> On a true null, the correct label rose from **48.0% to 84.7%** and the mislabel rate fell
> from **39% to 2.3%** against a ~2.5% nominal for a one-sided interval. Power on a real
> effect is unchanged at **91.7%**. Both outcomes remain refusals — `is_usable` is
> untouched — so this changed what a reader is told, not what is computed.

The general lesson, which is the reason this section exists: a test suite encodes the
assumptions its author held. These were defects *in those assumptions*, so no amount of
testing from inside this repository would have reached them. What reached them was a second
domain with a different data shape.

## What it does not claim

Stated here rather than buried, because a tool that hides its own limits is the failure mode
this rebuild exists to correct:

- The risk response exponent (0.85) is inherited and uncalibrated. Delivery history cannot
  fix it — that needs variation in funding levels, not market data.
- Fitted elasticities are associations, not causal effects, and they measure risk a node
  *carries* rather than risk an intervention *removes*.
- The reported 95% interval is optimistic: it measures about 91% on independent prices and
  about 88% under realistic price persistence, at 400 replications. Read that as "roughly
  90%, and the degradation under persistence is real but small". The test that guards it
  runs 120 replications, where Monte Carlo noise is larger than the effect — at that sample
  size the two figures can swap order — so the assertion floors are set well below the
  measured values and the test proves the interval is not badly broken rather than
  resolving the persistence effect. The measurement and the runs behind it are in the
  estimator's module docstring.
