# Cold test 3: python-dateutil 2.9.0 — the hard target

2026-09-17 · chosen to resist the method, not to suit it.

The first two cold tests were arguably easy: both were machine-learning components with an
obvious ablation switch, in fields where priors about likely defects exist. `dateutil` has
none of those properties. It is twenty years old, in nearly every Python stack, entirely
non-statistical, and has **no pluggable component to ablate**. A null result was the
expected outcome and would have been reported as one.

## What is not a finding

`parse()` resolves `01/02/2023` as January 2nd, and `dayfirst=True` makes it February 1st.
That is documented, widely known, and not worth reporting.

## Finding 1 — the assumption is applied per row, so one column comes back under two conventions

2,000 dates from a day/month/year locale, parsed with the defaults:

| | |
| --- | --- |
| silently wrong date returned | **745 (37.2%)** |
| correct | 1,255 (62.8%) |
| …of those, correct only because day > 12 forced the inference | 1,197 (95%) |
| exceptions raised | **0** |
| warnings emitted | **0** |

`parse()` decides per string. `01/02/2023` takes the US reading; `13/02/2023` cannot, so it
flips to day-first for that string alone. The column comes back with **803 rows read
month-first and 1,197 read day-first**, every value a valid datetime.

When wrong, the median error is 118 days — and every wrong value is a valid date in the
same year, so a range check, a dtype check and a null check all pass.

## Correction: finding 2 is already filed upstream

Checked after writing, which is the wrong order and is recorded here for that reason.
The ISO/European conflict is **a known, open issue on dateutil's own tracker** —
[dateutil#402, "It's impossible to parse ISO-style and European-style dates at the same
time"](https://github.com/dateutil/dateutil/issues/402). Nothing below is a discovery.

What is not in that issue, and is the part worth keeping:

* the **magnitude** — 37.2% of a day-first column silently wrong, and the remedy leaving
  the total essentially unchanged at 376 → 369
* the observation that **95% of the "correct" rows are correct only by accident**, because
  a day above 12 forced the inference
* that a single column comes back under **two conventions at once**
* a three-line check that detects it in 90 ms

And the sharper point for anything built on top of this: the behaviour has been **known
and filed since 2017 and still produces silent 37% error rates today**, with no warning in
the docstring and no signal at the call site. A defect being known upstream is not the
same as a caller being told. That gap — between what is filed and what reaches the person
running the code — is the whole case for a catalogue, and this finding is evidence for it
rather than against it.

## Finding 2 — the documented remedy breaks ISO 8601

`dayfirst=True` fixes the slashes. It also reorders ISO dates, which are unambiguous by
definition:

```
parse("2023-01-02")                  -> 2023-01-02
parse("2023-01-02", dayfirst=True)   -> 2023-02-01
parse("2023-11-12", dayfirst=True)   -> 2023-12-11
```

The docstring scopes the flag to *"the first value in an **ambiguous** 3-integer date (e.g.
01/05/09)"*. `2023-01-02` is not an ambiguous 3-integer date. Neither `dayfirst`'s
description nor `parse()`'s documentation mentions ISO or 8601 anywhere.

`isoparse` is immune — it accepts no `dayfirst` and cannot be flipped. dateutil has the
right tool; `parse()` simply does not route to it.

## The consequence, measured on a realistic mixed column

A very common shape: slashes exported from a spreadsheet, ISO from a database or API.
2,000 rows, half each:

| setting | slash rows wrong | ISO rows wrong | total |
| --- | --- | --- | --- |
| defaults | **376/1000 (37.6%)** | 0/1000 | 376 |
| `dayfirst=True` — the documented remedy | 0/1000 | **369/1000 (36.9%)** | **369** |
| route ISO to `isoparse` | 0 | 0 | **0** |

**The remedy moves the error from one half of the column to the other and leaves the total
almost unchanged: 376 → 369.** A caller who notices the problem, reads the documentation,
applies the documented fix and re-runs sees the same volume of silently wrong dates in
different rows. Zero exceptions and zero warnings in every row of that table.

## The check that catches it

The entire proposed product, on this library, is three lines: parse each value under both
conventions and flag the ones that move.

| input | flagged ambiguous | time |
| --- | --- | --- |
| day/month/year export | 745/2000 (37.2%) | 95 ms |
| US month/day/year export | 745/2000 (37.2%) | 90 ms |
| ISO 8601 | 745/2000 (37.2%) | 89 ms |
| month spelled out | **0/2000 (0.0%)** | 135 ms |
| mixed ISO + slashes | 745/2000 (37.2%) | 91 ms |

It needs no knowledge of which locale produced the file. It only notices that the answer
moves when the assumption does. Note that it flags ISO too — correctly, given finding 2.

## Verdict

The hard target produced the strongest finding of the three cold tests, so the class is not
an artefact of machine-learning libraries or of components with convenient switches:

> A component that works under an assumption, with nothing signalling when the assumption
> does not hold — and here, a documented remedy that introduces an equal and opposite
> failure while appearing to resolve the first.
