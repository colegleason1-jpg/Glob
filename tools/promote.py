"""Validate a staged audit and, on --confirm, promote it into the catalogue.

    python tools/promote.py --audit 14            # validate and show what would be added
    python tools/promote.py --audit 14 --confirm  # actually add it

This is the only way an entry enters ``CATALOGUE``. See ``staging/README.md`` for why:
unsupervised agents overreached on 8 of 11 claims in the last batch run, and overstatement
is the failure this catalogue cannot survive.

Validation is deliberately unforgiving. A staged record that cannot satisfy it is not a
record to be waved through — it is an audit that has not finished.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
STAGING = ROOT / "staging"
sys.path.insert(0, str(ROOT))

REQUIRED_TOP = ("audit", "package", "rank", "eligibility", "hypotheses",
                "versions_tested", "measurements", "hypothesis_outcomes",
                "proposed_verdict", "verifier")
VERDICTS = ("FINDING", "CLEAN", "LOUD", "INELIGIBLE")
ENTRY_FIELDS = ("library", "component", "versions_measured", "assumption",
                "cost_when_violated", "upstream_status", "evidence",
                "affected_versions", "resolved_in", "span_years", "resolution")


def find(audit: int) -> pathlib.Path:
    hits = sorted(STAGING.glob(f"audit-{audit:03d}-*.json"))
    if not hits:
        raise SystemExit(f"no staged record for audit {audit} in {STAGING}")
    if len(hits) > 1:
        raise SystemExit(f"several records for audit {audit}: {[h.name for h in hits]}")
    return hits[0]


def has_number(text: str) -> bool:
    return any(ch.isdigit() for ch in str(text))


#: Refusals that mean a required step has not happened yet. The record is not defective,
#: it is unfinished. Reported separately because a list that mixes "this is wrong" with
#: "this is not done" trains a reader to skim it.
INCOMPLETE_MARKERS = (
    "verifier has no refuted flag",
    "no hypotheses registered",
    "has no recorded outcome",
    "no measurements recorded",
    "no versions tested",
    "missing top-level field",
)


def classify(problem: str) -> str:
    """"incomplete" if a step has not run yet, "defect" if the record says something wrong."""
    return "incomplete" if any(m in problem for m in INCOMPLETE_MARKERS) else "defect"


def validate(rec: dict) -> list[str]:
    """Every reason this record may not be promoted. Empty means it may.

    **This gate checks FORM, not TRUTH.** It can see that a measurement carries no number.
    It cannot see that the number measures the wrong thing — on audit 14 it passed
    "both produced values [80, 100]", which was measured on a different hook entirely.
    Of the 8 real defects in that audit the gate caught 1; the adversarial verifier caught
    7. The gate is necessary and nowhere near sufficient, and nothing here should be read
    as saying a record that passes is correct.
    """
    from unstated._manifest import ESTABLISHED

    problems: list[str] = []

    for key in REQUIRED_TOP:
        if key not in rec:
            problems.append(f"missing top-level field: {key}")
    if problems:
        return problems

    if rec["proposed_verdict"] not in VERDICTS:
        problems.append(f"proposed_verdict {rec['proposed_verdict']!r} not in {VERDICTS}")

    if not rec["hypotheses"]:
        problems.append("no hypotheses registered — the protocol requires them before measuring")
    registered = {h.get("id") for h in rec["hypotheses"]}
    answered = {o.get("id") for o in rec["hypothesis_outcomes"]}
    for hid in sorted(registered - answered):
        problems.append(f"hypothesis {hid} has no recorded outcome")
    for h in rec["hypotheses"]:
        if not h.get("registered_before_measuring"):
            problems.append(f"hypothesis {h.get('id')} is not marked registered_before_measuring")

    if not rec["measurements"]:
        problems.append("no measurements recorded")
    for i, m in enumerate(rec["measurements"]):
        if not has_number(m.get("result", "")):
            problems.append(
                f"measurement {i} ({m.get('what', '?')[:40]!r}) carries no number — "
                f'"reproduced" is not a measurement'
            )

    if not rec["versions_tested"]:
        problems.append("no versions tested — a verdict is only as wide as what was measured")

    v = rec["verifier"]
    if "refuted" not in v:
        problems.append("verifier has no refuted flag")
    elif v["refuted"] and not rec.get("adopted_correction"):
        problems.append(
            "the verifier REFUTED this claim and no corrected version has been adopted "
            f"(set adopted_correction). Its reason: {str(v.get('reason'))[:120]}"
        )

    entry = rec.get("proposed_entry")
    if rec["proposed_verdict"] == "FINDING":
        if not entry:
            problems.append("verdict is FINDING but no proposed_entry")
        else:
            for f in ENTRY_FIELDS:
                if entry.get(f) in (None, ""):
                    problems.append(f"proposed_entry is missing {f}")
            if entry.get("resolution") not in ("open", "partial", "fixed"):
                problems.append(f"resolution {entry.get('resolution')!r} is not open/partial/fixed")
            if entry.get("resolution") in ("partial", "fixed") and not entry.get("resolved_version"):
                problems.append("resolution is partial/fixed but no resolved_version")
            ev = entry.get("evidence")
            if ev and not (ROOT / ev).exists():
                problems.append(f"evidence file does not exist: {ev}")
            key = f"{entry.get('library')}|{entry.get('component')}"
            if key in ESTABLISHED:
                problems.append(f"{key} is already established; promotion is not how an entry is edited")
    elif entry:
        problems.append(f"verdict is {rec['proposed_verdict']} but a proposed_entry is present")

    return problems


def render_entry(entry: dict) -> str:
    """The CatalogueEntry source this record would add."""
    def q(v):
        return "None" if v is None else (repr(v) if not isinstance(v, (int, float)) else str(v))

    lines = ["    CatalogueEntry("]
    for f in ("library", "component", "versions_measured", "affected_versions",
              "resolved_in", "assumption", "cost_when_violated", "upstream_status",
              "evidence"):
        lines.append(f"        {f}={q(entry[f])},")
    for f in ("span_years", "resolution", "resolved_version", "check"):
        lines.append(f"        {f}={q(entry.get(f))},")
    imp = entry.get("impact")
    if imp:
        lines.append("        impact=Impact(")
        for f in ("believed_claim", "actual_claim", "breaks", "detection"):
            lines.append(f"            {f}={q(imp.get(f))},")
        lines.append("        ),")
    lines.append("    ),")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--audit", type=int, required=True)
    ap.add_argument("--confirm", action="store_true",
                    help="write the entry into the catalogue and the ledger")
    args = ap.parse_args()

    path = find(args.audit)
    rec = json.loads(path.read_text())
    print(f"staged record: {path.relative_to(ROOT)}")
    print(f"  audit {rec.get('audit')} — {rec.get('package')} (rank {rec.get('rank')})")
    print(f"  proposed verdict: {rec.get('proposed_verdict')}")
    ver = rec.get("verifier", {})
    print(f"  verifier: {'REFUTED' if ver.get('refuted') else 'held'}")

    problems = validate(rec)
    if problems:
        defects = [p for p in problems if classify(p) == "defect"]
        pending = [p for p in problems if classify(p) == "incomplete"]
        print(f"\n  REFUSED — {len(defects)} defect(s), {len(pending)} step(s) not yet done")
        if defects:
            print("\n  DEFECTS — the record says something wrong:")
            for p in defects:
                print(f"    - {p}")
        if pending:
            print("\n  NOT YET DONE — no defect, the audit is unfinished:")
            for p in pending:
                print(f"    - {p}")
        print("\n  Note: this gate checks FORM, not TRUTH. A record that passes is not "
              "thereby correct —\n  on audit 14 it passed a measurement taken on the wrong "
              "hook. Adversarial verification\n  caught 7 of the 8 real defects; the gate "
              "caught 1.")
        return 1

    print("\n  validation: passed")
    if rec["proposed_verdict"] != "FINDING":
        print(f"  verdict is {rec['proposed_verdict']}; nothing is added to the catalogue.")
        print("  The record stays in staging/ as the published outcome.")
        return 0

    entry_src = render_entry(rec["proposed_entry"])
    key = f"{rec['proposed_entry']['library']}|{rec['proposed_entry']['component']}"
    if not args.confirm:
        print("\n  would add to unstated/_catalogue.py:\n")
        print(entry_src)
        print(f"\n  and to unstated/_manifest.py:ESTABLISHED:\n    {key!r},")
        print("\n  re-run with --confirm to apply.")
        return 0

    cat = ROOT / "unstated" / "_catalogue.py"
    s = cat.read_text()
    cat.write_text(s.rstrip().rstrip(")").rstrip() + "\n" + entry_src + "\n)\n")

    man = ROOT / "unstated" / "_manifest.py"
    m = man.read_text()
    anchor = "WITHDRAWALS: tuple[Withdrawal, ...]"
    head, tail = m.split(anchor, 1)
    head = head.rstrip().rstrip(")").rstrip() + f'\n    {key!r},\n)\n\n#: Findings lawfully withdrawn. Empty is the expected state.\n'
    man.write_text(head + anchor + tail)

    print(f"\n  PROMOTED {key}")
    print("  now run: python tools/regen_readme_table.py && python -m pytest -q")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
