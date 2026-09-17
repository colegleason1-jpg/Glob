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


def _first_sentence(text: str, limit: int) -> str:
    out = text.split(". ")[0].strip().rstrip(".")
    return out if len(out) <= limit else out[: limit - 3] + "..."


def build_table() -> str:
    rows = [
        "| library | component | assumption | measured | detection |",
        "| --- | --- | --- | --- | --- |",
    ]
    for entry in sorted(CATALOGUE, key=lambda e: e.library):
        detection = _first_sentence(entry.impact.detection, 46) if entry.impact else ""
        rows.append(
            f"| `{entry.library}` | `{entry.component}` "
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
    readme.write_text(f"{head}{BEGIN}\n{build_table()}\n{END}{tail}")
    print(f"README table regenerated from {len(CATALOGUE)} catalogue entries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
