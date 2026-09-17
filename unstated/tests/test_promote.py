"""The staging gate. Nothing enters CATALOGUE except through tools/promote.py.

These test the refusals, not the happy path. A gate that only passes good records is not
a gate — the value is entirely in what it turns away.
"""

from __future__ import annotations

import copy
import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

import promote  # noqa: E402


def _complete():
    """A record that passes, built from the real audit 14 staging file."""
    rec = json.loads((ROOT / "staging" / "audit-014-pluggy.json").read_text())
    rec["verifier"] = {"refuted": False, "reason": "checked"}
    return rec


def test_the_real_staged_record_is_complete_but_for_its_verifier():
    """Audit 14 as staged: the only thing standing between it and promotion is the
    verifier verdict. If this starts failing, the record drifted."""
    rec = json.loads((ROOT / "staging" / "audit-014-pluggy.json").read_text())
    problems = promote.validate(rec)
    assert all("verifier" in p or "REFUTED" in p for p in problems), (
        f"audit 14 has problems beyond its missing verdict: {problems}"
    )


def test_a_complete_record_is_accepted():
    assert promote.validate(_complete()) == []


@pytest.mark.parametrize("mutate,expected", [
    (lambda r: r.pop("hypotheses"), "missing top-level field: hypotheses"),
    (lambda r: r.update(hypotheses=[]), "no hypotheses registered"),
    (lambda r: r["hypothesis_outcomes"].pop(), "has no recorded outcome"),
    (lambda r: r["hypotheses"][0].update(registered_before_measuring=False),
     "not marked registered_before_measuring"),
    (lambda r: r["measurements"][0].update(result="reproduced"), "carries no number"),
    (lambda r: r.update(versions_tested=[]), "only as wide as what was measured"),
    (lambda r: r.update(verifier={}), "no refuted flag"),
    (lambda r: r.update(verifier={"refuted": True, "reason": "overreaches"}),
     "REFUTED this claim and no corrected version"),
    (lambda r: r["proposed_entry"].update(span_years=None), "missing span_years"),
    (lambda r: r["proposed_entry"].update(resolution="mostly"), "not open/partial/fixed"),
    (lambda r: r["proposed_entry"].update(resolution="fixed"), "no resolved_version"),
    (lambda r: r["proposed_entry"].update(evidence="docs/does-not-exist.md"),
     "evidence file does not exist"),
    (lambda r: r["proposed_entry"].update(library="pandas", component="DataFrame.merge"),
     "already established"),
    (lambda r: r.update(proposed_verdict="FINDING", proposed_entry=None),
     "FINDING but no proposed_entry"),
    (lambda r: r.update(proposed_verdict="CLEAN"), "but a proposed_entry is present"),
    (lambda r: r.update(proposed_verdict="PROBABLY"), "not in ('FINDING'"),
])
def test_the_gate_refuses(mutate, expected):
    """Each mutation is a way a staged record could be incomplete or overreaching."""
    rec = _complete()
    mutate(rec)
    problems = promote.validate(rec)
    assert any(expected in p for p in problems), (
        f"expected a refusal containing {expected!r}, got: {problems}"
    )


def test_a_refutation_can_be_answered_by_adopting_the_correction():
    """A verifier refutation is not a dead end — it is answered by narrowing the claim."""
    rec = _complete()
    rec["verifier"] = {"refuted": True, "reason": "span overreaches",
                       "corrected_claim": "7 releases sampled, not all"}
    assert any("no corrected version" in p for p in promote.validate(rec))
    rec["adopted_correction"] = "narrowed to the 7 releases actually measured"
    assert promote.validate(rec) == []


def test_a_clean_outcome_stages_without_an_entry():
    """An audit that found nothing is published the same as one that found something, and
    needs no catalogue entry to do it."""
    rec = _complete()
    rec["proposed_verdict"] = "CLEAN"
    rec["proposed_entry"] = None
    assert promote.validate(rec) == []
