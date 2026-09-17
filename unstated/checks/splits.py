"""Will this train/test split score the model on rows it already saw?

Catalogue entry: scikit-learn 1.9.1, ``model_selection.train_test_split``.

The assumption is that rows are independent. When several rows share a subject — repeated
measurements, sessions per user, images per patient, many rows per customer — a random
split puts the same subject on both sides and the score reports memorisation.

``train_test_split`` has no ``groups`` argument and its docstring contains none of
"group", "independent", "leak", "subject" or "cluster". The remedy ships in the same
module under a different name.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Iterable

from .._finding import Finding


def check_split(groups: Iterable[Any], test_size: float = 0.25) -> Finding | None:
    """Return a Finding when ``groups`` has repeats, so a random split would leak.

    ``groups`` is the identifier that rows share — a subject id, user id, patient id,
    session id. ``None`` means every row is its own group and a random split is sound.
    """
    counts = Counter(groups)
    if not counts:
        return None

    rows = sum(counts.values())
    repeated = {g: n for g, n in counts.items() if n > 1}
    if not repeated:
        return None

    rows_in_repeated = sum(repeated.values())
    largest = max(repeated.values())
    # A group of size n survives a split intact with probability p**n + (1-p)**n; anything
    # else puts it on both sides. This is the expected share of groups that will leak.
    p = 1.0 - test_size
    expected_leaking = sum(
        n_rows_groups * (1.0 - (p ** size + (1.0 - p) ** size))
        for size, n_rows_groups in Counter(repeated.values()).items()
    )

    return Finding(
        library="scikit-learn",
        component="model_selection.train_test_split",
        assumption="rows are independent — that no two rows share a subject",
        signal=(
            "nothing: train_test_split takes no groups argument, and its docstring "
            "contains none of 'group', 'independent', 'leak', 'subject' or 'cluster'"
        ),
        remedy=(
            "use GroupShuffleSplit or GroupKFold from the same module, passing these "
            "identifiers as groups=, so no subject appears on both sides"
        ),
        observed={
            "rows": rows,
            "distinct_groups": len(counts),
            "groups_with_repeats": len(repeated),
            "rows_in_repeated_groups": rows_in_repeated,
            "largest_group": largest,
            "expected_groups_split_across": f"{expected_leaking:.0f}",
        },
        severity="high" if rows_in_repeated / rows > 0.1 else "medium",
    )
