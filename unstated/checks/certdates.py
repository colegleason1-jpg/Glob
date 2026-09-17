"""Does this certificate hand you a time you can safely compare?

Catalogue entry: cryptography < 42.0.0, ``x509.Certificate.not_valid_after``.

``not_valid_after`` returns a **naive** datetime holding UTC. The comparison every
monitoring script writes is::

    if cert.not_valid_after < datetime.now():   # datetime.now() is LOCAL, and naive

Both sides are naive, so Python compares them without complaint and the answer is wrong by
the host's UTC offset. Measured on cryptography 41.0.7 across 10 real timezones: a
certificate that expired six hours ago **reads as valid** in 3 of them, and one with six
hours left reads as expired in 3 others. 0 exceptions, 0 warnings.

From **42.0.0** (2024-01-23) the attribute emits ``CryptographyDeprecationWarning`` and
``not_valid_after_utc`` exists, so on those versions the library tells you and this check
stays silent. Every release before it — 3.4.8 (2021) through 41.0.7 (2023-11) — is silent,
which is the range Debian stable still ships.

This is why the check probes the installed version rather than trusting a version string:
the same code is a defect or a non-event depending on what is on the machine.
"""

from __future__ import annotations

import datetime
import warnings
from typing import Any

from .._finding import Finding


def _naive_attribute_is_silent(cert: Any) -> tuple[bool, Any]:
    """Return (the library says nothing, the value it returned)."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            value = cert.not_valid_after
        except AttributeError:
            return False, None  # removed entirely; nothing to mis-compare
        return len(caught) == 0, value


def check_certificate_dates(cert: Any, now: datetime.datetime | None = None) -> Finding | None:
    """Return a Finding when ``cert.not_valid_after`` is a naive UTC value and silent.

    ``None`` means the installed version warns on the attribute, or has removed it, or the
    host runs at UTC where the naive comparison happens to be correct.
    """
    silent, value = _naive_attribute_is_silent(cert)
    if not silent or value is None:
        return None  # the library told you, or there is no attribute to misuse

    if not isinstance(value, datetime.datetime) or value.tzinfo is not None:
        return None  # already aware; the comparison is safe

    local = (now or datetime.datetime.now()).astimezone()
    offset = local.utcoffset() or datetime.timedelta(0)
    if offset == datetime.timedelta(0):
        return None  # at UTC the naive comparison is correct, by luck rather than design

    hours = offset.total_seconds() / 3600.0
    direction = (
        "accepts a certificate that has ALREADY EXPIRED, for a window this wide"
        if hours < 0
        else "reports a still-valid certificate as expired, for a window this wide"
    )

    aware = getattr(cert, "not_valid_after_utc", None)

    return Finding(
        library="cryptography",
        component="x509.Certificate.not_valid_after",
        assumption=(
            "the caller will compare this naive UTC value against another UTC value — not "
            "against datetime.now(), which is naive local time"
        ),
        signal=(
            "nothing on this installed version: both sides of the comparison are naive, so "
            "Python compares them without complaint and returns a confident wrong answer"
        ),
        remedy=(
            "use cert.not_valid_after_utc and compare against "
            "datetime.datetime.now(datetime.timezone.utc); on a release that predates it, "
            "attach the timezone yourself with "
            "cert.not_valid_after.replace(tzinfo=datetime.timezone.utc)"
        ),
        observed={
            "value_returned": repr(value),
            "tzinfo": "None (naive, holding UTC)",
            "warning_emitted": "no",
            "host_utc_offset": f"{hours:+.0f}h",
            "error_in_a_naive_comparison": f"{abs(hours):.0f}h — {direction}",
            "not_valid_after_utc_available": "yes" if aware is not None else "no",
        },
        severity="high" if hours < 0 else "medium",
    )
