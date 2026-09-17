"""Did this AWS response contain everything, or just the first page?

Catalogue entry: boto3 1.43.96, list/scan/query operations.

Every paginated AWS API returns a truncated first page and sets a marker the caller has to
know to read. The safe path — ``client.get_paginator(...)`` — exists and is not the one a
first draft reaches for.

The markers differ by service, which is part of the problem: there is no single field to
check and no round number to learn. S3 stops at 1,000 objects. DynamoDB stops at 1 MB, so
its cutoff moves with row width — the same code against the same table returns a different
fraction after someone adds a column.
"""

from __future__ import annotations

from typing import Any, Mapping

from .._finding import Finding

#: Truncation markers across AWS services. A response carrying any of these has more data
#: behind it. Boolean markers count only when true; the rest count whenever present.
BOOLEAN_MARKERS = ("IsTruncated",)
TOKEN_MARKERS = (
    "NextToken", "NextMarker", "NextContinuationToken", "LastEvaluatedKey",
    "Marker", "NextPageToken", "nextToken",
)

#: Keys whose value is the returned page of records, for reporting how much was seen.
PAYLOAD_KEYS = ("Contents", "Items", "Objects", "Versions", "Reservations", "Users",
                "Roles", "Buckets", "Functions", "LogGroups", "Parameters")


def check_paginated(response: Mapping[str, Any], operation: str = "") -> Finding | None:
    """Return a Finding when ``response`` is one page of a larger result set.

    ``None`` means the response is complete — no truncation marker is set.
    """
    if not isinstance(response, Mapping):
        return None

    markers: list[str] = [m for m in BOOLEAN_MARKERS if response.get(m) is True]
    markers += [m for m in TOKEN_MARKERS if response.get(m)]
    if not markers:
        return None

    seen = None
    for key in PAYLOAD_KEYS:
        value = response.get(key)
        if isinstance(value, list):
            seen = (key, len(value))
            break
    if seen is None and isinstance(response.get("Count"), int):
        seen = ("Count", response["Count"])

    observed: dict[str, Any] = {
        "operation": operation or "(not given)",
        "truncation_markers": ",".join(markers),
        "records_in_this_page": seen[1] if seen else "unknown",
    }
    if seen:
        observed["payload_key"] = seen[0]

    return Finding(
        library="boto3",
        component=operation or "list/scan/query operation",
        assumption="the caller's result set fits in one page",
        signal=(
            f"only {', '.join(markers)} in the response body — no exception, no warning, "
            "HTTP 200, and a well-formed list of records that is simply short"
        ),
        remedy=(
            "use client.get_paginator(<operation>).paginate(...) and consume every page, "
            "or loop on the marker explicitly. Do not rely on the page size: S3 stops at "
            "1,000 records while DynamoDB stops at 1 MB, so its cutoff moves with row width"
        ),
        observed=observed,
        severity="high",
    )
