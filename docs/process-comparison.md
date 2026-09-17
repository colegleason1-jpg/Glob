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

### packaging — **13 defects**, against audit 14's 8

Verified by me directly, not adopted on the verifier's word:

| claim | measured |
| --- | --- |
| the check fires **falsely** on `~=` | `check_specifier("~=1.4", ["1.3","1.4","1.5","2.0"])` fires with *"excludes 2 version(s) that order above the bound, because they are pre-releases (e.g. '1.3')"*. There are no pre-releases in that input and `1.3` does not order above `1.4`. **Every clause is false.** `~=` matches no operator in the scan, the loop falls through without `break`, and the clause is silently dropped. |
| the cause is hard-coded, not measured | `check_specifier("!=2.0", ["2.0+local","3.0"])` reports *"pre-releases"*; `Version("2.0+local").is_prerelease` is `False` and its local segment is `'local'`. Neither attribute is ever consulted. |
| **the published test suite fails on packaging 26.x** | Same test body, verbatim: **PASS** on 24.0, **AssertionError** on 26.3 — the release this entry publishes as the partial fix. The test asserts the defect exists in the installed library rather than that the check is correct. No `packaging` pin anywhere in the repo. |

Not re-verified by me but reported with evidence, and consistent with the above: "30% of 60
pairs" is a property of the author's unrecorded grid — 0 pre-releases and 0 local versions
on the axis gives **0.0% in every draw**, and 502,053 real specifier/version pairs give
**1.45%, with zero looser pairs**. The `detection` sentence ("the lockfile records the
version you asked for") is contradicted by pip, which prints the local segment in all four
places. The entry's evidence document contains no mention of 26.0 or the version range at
all.

**What survived:** the behaviour, the silence, and the whole version range — 18/60 from
14.3 through 25.0, 2/60 at every 26.x release, 0 warnings anywhere, boundary confirmed
exactly at 26.0. The verifier could not dent the range, which is the part the sweep
produced.

### Reading it against the registered rule

13 > 8 is the "more than 8" branch: **evidence that the production controls help**, because
the two registered confounds both push the other way.

**But an unregistered confound exists and it is named here rather than buried.** The counts
come from different verifier agents with different methods. The packaging verifier ran 21
mutants and harvested 502,053 real pairs; audit 14's verifiers did neither. **Some of the
13-vs-8 gap is verifier effort, not draft quality, and nothing in this design separates
them.** With n=1 on each side, the honest statement is that the result points in the
predicted direction and is not yet a rate. Two more verifications (`requests`, `urllib3`)
were still running when this was written.

### Separately — and this is not about process

**The published `packaging` entry has live defects.** The check produces false findings with
fabricated explanations, and the test suite breaks on the current release. That is in the
catalogue now.
