# Unstated — where this stands and what happens next

2026-09-17 · internal. Written to be argued with, not agreed with.

## What this is, in one sentence

A catalogue of preconditions that widely-used libraries rely on and do not state, each one
measured, each with a check that detects the violation on the caller's own data.

## What actually exists today

| | state |
| --- | --- |
| Defect class, named and confirmed | 6 audits across 6 libraries, 4 authors, 4 fields |
| `unstated/` package | 3 checks (dates, merges, splits), 14 tests, 5 catalogue entries |
| Evidence | one `docs/cold-test-*.md` per audit, with the runnable scripts behind each |
| Test suite | 719 passing |
| Two engine defects found and fixed | `limited_by`, `WRONG_SIGN` — found by measuring a downstream consumer |
| Published | **nothing** |
| Revenue | **none** |
| Buyer conversations | **none** |

This is not an MVP. An MVP is something a customer can use. This is a validated method, a
small catalogue, and a working prototype of the tooling — which is genuinely further than
most ideas get, and still two steps short of a product.

## The method, formalised

Applied identically to every target. Uniformity is what makes findings comparable,
reviewable, and re-runnable against a new library version.

1. **Name the assumption.** What does this component take for granted about the caller's
   data? ("Rows are independent." "The join key is unique on one side.")
2. **Construct a violation** and measure the cost against ground truth you control.
3. **Confirm the failure is silent.** No exception, no warning, no nulls, right dtype,
   values in range. If the library shouts, there is no entry.
4. **Audit the claims.** Grep the package for any statement of the precondition. Record
   what the docs say, including when they say nothing.
5. **Write the check**, and test that it stays silent on the safe case.
6. **Record upstream status.** Filed, documented, working-as-intended, or unknown.

Step 3 is the gate. A component that raises is not a catalogue entry, however wrong the
caller was.

## The gap in what has been done so far

**Targets were chosen by intuition, not by rule.** Six for six sounds like a hit rate. It
is not one, because the six were picked by someone with reason to suspect each of them.
Any reviewer will say so, and they will be right.

Before the catalogue is worth publishing at scale, target selection needs a stated
protocol. The obvious one:

> Work the top N packages by PyPI download count, in order, without skipping.

That makes the hit rate a real number instead of a selection artefact, and it makes a
*miss* publishable — which is what makes the hits believable.

## Metrics worth tracking from entry 6 onward

| metric | why |
| --- | --- |
| **hit rate** by target, in selection order | the honest expectation is that it falls as obvious targets are exhausted. Track it, publish it, do not hide the decline. |
| clean passes | already 2 (Optuna's TPE, the Cortex learner). A catalogue with no clean passes is a confirmation machine, not an instrument. |
| time per audit | currently well under an hour. If it climbs past a day, the economics change. |
| entries invalidated by a new library version | this is the subscription logic. If entries never go stale, there is no recurring product. |

## Catalogue policy

* **Every entry carries a number.** An entry without a measured cost is an opinion.
* **Every entry carries pinned versions.** A precondition is a property of a version.
* **Every entry carries upstream status.** dateutil's is filed and nine years open. That
  is not a weaker finding — it is the strongest evidence that filing upstream does not
  reach the person running the code.
* **Findings are phrased as preconditions, never as bugs.** "pandas assumes the join key
  is unique on one side" is accurate. "pandas has a bug" is false, unfair, and invites a
  response nobody needs.
* **Re-measure on major versions.** An entry that is no longer true gets marked resolved,
  not deleted. The history is part of the value.

## What is public and what is not

| public | gated |
| --- | --- |
| The findings, with numbers | The scanner |
| 2–3 fully reproducible examples | The full executable catalogue |
| The method, described | Integration, history, ownership mapping |
| Clean passes and misses | Customer scan results, always |

Enough public evidence that a skeptic can verify one claim in ten minutes. Not enough to
reconstruct the sweep. The public examples should be ones already public upstream —
dateutil#402, pandas `validate=` — so nothing is given away that was not already given.

## Distribution, in order

Nobody finds an unknown author's report by accident. The finding has to go where the
readers already are.

1. **One HN / r/datascience post** on the single most surprising finding. An afternoon,
   free, and the response is the cheapest possible test of whether anyone cares.
2. **Post the measurement into the open upstream issues** — dateutil#402 and the pandas
   discussion. Substantive contributions to live threads, not promotion.
3. **PyPI**, as a findable artefact and a download number worth citing.
4. **A talk submission** — PyData, SciPy. "Six libraries, six silent failures."
5. **Warm outreach only**, to people who engaged with 1–4. Never cold email maintainers
   about their own code.

## Commercial path

1. **Audit engagement.** One pipeline, fixed scope, fixed fee, written finding. Pays
   first, requires no product, and every engagement adds catalogue entries.
2. **Scanner licence**, specified by what three engagements independently ask for.
3. Report and tooling closed throughout.

Buyers, in order of pain rather than size: transaction diligence, library-migration
audits ("will our numbers change?"), then post-incident inbound. Model risk management is
the biggest prize and the wrong first target without a team.

## Honest risks

* **Selection artefact.** Addressed by the protocol above, and not before.
* **Hit rate decay.** Six for six will not hold. Plan for it; publish it when it happens.
* **The pitch is general, the pain is unfelt.** Everyone has these bugs, almost nobody
  knows. That combination is where developer tools go to die. The fix is to sell to people
  for whom a wrong number already has a named consequence.
* **Free alternatives.** `pandera`, `great_expectations`, `pandas-vet` occupy adjacent
  ground. The difference is that they check *your data against your rules*; this checks
  *your dependencies' assumptions against your data*. That distinction has to survive
  first contact with a skeptic or the product is a feature.
* **Own-repo contradictions.** Selling overstated-claim detection while shipping an
  overstated claim ends the conversation. Kill God's README still carries one; the patch
  exists and is unapplied.
* **AI co-authorship.** Every commit here is marked. Disclosed and framed by
  `docs/method-applied-to-the-agent.md` it is an asset — the method caught its own
  author's wrong claims eleven times. Discovered first by a skeptic, it reads as
  concealment. Lead with it.

## What would kill this

Stated in advance so it cannot be rationalised away later:

* The hit rate falls below roughly 1 in 5 on protocol-selected targets — the method needs
  a suspicious human and does not scale.
* Three buyers in the target segment independently say "we'd just fix it, nobody needs to
  know" — the finding is real and the consequence is not.
* A free tool already catches four of the six. Check this before publishing, not after.

## Immediate next steps

1. Apply the Kill God patch. Five minutes, removes the worst contradiction.
2. Adopt the selection protocol and record it before the next audit.
3. Continue audits in protocol order, tracking hit rate.
4. Survey `pandera` / `great_expectations` / `pandas-vet` against the current six.
5. Then, and only then, publish.
