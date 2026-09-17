"""Regenerate the README's findings table from unstated.CATALOGUE.

Run after adding a catalogue entry. `test_the_readme_table_matches_the_catalogue` fails
until you do, which is the point: the README went stale by three audits once, and a
document asserting something the code no longer supports is the exact failure this
catalogue is about.

    python tools/regen_readme_table.py
"""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from unstated import CATALOGUE  # noqa: E402

BEGIN = "<!-- BEGIN CATALOGUE TABLE (generated from unstated.CATALOGUE — do not hand-edit) -->"
END = "<!-- END CATALOGUE TABLE -->"
COUNT_BEGIN = "<!-- CATALOGUE COUNT -->"
COUNT_END = "<!-- /CATALOGUE COUNT -->"
PROJECT_BEGIN = "<!-- PROJECT COUNT -->"
PROJECT_END = "<!-- /PROJECT COUNT -->"


def _first_sentence(text: str, limit: int) -> str:
    out = text.split(". ")[0].strip().rstrip(".")
    return out if len(out) <= limit else out[: limit - 3] + "..."


def build_table() -> str:
    rows = [
        "| library | component | affected versions | assumption | measured | detection |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for entry in sorted(CATALOGUE, key=lambda e: e.library):
        detection = _first_sentence(entry.impact.detection, 46) if entry.impact else ""
        span = _first_sentence(entry.affected_versions, 64)
        if entry.is_resolved:
            span += f" — **fixed in {entry.resolved_in}**"
        rows.append(
            f"| `{entry.library}` | `{entry.component}` "
            f"| {span} "
            f"| {_first_sentence(entry.assumption, 74)} "
            f"| {_first_sentence(entry.cost_when_violated, 150)} "
            f"| {detection} |"
        )
    return "\n".join(rows)


def main() -> int:
    readme = ROOT / "README.md"
    text = readme.read_text()
    if BEGIN not in text or END not in text:
        print("markers not found in README.md", file=sys.stderr)
        return 1
    head, rest = text.split(BEGIN, 1)
    _, tail = rest.split(END, 1)
    text = f"{head}{BEGIN}\n{build_table()}\n{END}{tail}"

    # The prose count drifted too, so it is generated from the same source.
    if COUNT_BEGIN in text and COUNT_END in text:
        head, rest = text.split(COUNT_BEGIN, 1)
        _, tail = rest.split(COUNT_END, 1)
        text = f"{head}{COUNT_BEGIN}{len(CATALOGUE)}{COUNT_END}{tail}"

    if PROJECT_BEGIN in text and PROJECT_END in text:
        projects = len({e.library for e in CATALOGUE})
        head, rest = text.split(PROJECT_BEGIN, 1)
        _, tail = rest.split(PROJECT_END, 1)
        text = f"{head}{PROJECT_BEGIN}{projects}{PROJECT_END}{tail}"

    readme.write_text(text)
    print(f"README table regenerated from {len(CATALOGUE)} catalogue entries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
