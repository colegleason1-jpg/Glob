"""Checks for preconditions your dependencies rely on and do not state.

Every entry in this package comes from the same measured pattern:

    a component works under an assumption about your data, nothing signals when the
    assumption does not hold, and the resulting failure passes every ordinary check —
    no exception, no warning, no nulls, right dtype, values in range.

The checks are small. `assumption_dependent_dates` is three lines of real work. The
expensive part is not writing them: it is establishing, for each library, that the
assumption exists, measuring what it costs when violated, and confirming the check
catches it. That work is recorded per entry in ``CATALOGUE`` and in ``docs/``.

The assumption is **misdirection, not omission** — a call site that actively reads as
asserting something false. ``Retry(total=3)`` is an entry because a parameter you *did* set
does not mean what its name says; a different parameter governs the behaviour.

An earlier draft of this paragraph said the line was "an assumption about your data you
were never asked about, as against a parameter you were offered". That was wrong, and it
contradicted ``urllib3.Retry`` — ``status_forcelist`` is exactly a parameter you are
offered, with a default. The principle had been fitted to a verdict rather than derived
from the entries. It is recorded in ``docs/cold-test-cryptography.md`` rather than quietly
replaced, for the same reason the entries carry their measurements.

**An entry is a claim about versions, not about a library.** A fix upstream bounds an entry
(``resolved_in``); it does not delete one, because the affected range stays installed for
years. ``cryptography.Certificate.not_valid_after`` is silently naive from 3.4.8 (2021) to
41.0.7 (2023) and warns from 42.0.0 — the same attribute, a security defect on one machine
and a non-event on the next. That is why the checks probe the installed library rather than
comparing version strings.

A finding here is never a claim that a library is broken. In every case so far the
behaviour is arithmetic working correctly under a condition nobody wrote down, and in
one case (dateutil) it is filed upstream and has been for years. The gap this package
addresses is between what is known somewhere and what reaches the person running the
code.

Usage::

    from unstated import check_dates, check_merge
    finding = check_dates(df["signup_date"])
    if finding:
        print(finding.summary())
"""

from ._finding import Finding
from ._catalogue import CATALOGUE, CatalogueEntry
from .checks.dates import check_dates
from .checks.frames import check_merge
from .checks.splits import check_split
from .checks.aws import check_paginated
from .checks.versions import check_specifier
from .checks.domains import check_domain_encoding
from .checks.retries import check_retry
from .checks.encoding import check_response_encoding
from .checks.detection import check_detected_encoding
from .checks.certdates import check_certificate_dates

__all__ = ["Finding", "CATALOGUE", "CatalogueEntry", "check_dates", "check_merge", "check_split", "check_paginated", "check_specifier", "check_domain_encoding", "check_retry", "check_response_encoding", "check_detected_encoding", "check_certificate_dates"]
__version__ = "0.1.0"
