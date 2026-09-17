"""Will this join multiply your rows?

Catalogue entry: pandas 3.0.5, ``DataFrame.merge``.

pandas already ships the guard — ``validate=`` — and it defaults to ``None``. This check
answers the question the default leaves open, before the merge runs, and reports what the
inflation would actually be on these two frames rather than that it could happen.
"""

from __future__ import annotations

from typing import Any, Sequence

from .._finding import Finding


def check_merge(left: Any, right: Any, on: str | Sequence[str]) -> Finding | None:
    """Return a Finding when merging ``left`` and ``right`` on ``on`` would inflate rows.

    ``None`` means the key is unique on at least one side, so the row count is safe.
    """
    keys = [on] if isinstance(on, str) else list(on)
    for frame, name in ((left, "left"), (right, "right")):
        missing = [k for k in keys if k not in frame.columns]
        if missing:
            raise KeyError(f"{name} frame has no column(s) {missing}")

    left_dupes = int(left.duplicated(subset=keys).sum())
    right_dupes = int(right.duplicated(subset=keys).sum())
    if not (left_dupes and right_dupes):
        return None  # unique on one side: the join cannot multiply

    # What the inflation actually is, on these frames, without materialising the join.
    left_counts = left.groupby(keys, dropna=False).size()
    right_counts = right.groupby(keys, dropna=False).size()
    shared = left_counts.index.intersection(right_counts.index)
    if len(shared) == 0:
        return None
    produced = int((left_counts.loc[shared] * right_counts.loc[shared]).sum())
    matched = int(left_counts.loc[shared].sum())
    if produced <= matched:
        return None

    factor = produced / matched
    return Finding(
        library="pandas",
        component="DataFrame.merge",
        assumption="the join key is unique on at least one side",
        signal=(
            "nothing: no exception, no warning, no nulls introduced, dtypes preserved "
            "and every value still in range — only the row count and every sum change"
        ),
        remedy=(
            f"pass validate= to merge (m:1, 1:m or 1:1 as appropriate), or de-duplicate "
            f"the right frame on {keys} before joining"
        ),
        observed={
            "keys": ",".join(keys),
            "duplicate_keys_left": left_dupes,
            "duplicate_keys_right": right_dupes,
            "matching_rows_in": matched,
            "rows_out": produced,
            "inflation": f"{factor:.2f}x",
        },
        severity="high" if factor > 1.05 else "medium",
    )
