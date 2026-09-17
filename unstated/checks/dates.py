"""Does this column's meaning depend on a date convention nobody declared?

Catalogue entry: python-dateutil 2.9.0, ``parser.parse``.

The check is the whole idea in one function: parse each value under both conventions and
flag the ones that move. It needs no knowledge of which locale produced the file, and it
does not try to guess the right answer — guessing is what caused the problem. It reports
that a choice is being made silently, and hands the decision back.
"""

from __future__ import annotations

from typing import Iterable, Sequence

from .._finding import Finding

#: Values sampled before giving an answer. Parsing is ~45 us per value per convention, so
#: 5,000 keeps a check under half a second on a column of any size. Sampling is honest
#: here because the question is "does this column contain ambiguity", not "how many rows" —
#: the count is reported as a rate over what was examined.
MAX_SAMPLE = 5_000


def check_dates(values: Iterable[str], sample: int = MAX_SAMPLE) -> Finding | None:
    """Return a Finding when the parse of ``values`` depends on an undeclared convention.

    ``None`` means every value examined reads the same under both conventions — an ISO
    column, or one with the month spelled out, clears here.
    """
    try:
        from dateutil import parser as _parser
    except ImportError:  # pragma: no cover - dateutil absent means nothing to check
        return None

    seen = examined = flipped = 0
    example: tuple[str, str, str] | None = None
    for raw in values:
        if seen >= sample:
            break
        seen += 1
        text = str(raw).strip()
        if not text:
            continue
        try:
            a = _parser.parse(text)
            b = _parser.parse(text, dayfirst=True)
        except (ValueError, OverflowError, TypeError):
            continue  # unparseable is a different problem, and a loud one
        examined += 1
        if a.date() != b.date():
            flipped += 1
            if example is None:
                example = (text, str(a.date()), str(b.date()))

    if not examined or not flipped:
        return None

    rate = flipped / examined
    return Finding(
        library="python-dateutil",
        component="parser.parse",
        assumption=(
            "month-before-day ordering — and it is decided per string, so one column can "
            "come back under two conventions at once"
        ),
        signal="nothing: no exception, no warning, and every value is a valid date",
        remedy=(
            "declare the convention at the call site (dayfirst=), and route ISO 8601 "
            "values to dateutil.parser.isoparse, which cannot be flipped — dayfirst=True "
            "reorders ISO dates (dateutil/dateutil#402)"
        ),
        observed={
            "values_examined": examined,
            "convention_dependent": flipped,
            "rate": f"{rate:.1%}",
            "example": (
                f"{example[0]!r} -> {example[1]} or {example[2]}" if example else ""
            ),
        },
        severity="high" if rate > 0.05 else "medium",
    )
