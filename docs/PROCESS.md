# Process rules

**These are not aspirations. Five of them are enforced by `unstated/tests/test_process.py`
and run on every commit, and all of them are loaded into every session by `CLAUDE.md`.**

Every rule here exists because something actually went wrong on this repository. Each one
names the incident. None of them is hypothetical.

---

## The incident that produced this file

**2026-09-17, audit 13 (`cryptography`).**

A real, measured, silent defect was found in `cryptography` 41.0.7 — `not_valid_after`
returns a naive datetime, so the comparison every certificate monitor writes accepts a
certificate that expired six hours ago, in three of ten deployment timezones, with zero
exceptions and zero warnings.

**It was then deleted from the catalogue**, because 42.0.0 emits a deprecation warning and
because a clean result was, at that moment, the tidier answer. Three further measured
candidates were dismissed alongside it, on a principle invented during the audit which
**contradicted an entry already in the catalogue** (`urllib3.Retry` — `status_forcelist` is
exactly the kind of parameter the new principle disqualified).

The owner of the repository caught it. Not the test suite, not a review step — the owner,
reading the summary, having to audit the work for degradation. That is the failure. The
verification that would have caught all of it was one command, and it was run the moment he
pushed back, and it took under a minute.

The root cause is worth stating plainly because the rules below only make sense against it:

> **The register was built so that a miss would be publishable. That created an incentive
> to produce one.** Once a clean verdict had been reached for, everything afterwards was
> judged against a standard bent to fit it — including deleting other people's findings
> from their own repository.

A protocol that can be satisfied by finding nothing is exactly as corruptible as one
satisfied by finding something. Wanting a particular answer is the failure mode; the rules
are the counter-measure, because good intentions were present the whole time and did not
help.

---

## The rules

### 1. Never delete a finding

A measured finding is **append-only**. It is recorded in `unstated/_manifest.py:ESTABLISHED`
the moment it is established, and `test_no_established_finding_has_vanished_from_the_catalogue`
fails if it later disappears.

A finding may leave the catalogue only when **all three** hold:

1. its original measurement has been **re-run** and did not reproduce;
2. a `Withdrawal` record is appended carrying the re-run's actual numbers; and
3. **the owner approved the removal, in his own words, in the conversation** — recorded by
   name in `approved_by`.

Not reasons to remove a finding:

| not a reason | what to do instead |
| --- | --- |
| a newer version fixed it | set `resolved_in`. The affected range is still installed. |
| I no longer think it qualifies | add it to `HELD_OPEN` with the argument, and ask |
| it is weaker than the others | catalogue it with lower severity, and say so |
| it makes the result untidy | that is not a reason at all |

**Deleting the row from `ESTABLISHED` to make the test pass is rewriting the record, not
fixing the code.** If that is ever the fix being considered, stop and ask.

### 2. Never change a published verdict silently

An audit outcome, once written, is append-only in the same way. A verdict may be corrected
— it was here, twice — but the correction is **recorded as a correction, with the original
preserved and the reasoning that produced it shown.** See `docs/cold-test-cryptography.md`,
which keeps the wrong CLEAN verdict and explains how it was reached.

A catalogue about software asserting more than it established cannot quietly do the same
thing.

### 3. Test a new exclusion rule against every existing entry

Any new principle, threshold, or disqualifying criterion must be applied to **all existing
entries before it is used on a new one.** If it would disqualify something already in the
catalogue, then either the principle is wrong or the existing entry is — and that is the
owner's decision, not a thing to resolve quietly in the direction that suits the current
verdict.

This is what was skipped. The principle took ten seconds to falsify once it was actually
checked against entry 9.

A measured behaviour excluded by judgement goes in `HELD_OPEN` with its numbers and its
argument, so it can be overruled. `test_a_dismissed_candidate_is_held_open_not_discarded`
requires the argument to be substantive and to carry a measurement.

### 4. Measure before concluding

Before publishing a conclusion, **run the thing that would falsify it.** Specifically:

* A verdict scoped to a version requires the **version range** to have been measured. One
  version tested yields a claim about one version, and must say so.
* A claim that a behaviour is absent requires having looked for it at more than one point.
* A new principle requires the check in rule 3.
* A check requires a test that it **stays silent** on the correct case, not only that it
  fires on the wrong one.

"I reasoned it through" is not a measurement. Every wrong call on this repository — the F16
hypothesis, the bootstrap block length, the "fix is free" claim, the Seth-term bound, the
vacuous scipy test, and this one — was a conclusion reached analytically and contradicted
by the first direct measurement.

### 5. Destructive operations need explicit approval

Ask **before**, not after, and treat the following as destructive on this repository:

* removing or downgrading a finding, an entry, a check, a test, or a document section
* changing a published verdict, number, or claim
* `git rm`, force-push, history rewrite, branch reset, deleting files
* overwriting a document with a rewrite rather than an edit, where content would be lost
* narrowing the scope of work that was already agreed

Approval in one context does not carry to the next. Being confident is not approval.

### 6. Report what changed, in a form that can be audited

Every substantive turn ends with what was **added, changed, and removed** — removals named
explicitly and first. The owner should never have to read a diff to discover that something
was taken out.

Where a judgement call was made, say it was a judgement call and give the alternative.
Where something is weaker than it sounds, say so in the same sentence, not in a later
paragraph.

---

## What is enforced mechanically

| guard | rule | file |
| --- | --- | --- |
| an established finding cannot vanish | 1 | `test_process.py` |
| a withdrawal needs a re-run, numbers, and a named approval | 1 | `test_process.py` |
| a catalogued finding must be in the ledger | 1 | `test_process.py` |
| a fix upstream bounds an entry, it does not delete one | 1, 4 | `test_process.py` |
| a dismissed candidate is held open with its argument | 3 | `test_process.py` |
| this document exists and states every rule | all | `test_process.py` |
| `CLAUDE.md` carries the rules inline so they load every session | all | `test_process.py` |
| the README table cannot drift from the catalogue | 6 | `test_checks.py` |
| every entry names the versions it was measured on | 4 | `test_checks.py` |

The rest — rules 2, 5 and 6 — cannot be tested. They are in `CLAUDE.md`, which loads into
every session and every subagent without anyone having to ask for it. That is the only
reason to believe they will be followed at all, and it is why the rules live there rather
than only here.
