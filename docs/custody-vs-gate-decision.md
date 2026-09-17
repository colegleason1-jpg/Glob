# Custody vs Gate — the decision after the Chat-Johnson tests

2026-09-16

## Short answer

The gate — but not the gate originally pitched, and custody is **too early** rather
than wrong. Both theses moved. Neither moved as predicted.

## What the test did to the gate thesis

Stated kill criterion: *if each new domain needs new reasons, it is a checklist, not a
product.* One domain (LLM vendor failure under load) needed:

- one reason **mis-ordered** — `WRONG_SIGN` is decided on the point estimate's sign
  before the interval is consulted, so 39% of true nulls read as a real inverted effect
- one reason **missing entirely** — per-observation precision; the taxonomy guards thin
  evidence in aggregate but has no notion of how precisely a single point was measured
- and that missing reason **could not be a constant** — a flat threshold was catastrophic
  at light traffic (every vendor unfittable), so it had to be self-limiting

So the fixed taxonomy does not generalize as a fixed taxonomy. That half failed.

What did generalize: the machinery (91–100% power on a completely different domain) and
the discipline — enumerate how the data can fail to support the claim, then refuse rather
than hedge. But a discipline is a library and a doc, not an API. Nobody pays per call for
a methodology.

**The sellable artifact is the measurement, not the taxonomy.** The valuable output was
one sentence nobody had: *the estimator reports USABLE on 13% of vendors that have no
load/failure relationship at all.* Producing it needed a synthetic null, a run of the
real pipeline, and a count.

Known weakness, stated up front: generating a domain-appropriate null is itself
domain-specific, so a measurement service inherits the same generalization problem. It is
better positioned than the taxonomy, not immune to the same objection.

## What the test did to the custody thesis

**Confirmed, and independently discovered.** `orchestrator/router.py:2187`,
`CRITIQUE_CUT_NOTE`: the critique agent needed to know the draft had been cut off by the
token budget, there was no channel for that, so one signal was hardcoded as a string
append to the critique's system prompt. Someone building a multi-agent system hit the
provenance-loss problem without looking for it.

**And the same fact is the strongest argument against the product.** That fix was one
line and it was free. No signing service was needed — a field in the JSON was.

Custody's value depends entirely on the serializer being untrustworthy. In a single-owner
pipeline — Chat-Johnson, and nearly every agent system shipping today — you serialize
your own data and can simply include the provenance. Signing buys nothing against
yourself.

A correction to an earlier claim: the assertion that "confidence language gets stripped at
the first summarization step" was wrong in mechanism. Nothing is stripped, because nothing
is ever attached. Provenance dies at the **serialization boundary**, not at summarization.
No summarizer is required to lose it. The metadata channel (`RouteDecision`) survives and
even accumulates; the content channel carries text only; the next agent sees only the
content channel.

So: a real problem, with a cheap self-serve fix now, and an expensive vendor fix that pays
only once pipelines cross trust boundaries between parties. Those largely do not exist yet.
That is "too early", which is a more specific verdict than "the market is unvalidated".

## Recommendation

Do the gate work, aimed at measurement rather than taxonomy.

1. Run the false-positive measurement against the other judgement points in Chat-Johnson —
   the Cortex 2 MILP routing decisions, the `Verdict` statuses, the quality priors in the
   Cortex learner. Today one was measured and it carried a 5x error inflation nobody knew
   about.
2. If two or three more come back with real numbers, there is a repeatable thing. If they
   come back clean, the elasticity case was a one-off and the thesis should be dropped.

A week, no building. It either produces a product thesis or kills one cheaply.

## What would reverse this

One thing: a pipeline where agents from **different owners** exchange numbers under audit.
If such a pipeline can be named, custody stops being early and the order flips. None was
found in the code, and a market survey is not something this analysis could run.

## Provenance of the claims above

Measured: the 91–100% power, the 13%/5%/2.5% false-USABLE rates by traffic density, the
39% WRONG_SIGN rate, the CRITIQUE_CUT_NOTE mechanism and the two-channel structure.
Asserted: that multi-party agent pipelines are rare today, and that a measurement service
would find buyers. Neither was tested.
