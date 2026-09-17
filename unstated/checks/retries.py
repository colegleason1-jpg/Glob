"""Does this retry configuration retry the thing you are worried about?

Catalogue entry: urllib3 2.6.3, ``util.retry.Retry``.

``Retry(total=3)`` reads as "try three more times if it fails". Measured against a server
returning 503, it sends **one** request: ``status_forcelist`` is empty by default, so HTTP
error statuses are not retried at all — only connection and read errors are.

Adding the statuses exposes the second default: ``backoff_factor=0``, so the retries fire
with no delay at a server that is already failing.

And the third is the opposite mistake, usually made while fixing the first two: setting
``allowed_methods=None`` to make a POST retry replays a non-idempotent request.
"""

from __future__ import annotations

from typing import Any

from .._finding import Finding


def check_retry(retry: Any) -> Finding | None:
    """Return a Finding when a ``Retry`` will not do what its call site reads as.

    ``None`` means the configuration retries statuses, spaces its attempts, and has not
    been opened up to non-idempotent methods.
    """
    total = getattr(retry, "total", None)
    if total in (None, 0, False):
        return None  # retries are off; nothing is being promised

    forcelist = getattr(retry, "status_forcelist", None) or set()
    backoff = getattr(retry, "backoff_factor", None) or 0
    methods = getattr(retry, "allowed_methods", "unset")

    gaps: list[str] = []
    severity = "medium"

    if not forcelist:
        gaps.append(
            "status_forcelist is empty, so no HTTP status is retried — a 500, 502 or 503 "
            "is handed back to the caller on the first attempt"
        )
        severity = "high"
    if forcelist and not backoff:
        gaps.append(
            "backoff_factor is 0, so every retry fires immediately; a failing service "
            "receives the whole burst within milliseconds"
        )
        severity = "high"
    if methods is None:
        gaps.append(
            "allowed_methods is None, so every method is retried including POST and "
            "PATCH — a non-idempotent request is replayed"
        )
        severity = "high"

    if not gaps:
        return None

    return Finding(
        library="urllib3",
        component="util.retry.Retry",
        assumption=(
            "the caller wants connection-level retries only, spaced by nothing, on "
            "methods the library judged idempotent"
        ),
        signal=(
            "nothing: the request succeeds or returns its error response normally, and a "
            "retry that never happened is indistinguishable from one that did not help"
        ),
        remedy=(
            "name what you are retrying: status_forcelist=[500, 502, 503, 504] for server "
            "errors, backoff_factor>=0.5 so attempts are spaced, and leave allowed_methods "
            "at its default unless the endpoint is genuinely idempotent or you send an "
            "idempotency key"
        ),
        observed={
            "total": total,
            "status_forcelist": sorted(forcelist) if forcelist else "empty",
            "backoff_factor": backoff,
            "allowed_methods": "all (None)" if methods is None else "library default",
            "gaps": "; ".join(gaps),
        },
        severity=severity,
    )
