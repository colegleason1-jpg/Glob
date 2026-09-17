"""Does this version constraint mean what it reads as?

Catalogue entry: packaging 24.0, ``SpecifierSet``.

A specifier's answer depends on two properties of the version string the caller never
stated: whether it is a pre-release, and whether it carries a local segment. Both are
PEP 440 and both are documented. Neither is visible at the call site, and they pull in
opposite directions — one makes the constraint stricter than it reads, the other looser.
"""

from __future__ import annotations

import operator
from typing import Iterable

from .._finding import Finding

_OPS = {">=": operator.ge, ">": operator.gt, "<=": operator.le,
        "<": operator.lt, "==": operator.eq, "!=": operator.ne}


def _ordering_says(spec_text: str, version) -> bool:
    """Does the version satisfy the constraint under plain ordering alone?

    This is the baseline a reader applies: `>=1.0` reads as "orders at or above 1.0".
    """
    from packaging.version import Version

    result = True
    for clause in spec_text.split(","):
        clause = clause.strip()
        for symbol in (">=", "<=", "==", "!=", ">", "<"):
            if clause.startswith(symbol):
                result = result and _OPS[symbol](version, Version(clause[len(symbol):]))
                break
    return result


def check_specifier(specifier: str, versions: Iterable[str]) -> Finding | None:
    """Return a Finding when the specifier's verdict on ``versions`` departs from ordering.

    ``None`` means every candidate is decided by ordering alone, which is what the
    constraint reads as.
    """
    try:
        from packaging.specifiers import InvalidSpecifier, SpecifierSet
        from packaging.version import InvalidVersion, Version
    except ImportError:  # pragma: no cover
        return None

    try:
        spec = SpecifierSet(specifier)
    except InvalidSpecifier:
        return None

    stricter: list[str] = []   # ordering says yes, packaging says no — a pre-release
    looser: list[str] = []     # ordering says no, packaging says yes — a local segment
    examined = 0
    for raw in versions:
        text = str(raw).strip()
        try:
            parsed = Version(text)
        except InvalidVersion:
            continue
        examined += 1
        try:
            ordered = _ordering_says(specifier, parsed)
        except InvalidVersion:
            continue
        if ordered and not spec.contains(text):
            stricter.append(text)
        elif spec.contains(text) and not ordered:
            looser.append(text)

    if not examined or not (stricter or looser):
        return None

    parts = []
    if stricter:
        parts.append(
            f"excludes {len(stricter)} version(s) that order above the bound, because "
            f"they are pre-releases (e.g. {stricter[0]!r})"
        )
    if looser:
        parts.append(
            f"accepts {len(looser)} version(s) that are not the pinned artifact, because "
            f"a local segment is ignored (e.g. {looser[0]!r})"
        )

    return Finding(
        library="packaging",
        component="SpecifierSet",
        assumption=(
            "the caller cares only about ordering — not about whether a candidate is a "
            "pre-release, or carries a local build segment"
        ),
        signal="nothing: the answer is a plain True or False, and both are plausible",
        remedy=(
            "state the intent rather than relying on the default: pass "
            "prereleases=True to accept them, and compare Version(...).local or pin the "
            "artifact by hash when a local build must not satisfy an exact pin"
        ),
        observed={
            "specifier": specifier,
            "versions_examined": examined,
            "stricter_than_it_reads": len(stricter),
            "looser_than_it_reads": len(looser),
            "detail": "; ".join(parts),
        },
        severity="high" if looser else "medium",
    )
