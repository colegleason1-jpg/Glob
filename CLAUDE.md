# CLAUDE.md

This repository builds a catalogue of measured defects in public libraries. Its entire
value is that every claim in it is true and every number in it was measured. A claim that
is wrong, or a finding that quietly disappears, damages it more than a missing feature ever
could.

**Read `docs/PROCESS.md` before changing anything in `unstated/`, `docs/`, or `README.md`.**
The rules below are the enforceable core of it. They exist because each was broken here.

---

## Hard rules

### 1. Never delete a finding

Findings are append-only. They are recorded in `unstated/_manifest.py:ESTABLISHED` and
`unstated/tests/test_process.py` fails if one vanishes.

A finding leaves the catalogue only when its measurement has been **re-run and did not
reproduce**, a `Withdrawal` is appended with the re-run's numbers, and **the owner approved
it in his own words.**

- "A newer version fixed it" → set `resolved_in`. The affected range is still installed.
  **This exact reasoning deleted a real finding on 2026-09-17.**
- "I no longer think it qualifies" → `HELD_OPEN` with the argument, and ask.
- Deleting the row from `ESTABLISHED` to make the test pass is rewriting the record. Stop
  and ask instead.

### 2. Never change a published verdict silently

Outcomes are append-only too. Correct them openly — keep the original and show the
reasoning that produced it. `docs/cold-test-cryptography.md` is the worked example.

### 3. Test a new exclusion rule against every existing entry

Any new principle, threshold or disqualifying criterion is applied to **all existing
entries before it is used on a new one**. If it would disqualify one already catalogued,
the principle is wrong or that entry is — and that is the owner's call.

Skipping this check dismissed three measured candidates against a principle that
contradicted entry 9. It took ten seconds to falsify once it was checked.

### 4. Measure before concluding

Run the thing that would falsify the conclusion, before publishing it.

- A version-scoped verdict needs the **version range measured**. One version tested is a
  claim about one version, and must say so.
- A check needs a test that it stays **silent** on the correct case, not only that it fires.
- "I reasoned it through" is not a measurement. Every wrong call on this repository was
  reached analytically and contradicted by the first direct measurement.

### 5. Destructive operations need explicit approval

Ask **before**. Destructive here means: removing or downgrading a finding, entry, check,
test or document section; changing a published verdict, number or claim; `git rm`,
force-push, history rewrite, branch reset; overwriting a document where content is lost;
narrowing agreed scope. Approval in one context does not carry to the next.

### 6. Report what changed, removals first

End every substantive turn with what was added, changed and **removed** — removals named
explicitly and first. The owner should never discover a removal by reading a diff.

Say when something was a judgement call, and give the alternative. Say when something is
weaker than it sounds, in the same sentence, not a later paragraph.

---

## The bias these rules counter

The audit protocol was built so that a **miss is as publishable as a hit**. That is correct
and it must stay. But it creates an incentive to *produce* a miss — and on 2026-09-17 that
incentive deleted a measured finding, dismissed three more, and invented a principle to
justify it.

**A protocol satisfiable by finding nothing is exactly as corruptible as one satisfied by
finding something.** Wanting a particular answer is the failure mode. Good intentions were
present throughout and did not help.

---

## Working conventions

- **Findings are measured, never predicted.** "37.2% of these 2,000 values", not "this can
  happen". An entry without a number is an opinion.
- **An entry is a claim about versions**, not about a library. `affected_versions` and
  `resolved_in` are fields, not footnotes.
- **Checks probe the installed library**, not a version string — the same attribute is a
  defect on one machine and a non-event on the next.
- **Half of every check's tests assert silence.** A check that flags everything is switched
  off in its first week and takes the real findings with it.
- **Findings are phrased as preconditions, never as bugs.** "pandas assumes the join key is
  unique on one side" is accurate and fair. "pandas has a bug" is neither.
- **Generated content stays generated.** The README table and its counts come from
  `tools/regen_readme_table.py`; run it after touching `CATALOGUE`.
- Audits are pre-registered in `docs/TARGETS.md` — eligibility *and* hypotheses — before
  measuring. Hypotheses that do not reproduce are published.

## Layout

| path | what it is |
| --- | --- |
| `unstated/_manifest.py` | append-only ledger of every finding. **Read its docstring before editing.** |
| `unstated/_catalogue.py` | the entries, with measurements, ranges and impact |
| `unstated/checks/` | one check per entry |
| `unstated/tests/test_process.py` | the guards on the rules above |
| `docs/PROCESS.md` | the rules in full, with the incidents that produced them |
| `docs/TARGETS.md` | the selection protocol and the audit register |
| `docs/cold-test-*.md` | one file per audit, the full measurement |

Run `python -m pytest -q` before committing. 759+ tests; all must pass.
