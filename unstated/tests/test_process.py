"""Guards on the process, not on the code.

Every test here exists because something actually went wrong, and each names the incident.
They are cheap and they run on every commit, which is the point: the failures they guard
against were all cheap to catch and were not caught, and the person who caught them was
the owner of the repository rather than the test suite.
"""

from __future__ import annotations

import pathlib

import pytest

from unstated import CATALOGUE
from unstated._manifest import ESTABLISHED, HELD_OPEN, WITHDRAWALS

ROOT = pathlib.Path(__file__).resolve().parents[2]


def _keys():
    return {f"{e.library}|{e.component}" for e in CATALOGUE}


# --------------------------------------------------------------------------- #
# 2026-09-17: a measured finding in cryptography 41.0.7 was deleted from the
# catalogue without being asked about, because a later release fixed it.
# --------------------------------------------------------------------------- #

def test_no_established_finding_has_vanished_from_the_catalogue():
    """The guard on the incident this whole file exists for.

    If this fails you are about to remove a finding. That is allowed exactly once you have
    re-run its measurement, watched it not reproduce, and recorded a Withdrawal carrying
    the owner's approval in their own words. Deleting the row from ESTABLISHED to make the
    test pass is rewriting the record, not fixing the code.
    """
    withdrawn = {w.key for w in WITHDRAWALS}
    missing = [k for k in ESTABLISHED if k not in _keys() and k not in withdrawn]
    assert not missing, (
        f"{len(missing)} established finding(s) are gone from CATALOGUE with no "
        f"Withdrawal record: {missing}. See unstated/_manifest.py and docs/PROCESS.md."
    )


def test_a_withdrawal_carries_a_re_run_and_a_named_approval():
    """'I no longer think it qualifies' is not a withdrawal. A re-run that did not
    reproduce, plus the owner saying so, is."""
    for w in WITHDRAWALS:
        for field in ("key", "established_in", "remeasured_on", "what_it_showed",
                      "approved_by", "evidence"):
            value = getattr(w, field)
            assert value and value.strip(), f"withdrawal of {w.key!r} has empty {field}"
        assert any(ch.isdigit() for ch in w.what_it_showed), (
            f"withdrawal of {w.key!r} records no number from the re-run — a withdrawal "
            "needs the measurement, not a description of it"
        )
        assert (ROOT / w.evidence).exists(), f"withdrawal of {w.key!r} cites missing evidence"


def test_every_catalogue_entry_is_recorded_in_the_ledger():
    """The other direction: a finding added to CATALOGUE and not to ESTABLISHED is
    unprotected — it could be deleted later and nothing would notice."""
    unrecorded = sorted(_keys() - set(ESTABLISHED))
    assert not unrecorded, (
        f"catalogued but not in the append-only ledger: {unrecorded}. "
        "Add them to unstated/_manifest.py:ESTABLISHED."
    )


def test_a_fix_upstream_bounds_an_entry_it_does_not_delete_one():
    """The specific wrong reasoning: 42.0.0 fixed it, therefore there is no finding.
    A resolved entry must still be present, and must carry the range it applies to."""
    resolved = [e for e in CATALOGUE if e.is_resolved]
    assert resolved, (
        "no resolved entries at all — if one was dropped because upstream fixed it, that "
        "is the exact error this guards"
    )
    for e in resolved:
        assert e.affected_versions != "not yet ranged", (
            f"{e.library} names a fix version but no measured affected range: a bound "
            "needs both ends"
        )


# --------------------------------------------------------------------------- #
# 2026-09-17: three further candidates were dismissed on a principle invented
# mid-audit, which contradicted an existing entry.
# --------------------------------------------------------------------------- #

def test_a_dismissed_candidate_is_held_open_not_discarded():
    """A measured behaviour excluded by judgement is recorded with its argument so the
    owner can overrule it. Silently dropping one is how the incident happened."""
    for key, argument in HELD_OPEN:
        assert "|" in key, f"held-open key {key!r} is not library|component"
        assert len(argument) > 120, (
            f"held-open {key!r} carries a {len(argument)}-character argument — too thin "
            "for someone to overrule it on"
        )
        assert any(ch.isdigit() for ch in argument), (
            f"held-open {key!r} records no measurement; a judgement call still needs the "
            "numbers it was made against"
        )


