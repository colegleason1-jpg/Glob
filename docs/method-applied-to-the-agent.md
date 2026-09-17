# What the engine's discipline did to the agent applying it

2026-09-17

## The claim, and its limit stated first

The claim worth testing: the supply-chain engine's core discipline — separate what was
measured from what was asserted, refuse rather than hedge, make every number trace to a
stated input — is not domain-specific. It is a general method, and it improves the output
of anything that adopts it, including an AI system.

**The limit, stated before the evidence:** this session *began* with that repository, so
there is no clean control period. What follows is not a before/after experiment. It is a
within-session record of unmeasured claims being caught, and of who caught them. Read it
as an existence proof that the discipline binds on an agent's own output, not as a
measurement of how much.

Two further honesty notes: several catches below happened because the user's instructions
demanded measurement, not purely on the agent's initiative. And the agent still repeated
one ordinary mistake twice (see the last row).

## The record

Every row is a claim the agent made, and what happened to it.

| # | The claim, as made | What measurement found |
| --- | --- | --- |
| 1 | Token routing saves ~51% | 21.6% once decisions were made on *believed* quality and graded on *true* quality. The gap was the optimizer's curse, not a result. |
| 2 | Agent workflows will escape the allocation degeneracy | 99% pure allocations at 200 decisions — identical to routing. Prediction failed; reported as a failure. |
| 3 | "Confidence language gets stripped at the first summarization step" | Wrong mechanism. Nothing is stripped, because nothing is attached. Provenance dies at the serialization boundary; no summarizer is needed. |
| 4 | The false-positive rate comes from the bootstrap's block length being shorter than the session length | Forcing the block to session length moved 12.0% → 12.3%. Not the mechanism. The cause was heteroskedasticity from the rate denominator. |
| 5 | "The min-calls fix is free — no vendors lost" | True only at the traffic density assumed. At 2–10 calls/hour a flat floor makes *every* vendor unfittable. The first version broke an existing test. |
| 6 | The Cortex 3 seth term can flip 0 of 6 task types | Analytical bound too coarse. The direct test found 3 decisions changed in 1,500. |
| 7 | Build the custody API first — it has the moat | Sequencing on defensibility before demand is backwards. Recognised only after writing "the market is asserted, not measured" two sections earlier in the same memo. |
| 8 | A MILP-vs-fallback comparison showing 400/400 agreement | **Vacuous.** scipy was not installed, so both arms ran the same code. Caught by noticing the solver field said `deterministic-binary-fallback` on every row. |
| 9 | Kill God enemy attack is 0 and budget utilisation is 0% | Wrong dict keys (`atk` not `attack`, `spent` not `net_capital`). Caught before reporting, because two zeros in a row were implausible. |
| 10 | `AttainabilityReport.more_capital_would_help` | Does not exist; the property is `is_budget_limited`. **Made this same mistake twice in one session.** Caught by a test both times, not by reasoning. |

## What the record supports

**Nine of ten were caught by running something, not by thinking harder.** In every case
the analytical argument was clean and the conclusion was wrong. Rows 4 and 6 are the
sharpest: both were correct-sounding mechanical explanations that survived scrutiny and
died on contact with a measurement that took under a minute to write.

**The discipline is what produced the catches, not care.** Rows 8 and 9 are near-misses —
findings that would have been reported as real had a sanity check not been habitual. Both
were caught by the same reflex the engine's provenance rows encode: a number with no
evidence behind it is not a number yet.

**It generalises across domains because it is about evidence, not subject matter.** The
same method found a heteroskedasticity defect in LLM route logs, an argmax masquerading as
a mixed-integer program, a label naming the wrong remedy 400 times out of 400, and a
cardinality constraint missing from a game engine's upstream library.

## What it does not support

It does not show the agent was worse before, because there is no before. It does not
isolate the method from the instructions that invoked it. And row 10 shows the discipline
does not prevent ordinary errors — it catches them, which is a different and more modest
claim.

That more modest claim is the defensible one: **the method does not make the reasoner
right. It makes being wrong survivable and visible, fast enough to matter.**

## Why this is the strongest evidence in the whole exercise

Every other finding this session was the method applied to someone else's code, where the
agent had every incentive to find something. This record is the method applied to the
agent's own output, where it had every incentive to find nothing — and it found ten.
