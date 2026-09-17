"""Checks for preconditions your dependencies rely on and do not state.

Every entry in this package comes from the same measured pattern:

    a component works under an assumption about your data, nothing signals when the
    assumption does not hold, and the resulting failure passes every ordinary check —
    no exception, no warning, no nulls, right dtype, values in range.

The checks are small. `assumption_dependent_dates` is three lines of real work. The
expensive part is not writing them: it is establishing, for each library, that the
assumption exists, measuring what it costs when violated, and confirming the check
catches it. That work is recorded per entry in ``CATALOGUE`` and in ``docs/``.

The assumption is always one made **about the caller's data, that the caller was never
asked about**. A parameter the library did offer at the call site, left at its default, is
not an entry here however sharp the consequence — that boundary was drawn when
``cryptography`` was audited and came back clean, and it is what keeps this a catalogue
rather than a list of configuration advice.

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

__all__ = ["Finding", "CATALOGUE", "CatalogueEntry", "check_dates", "check_merge", "check_split", "check_paginated", "check_specifier", "check_domain_encoding", "check_retry", "check_response_encoding", "check_detected_encoding"]
__version__ = "0.1.0"
