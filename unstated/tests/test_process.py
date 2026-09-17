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


def test_is_resolved_reads_a_field_not_a_sentence():
    """`is_resolved` used to parse `resolved_in`, and got it wrong twice in opposite
    directions: comparing the whole string reported four unresolved entries as fixed, and
    the fix `startswith(("not resolved", "unknown", ""))` reported every entry as
    unresolved, because "" is a prefix of everything.

    It reads the `resolution` field now, so neither failure is reachable. This test keeps
    the history and guards the replacement.
    """
    from unstated._catalogue import CatalogueEntry

    def entry(resolution, version=None, prose="not resolved"):
        return CatalogueEntry(
            library="l", component="c", versions_measured="v", assumption="a",
            cost_when_violated="c", upstream_status="u", evidence="e",
            affected_versions="x", resolved_in=prose, span_years=1.0,
            resolution=resolution, resolved_version=version,
        )

    assert entry("open").is_resolved is False
    assert entry("partial", "26.0", "partially: 26.0").is_resolved is True
    assert entry("fixed", "42.0.0", "42.0.0 (2024-01-23)").is_resolved is True

    # The prose no longer decides anything, which is the point of the change.
    assert entry("open", prose="not resolved — by design").is_resolved is False
    assert entry("open", prose="").is_resolved is False

    assert entry("open").status == "open"
    assert entry("partial", "26.0", "partially: 26.0").status == "PARTLY fixed 26.0"
    assert entry("fixed", "42.0.0", "42.0.0 (2024-01-23)").status == "fixed in 42.0.0"


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


# --------------------------------------------------------------------------- #
# 2026-09-17: tools/state.py rendered three columns wrongly in a row, every one
# of them by recovering a fact from prose that the writer already knew. The
# facts are fields now; these guard the fields and the rendering.
# --------------------------------------------------------------------------- #

def test_every_entry_carries_its_facts_as_fields():
    """span, resolution and the fix version are data, not sentences to be parsed."""
    for e in CATALOGUE:
        assert e.span_years is not None, f"{e.library} has no span_years"
        assert e.span_years > 0, f"{e.library} has a non-positive span"
        assert e.resolution in e.RESOLUTIONS, (
            f"{e.library} has resolution={e.resolution!r}, not one of {e.RESOLUTIONS}"
        )


def test_the_fields_and_the_prose_say_the_same_thing():
    """Either can be edited alone, so drift between them is the live risk. A fix version
    in the fields with 'not resolved' in the prose means one of them is stale."""
    for e in CATALOGUE:
        prose_says_open = e.resolved_in.strip().lower().startswith(
            ("not resolved", "unknown")
        )
        assert (e.resolution == "open") == prose_says_open, (
            f"{e.library}: resolution={e.resolution!r} but resolved_in reads "
            f"{e.resolved_in[:60]!r}"
        )
        if e.resolution in ("partial", "fixed"):
            assert e.resolved_version, f"{e.library} is {e.resolution} with no version"
        else:
            assert not e.resolved_version, f"{e.library} is open but names a fix version"


def test_every_named_check_exists_and_is_callable():
    """The name is declared by the entry; this confirms it resolves. Previously the tool
    grepped check sources for `library="x"`, which breaks if a string changes."""
    import unstated

    for e in CATALOGUE:
        if e.check is None:
            continue
        fn = getattr(unstated, e.check, None)
        assert callable(fn), f"{e.library} names check {e.check!r}, which does not exist"


def test_entries_without_a_check_are_the_two_statistical_ones():
    """Not an accident: SMOTE's calibration damage and MedianPruner's rank assumption are
    measured by experiment, not by a function you can call on your data. If a third
    appears, it needs a reason."""
    assert {e.library for e in CATALOGUE if e.check is None} == {
        "imbalanced-learn", "optuna"
    }


def test_the_state_report_renders_a_real_span_and_status_for_every_entry():
    """The test that would have caught the original three bugs. The old one asserted the
    tool exits 0 — which it did, with all three present."""
    import subprocess
    import sys

    out = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "state.py")],
        capture_output=True, text=True, cwd=ROOT, timeout=300,
    ).stdout
    findings = out.split("LEDGER INTEGRITY")[0]
    assert "NO SPAN" not in findings and "—  " not in findings, (
        "an entry rendered with no span:\n" + findings
    )
    for e in CATALOGUE:
        row = [l for l in findings.splitlines() if l.strip().startswith(e.library)]
        assert row, f"{e.library} has no row in the state report"
        assert f"{e.span_years:.1f}y" in row[0], f"{e.library}: span not rendered"
        assert e.status in row[0], f"{e.library}: status {e.status!r} not rendered"
