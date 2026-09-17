# Does the new audit process produce a better first draft?

**Registered 2026-09-17, before any result was seen.** Three adversarial verifications of
published entries were launched and this file was written while they ran. Nothing here is
adjusted afterwards; results go in a separate section below.

## The question

`docs/PROCESS.md` and `staging/` added, between audit 13 and audit 14: hypotheses
registered before measuring, version ranges required, every measurement required to carry a
number, a promotion gate, and adversarial verification.

Of those, the gate and the verifier are **detection** — they catch defects after the draft
exists. Pre-registration, required ranges and required numbers are **production** — they
should change the draft itself.

**Detection is already proven better and is not in question:**

| | audits 1–13 | audit 14 |
| --- | --- | --- |
| adversarial rounds | 0 | 2 |
| gate refusals | 0 | 3 |
| defects caught before publication | 0 recorded | **12** |
| defects reaching the catalogue | unknown | **0** |

**Production is the open question, and it is unmeasured.** Audit 14's first draft contained
**8** defects despite the new production controls. That is n=1, against n=0 for the old
process, and no comparison can be drawn from it.

## The experiment

Put three published entries — `requests`, `urllib3`, `packaging` — through the identical
adversarial treatment audit 14 received, and count distinct defects per entry. Same
instruction to the verifier ("your job is to refute, default to refuted when uncertain,
write your own probes"), same demand for a defect count.

Subjects were chosen for spread across defect kinds, not for expected result: encoding
semantics, configuration semantics, version-comparison semantics. All three have a check
and a test suite. All three have already had their version ranges corrected by the sweep of
2026-09-17.

## Prediction, written before the results

**3 to 6 defects each**, i.e. fewer than audit 14's 8.

Not because the old process was better. Two reasons that have nothing to do with process
quality:

1. The version-range sweep already found and fixed one whole class of defect in these
   entries — 8 of 11 boundary claims were narrowed. Audit 14 had no such prior pass.
2. pluggy's hook ordering is a genuinely subtler subject than "is this body UTF-8". Subject
   difficulty is not held constant.

## The interpretation rule, fixed in advance

This comparison is **confounded**, and the rule for reading it is written here before the
numbers arrive so it cannot be chosen afterwards:

* **Old entries come back with FEWER defects than 8** → *does not* show the old process was
  better. Both confounds above push that way. The most it supports is that the new process
  has not been shown to improve the draft.
* **Old entries come back with MORE defects than 8** → evidence the new production controls
  help, because the confounds push the other way and the result would be against them.
* **Roughly equal** → the production controls are not doing measurable work, and the gain is
  all in detection. That would be worth knowing: it would say keep the gate and the
  verifier, and stop claiming pre-registration improves the draft.

In **every** one of those three cases, detection stays proven and the verifier stays. The
only thing at stake is whether pre-registration and the required-number rule earn their
keep.

**A defect count above zero on any of the three is also, separately, a finding about the
published catalogue** — those entries are in it now.

## Results

*(empty — the verifications were still running when this was written)*
