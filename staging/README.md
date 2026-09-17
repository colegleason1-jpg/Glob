# Staging — candidate audits awaiting review

**Nothing enters `CATALOGUE` except through `tools/promote.py`, and nothing reaches
`promote.py` except a complete record in this directory.**

## Why

In the version-range sweep of 2026-09-17, **8 of 11 boundary claims produced by
unsupervised agents were refuted by their verifiers** — a 73% overreach rate. Read the
direction carefully: the verifiers narrowed *claims*, not *existence*. Every underlying
finding held. So the failure mode at scale is not fabricated findings, it is **overstated
ones** — "present in every version" where 11 of 2,078 were tested, "byte-identical" where
the file changed twenty times.

Overstatement is the one thing this catalogue cannot survive, because its entire value is
that the claims are true. At one audit per turn the owner reads each claim. At a hundred
audits nobody does. This directory is what replaces that reading.

## The pipeline

    register hypotheses ──▶ measure ──▶ staging/audit-NNN-<pkg>.json
                                              │
                                     adversarial verifier
                                     (told to refute; defaults to refuted)
                                              │
                                     tools/promote.py --audit NNN
                                     validates completeness, refuses on a
                                     live refutation, prints the exact entry
                                              │
                                        owner reviews
                                              │
                                     --confirm ──▶ CATALOGUE + ESTABLISHED

A record with `proposed_verdict` of `CLEAN`, `LOUD` or `INELIGIBLE` is still filed here.
An audit that found nothing is published exactly as one that found something; that is the
protocol, and a staged record is how it survives a batch run.

## What promote.py refuses

* hypotheses missing, or a hypothesis with no recorded outcome
* a measurement with no number in it — "reproduced" is not a measurement
* no verifier verdict
* a verifier refutation that has not been answered by adopting the corrected claim
* a proposed FINDING with no `span_years`, no `resolution`, or an evidence file that does
  not exist
* a key already present in `ESTABLISHED` (promotion is not how an entry gets edited)
