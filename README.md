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
