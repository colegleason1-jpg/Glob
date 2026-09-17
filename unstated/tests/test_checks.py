"""Each check has to do two things: fire on the defect, and stay silent otherwise.

The second half is the one that decides whether this is a tool or a nuisance. A check
that flags everything is noise, gets switched off in the first week, and takes the real
findings with it — so every check here is tested against input it must NOT flag.
"""

from __future__ import annotations

import datetime
import random

import pandas as pd
import pytest

from unstated import CATALOGUE, check_dates, check_merge


# --------------------------------------------------------------------------- #
# dates
# --------------------------------------------------------------------------- #

def _dates(n=400, seed=7):
    rng = random.Random(seed)
    start = datetime.date(2023, 1, 1)
    return [start + datetime.timedelta(days=rng.randrange(365)) for _ in range(n)]


def test_a_day_first_column_is_flagged():
    """The measured case: 37.2% of such a column parses wrong under the defaults."""
    finding = check_dates(d.strftime("%d/%m/%Y") for d in _dates())
    assert finding is not None
    assert finding.severity == "high"
    assert float(finding.observed["rate"].rstrip("%")) > 20.0
    assert "isoparse" in finding.remedy


def test_a_us_column_is_flagged_too():
    """Ambiguity is symmetric. A US-ordered column is just as convention-dependent —
    it happens to be right under the default, which is luck, not safety."""
    assert check_dates(d.strftime("%m/%d/%Y") for d in _dates()) is not None


def test_a_month_name_column_is_not_flagged():
    """The silence case that matters most: an unambiguous format must pass clean."""
    assert check_dates(d.strftime("%d %b %Y") for d in _dates()) is None


def test_an_empty_or_unparseable_column_is_not_flagged():
    """Unparseable input is a different problem, and a loud one. Not this check's job."""
    assert check_dates([]) is None
    assert check_dates(["", "   ", "not a date", "banana"]) is None


def test_iso_is_flagged_and_the_reason_is_in_the_remedy():
    """ISO reads correctly under the default and is transposed by dayfirst=True, so it
    IS convention-dependent — dateutil/dateutil#402. Flagging it is correct, and the
    remedy has to say why, or the finding reads as a false positive."""
    finding = check_dates(d.isoformat() for d in _dates())
    assert finding is not None
    assert "isoparse" in finding.remedy and "#402" in finding.remedy


# --------------------------------------------------------------------------- #
# merge
# --------------------------------------------------------------------------- #

def test_a_many_to_many_join_is_flagged_with_its_real_inflation():
    left = pd.DataFrame({"k": [1, 1, 2, 3], "v": [10, 20, 30, 40]})
    right = pd.DataFrame({"k": [1, 1, 2], "w": ["a", "b", "c"]})
    finding = check_merge(left, right, on="k")
    assert finding is not None
    # k=1: 2 left x 2 right = 4; k=2: 1 x 1 = 1. Five rows out of three matching in.
    assert finding.observed["rows_out"] == 5
    assert finding.observed["matching_rows_in"] == 3
    assert pd.merge(left, right, on="k").shape[0] == finding.observed["rows_out"], (
        "the predicted row count must match what merge actually produces"
    )


def test_a_many_to_one_join_is_not_flagged():
    """The common, safe case. Flagging it would make the check useless."""
    left = pd.DataFrame({"k": [1, 1, 2, 3], "v": [10, 20, 30, 40]})
    right = pd.DataFrame({"k": [1, 2, 3], "w": ["a", "b", "c"]})
    assert check_merge(left, right, on="k") is None


def test_duplicates_on_both_sides_that_never_meet_are_not_flagged():
    """Duplicate keys are not the defect — duplicate keys that MATCH are. A check that
    fired on the former would cry wolf on every join against a reference table."""
    left = pd.DataFrame({"k": [1, 1, 2], "v": [1, 2, 3]})
    right = pd.DataFrame({"k": [8, 8, 9], "w": ["a", "b", "c"]})
    assert check_merge(left, right, on="k") is None


def test_composite_keys_are_handled():
    left = pd.DataFrame({"a": [1, 1], "b": ["x", "x"], "v": [1, 2]})
    right = pd.DataFrame({"a": [1, 1], "b": ["x", "x"], "w": [3, 4]})
    finding = check_merge(left, right, on=["a", "b"])
    assert finding is not None and finding.observed["rows_out"] == 4


def test_a_missing_key_column_is_an_error_not_a_finding():
    left = pd.DataFrame({"k": [1]})
    right = pd.DataFrame({"j": [1]})
    with pytest.raises(KeyError):
        check_merge(left, right, on="k")


# --------------------------------------------------------------------------- #
# catalogue
# --------------------------------------------------------------------------- #

def test_every_catalogue_entry_carries_its_evidence_and_a_measured_cost():
    """An entry without a number is an opinion. The catalogue is only worth something
    if each row can be checked by the reader against the run that produced it."""
    assert CATALOGUE, "the catalogue is empty"
    for entry in CATALOGUE:
        assert entry.evidence.endswith(".md"), entry
        assert any(ch.isdigit() for ch in entry.cost_when_violated), (
            f"{entry} states no measured cost"
        )
        assert entry.upstream_status, entry