# --------------------------------------------------------------------------- #
# The rules have to load without being asked for, or they are not rules.
# --------------------------------------------------------------------------- #

MANDATORY_RULES = [
    "Never delete a finding",
    "Never change a published verdict",
    "Test a new exclusion rule against every existing entry",
    "Measure before concluding",
    "Destructive operations need explicit approval",
    "Report what changed, removals first",
    "A doubt about the work is a hypothesis, not a conclusion",
]


def test_the_process_document_exists_and_states_every_rule():
    process = ROOT / "docs" / "PROCESS.md"
    assert process.exists(), "docs/PROCESS.md is missing"
    text = process.read_text()
    for rule in MANDATORY_RULES:
        assert rule in text, f"docs/PROCESS.md no longer states the rule: {rule!r}"


def test_claude_md_loads_the_rules_automatically():
    """A document nobody reads is not a rule. CLAUDE.md is injected into every session,
    including subagents, so the rules arrive without the owner having to ask for them."""
    claude_md = ROOT / "CLAUDE.md"
    assert claude_md.exists(), "CLAUDE.md is missing — the rules will not load"
    text = claude_md.read_text()
    assert "docs/PROCESS.md" in text, "CLAUDE.md does not point at the process document"
    for rule in MANDATORY_RULES:
        assert rule in text, (
            f"CLAUDE.md no longer carries the rule {rule!r} inline. Pointing at a file is "
            "not enough; the hard rules must be in the text that always loads."
        )


def test_is_resolved_reads_the_verdict_not_the_whole_string():
    """`resolved_in` carries an explanation after the verdict — "not resolved — upstream
    treats this as by design". Two earlier versions of this predicate got it wrong in
    opposite directions: one reported four unresolved entries as fixed, the next reported
    every entry as unresolved because "" is a prefix of everything."""
    from unstated._catalogue import CatalogueEntry

    def entry(resolved_in):
        return CatalogueEntry(
            library="l", component="c", versions_measured="v", assumption="a",
            cost_when_violated="c", upstream_status="u", evidence="e",
            affected_versions="x", resolved_in=resolved_in,
        )

    for verdict, expected in [
        ("not resolved", False),
        ("not resolved — upstream treats the divergence as by design", False),
        ("unknown", False),
        ("", False),
        ("   ", False),
        ("Not Resolved", False),
        ("42.0.0 (2024-01-23)", True),
        ("partially: 26.0 (2026-01-21)", True),
    ]:
        assert entry(verdict).is_resolved is expected, f"{verdict!r} misread"


def test_every_entry_carries_a_measured_version_range():
    """A single-version entry is an under-specified claim. Added after the sweep of
    2026-09-17 ranged all eleven."""
    unranged = [e.library for e in CATALOGUE if e.affected_versions == "not yet ranged"]
    assert not unranged, f"entries with no measured range: {unranged}"


def test_the_anti_reframing_rule_names_what_it_bans():
    """Rule 7. A rule stated abstractly is one I can read past; the banned moves are listed
    concretely because each of them happened, and the last one is the excuse offered for
    the others."""
    for path in (ROOT / "CLAUDE.md", ROOT / "docs" / "PROCESS.md"):
        text = path.read_text()
        assert "Never publish the doubt as a finding" in text or \
               "Never publish the doubt itself as a finding" in text, \
            f"{path.name} does not state the core of rule 7"
        assert "claiming a rule gap to excuse breaking a rule" in text.lower(), (
            f"{path.name} does not ban the excuse that was actually used — claiming the "
            "rules did not cover something without reading them"
        )


def test_the_state_tool_runs_and_reports_ground_truth():
    """Rule 6 names a command, so the command has to work. This runs it for real rather
    than asserting the file exists."""
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "state.py")],
        capture_output=True, text=True, cwd=ROOT, timeout=300,
    )
    assert result.returncode == 0, (
        f"tools/state.py reported a problem with the repository:\n{result.stdout}"
    )
    out = result.stdout
    assert f"FINDINGS — {len(CATALOGUE)}" in out, "state.py miscounts the catalogue"
    assert "VANISHED WITHOUT A WITHDRAWAL                0" in out
    assert f"HELD OPEN — {len(HELD_OPEN)}" in out
    for entry in CATALOGUE:
        assert entry.library in out, f"{entry.library} is missing from the state report"
