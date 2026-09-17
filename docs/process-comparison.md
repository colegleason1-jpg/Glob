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

### requests — **16 defects**, against audit 14's 8

Verified by me directly:

| claim | measured |
| --- | --- |
| **the published remedy is wrong ~43% of the time** | `unstated/checks/encoding.py` tells the caller to `set r.encoding = r.apparent_encoding`, *"correct on 12 of 12 measured UTF-8 bodies."* On 58 realistic short UTF-8 bodies: **correct 33/58 (56.9%), wrong 25/58 (43.1%)**. Every failure is valid UTF-8 — `'£5'`→big5, `'€9'`→utf_16_le, `'•'`→cp037, `'½'`→big5. The verifier measured 23% wrong on its corpus; mine is worse. |
| the `12/12` rests on an unpublished corpus | `cold-test-requests.md:55` says *"12 UTF-8 bodies"* and never lists them. No probe script was committed. **The entry's headline cannot be audited by a reader.** |
| `'£5'` → big5 | Confirmed: `b'\xc2\xa35'` → `big5` → `'瞿5'`, does not round-trip, at charset-normalizer 3.3.2, 3.4.6 and 3.5.1. |

**A previous verifier raised `'£5'` and I rejected it**, on the grounds that it belongs to
the character-count table rather than the `apparent_encoding` corpus. That distinction is
true of what I ran and **appears nowhere in the published document** — line 55 presents "12
UTF-8 bodies" under one heading and line 116 prints `'£5'` as a body. My defence rested on a
corpus only I could see. Rejecting it was the wrong call.

Also reported with evidence: *"byte-identical in 82 of the 83 non-prerelease 2.x releases"*
is false — **17 of 82** are byte-identical, 65 use single quotes, and the "83rd" (2.15.0)
has no files on PyPI so it cannot be checked at all. `get_encoding_from_headers` has 6
distinct bodies across the span, not one. The check's charset guard is a substring test
where requests uses a parsed-key test, so four Content-Types mojibake while the check stays
silent. The check fires on a genuinely Latin-1 body where requests is **right**, and fires
again *after its own remedy is applied*, contradicting its own `observed` field.

**What survived:** the defect itself, entirely. The content-type table 11/11, the
character-count table 5/5 with exact mojibake strings, the lookups table, `r.json()` and
`iter_lines` inheritance, the truncation arithmetic, the `VARCHAR(20)` example, the 2.25.1
`application/json` boundary, and both PyPI endpoint dates.

### urllib3 — **20 defects**, against audit 14's 8

Verified by me directly:

| claim | measured |
| --- | --- |
| **a published claim is outright false** | The entry publishes *"2.8.0 is the first release ever to attach a deprecation to `Retry.__init__`."* urllib3 **1.26.20** emits `DeprecationWarning: Using 'method_whitelist' with Retry is deprecated…` from `Retry.__init__`. 1.26.0 shipped 2020-11-10 — **off by 5.8 years**, and it is a deprecation about `method_whitelist`, the exact parameter this entry's third gap concerns. Repeated verbatim in `version-range-sweep.md:94`. |
| **the check cannot see the defect in the form most people write it** | `check_retry(3)` → `None`. `check_retry(True)` → `None`. `getattr(3, "total", None)` is `None`, so a plain int falls into the "retries are off" branch. On the wire, `retries=3` against a 503 sends **1 request** — precisely this entry's defect, undetected. |
| an unbounded retry reads as "off" | `Retry(total=None, status_forcelist=[503])` → check returns `None` with the comment *"retries are off; nothing is being promised"*. `is_exhausted()` is **False** with all counts `None`; the verifier measured **501 requests**. The comment states the opposite of the library's behaviour. |

Also reported with evidence: `retry.py` has **33** distinct released contents, not "~20";
the emitted message is measurably false whenever the server sends `Retry-After`, which
`respect_retry_after_header=True` honours by default; `allowed_methods=frozenset()` replays
a POST 4 times with the check silent — the very case urllib3 2.8.0's new warning exists for;
16 of 84 in-range releases were sampled (19%) with no list of which 16 recorded anywhere;
and 7 of 19 mutants survive, including **inverting gap 1's message to its exact negation**.

**What survived:** every number in the Measured table — 1 / 1 / 4 / 4 requests, 0.00 s,
3.00 s — the three-mechanism isolation, the three defaults, the 1.9 floor and its date, the
2.8.0 ceiling, 12.2 years, both byte counts. "POST was never in the default method set" is
true across **84 of 84** releases, stronger than the entry claims for itself.

### Reading it against the registered rule

| entry | process | defects |
| --- | --- | ---: |
| `urllib3` | old | **20** |
| `requests` | old | **16** |
| `packaging` | old | **13** |
| `pluggy` (audit 14) | **new** | **8** |

**All three old entries land above audit 14's 8, with no overlap — 13 to 20 against 8.**
That is the "more than 8" branch of the registered rule, three times over, and the two
registered confounds both push the other way.

**But an unregistered confound exists and it is named here rather than buried.** The counts
come from different verifier agents. Both old-entry verifiers ran mutation testing; audit
14's round-1 verifier did not. **Some of the gap is verifier effort, not draft quality, and
nothing in this design separates them.**

**The least-confounded number available is the mutation score**, because it measures the
entry's own test suite rather than how hard the verifier looked:

| check's test suite | mutation score |
| --- | --- |
| `packaging` (old process) | **43%** — 9 of 21 mutants killed |
| `requests` (old process) | **28%** — 7 of 25 mutants killed |
| `pluggy` (new process, after rework) | **~70%** — 3 of 10 survived |

Those are the verifiers' measurements, not mine, and the mutant sets differ. But they point
the same way as the defect counts and do not depend on verifier thoroughness. A crippled
`requests` check that is silent on Cyrillic, Greek, Hebrew, Arabic, Thai, Korean and emoji
**passes all 8 published tests** — every non-ASCII fixture in that suite is Latin-1-range
plus one Japanese string.

`urllib3` was still running when this was written.

### Separately — and this is not about process

**The published `packaging` entry has live defects.** The check produces false findings with
fabricated explanations, and the test suite breaks on the current release. That is in the
catalogue now.
