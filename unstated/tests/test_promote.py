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
    """A record that passes, built from audit 14's staging file with its verdict reset.

    Audit 14 is itself REFUTED, so the live record does not validate — that is the point
    of it. These tests need a record that would pass, to check what each mutation breaks,
    so the fields the refutation set are normalised back here.
    """
    rec = json.loads((ROOT / "staging" / "audit-014-pluggy.json").read_text())
    rec["verifier"] = {"refuted": False, "reason": "checked"}
    rec["proposed_verdict"] = "FINDING"
    rec.pop("owner_review", None)
    rec.pop("adopted_correction", None)
    return rec


def test_audit_14_is_refuted_and_cannot_be_promoted():
    """Audit 14 was the pilot for the staged pipeline, and its verifier REFUTED it — the
    mechanism was wrong (pluggy short-circuits, it does not discard), the ordering rule was
    wrong, two "no API exists" claims were false, a release date was wrong, and the check
    fires at high severity on a stock pytest with no third-party plugins.

    Every one of those was re-measured directly before being accepted; see owner_review in
    the record. This test holds the gate shut until the rework is done.
    """
    rec = json.loads((ROOT / "staging" / "audit-014-pluggy.json").read_text())
    assert rec["verifier"]["refuted"] is True
    assert rec["owner_review"]["verdict"].startswith("DO NOT PROMOTE")
    assert len(rec["owner_review"]["confirmed"]) >= 7
    assert promote.validate(rec), "a refuted record must not validate"


def test_pluggy_is_not_in_the_catalogue():
    """The pilot's whole point. A refuted audit leaves no trace in the catalogue."""
    from unstated import CATALOGUE
    from unstated._manifest import ESTABLISHED

    assert not any(e.library == "pluggy" for e in CATALOGUE)
    assert not any(k.startswith("pluggy|") for k in ESTABLISHED)


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


def test_the_gate_separates_a_defect_from_an_unfinished_step():
    """Both flags on audit 14's first run were genuine, but they were different kinds:
    "measurement carries no number" is a defect in the record; "verifier has no refuted
    flag" is a step that had not run yet. Reporting them in one undifferentiated list
    trains a reader to skim it."""
    assert promote.classify("measurement 2 ('x') carries no number") == "defect"
    assert promote.classify("verifier has no refuted flag") == "incomplete"
    assert promote.classify("no hypotheses registered") == "incomplete"
    assert promote.classify("hypothesis H1 is not marked registered_before_measuring") == "defect"
    assert promote.classify("evidence file does not exist: x") == "defect"
    assert promote.classify("no versions tested — a verdict is only as wide") == "incomplete"


def test_every_refusal_the_gate_can_produce_is_classified():
    """A refusal that falls through to 'defect' by accident would misreport an unfinished
    audit as a broken one. Every condition validate() can emit is exercised here."""
    rec = _complete()
    seen = set()
    for mutate in (
        lambda r: r.update(hypotheses=[]),
        lambda r: r["hypothesis_outcomes"].pop(),
        lambda r: r["hypotheses"][0].update(registered_before_measuring=False),
        lambda r: r["measurements"][0].update(result="reproduced"),
        lambda r: r.update(versions_tested=[]),
        lambda r: r.update(verifier={}),
        lambda r: r.update(verifier={"refuted": True, "reason": "x"}),
        lambda r: r["proposed_entry"].update(span_years=None),
        lambda r: r["proposed_entry"].update(evidence="docs/nope.md"),
        lambda r: r.update(proposed_verdict="MAYBE"),
    ):
        fresh = json.loads(json.dumps(rec))
        mutate(fresh)
        for p in promote.validate(fresh):
            seen.add(promote.classify(p))
    assert seen == {"defect", "incomplete"}, f"classification collapsed to {seen}"
