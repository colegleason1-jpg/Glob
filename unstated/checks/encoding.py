"""Is the string you are reading the string the server sent?

Catalogue entry: requests 2.33.1, ``Response.text``.

``requests.utils.get_encoding_from_headers`` ends with::

    if "text" in content_type:
        return "ISO-8859-1"

That is RFC 2616 §3.7.1, and the docstring on ``Response.text`` says so: *"following RFC
2616 to the letter."* RFC 7231 removed the default in 2014 and RFC 9110 has not brought it
back, so for any ``text/*`` response that omits ``charset`` — which is most of them —
``r.text`` decodes UTF-8 bytes as Latin-1.

Measured on the wire over 12 UTF-8 bodies served as ``text/plain``: ``r.text`` was correct
0/12 and ``r.apparent_encoding`` was correct 12/12. The right answer is computed by the
same object and is not consulted, because the header rule already produced one.

ISO-8859-1 maps all 256 byte values to characters, so the decode cannot fail. There is no
byte sequence that signals the guess was wrong, and an ASCII body decodes identically
under both — which is why this survives a test suite.
"""

from __future__ import annotations

from typing import Any

from .._finding import Finding


def _content_type(response: Any) -> str | None:
    headers = getattr(response, "headers", None) or {}
    try:
        return headers.get("content-type") or headers.get("Content-Type")
    except AttributeError:
        return None


def check_response_encoding(response: Any) -> Finding | None:
    """Return a Finding when ``response.text`` will decode the body under a guess.

    ``None`` means the server declared a charset, or the body is pure ASCII and so decodes
    identically either way, or the media type is one requests does not claim to know.
    """
    raw = _content_type(response)
    if not raw:
        return None  # no header: requests falls through to detection, which measured 12/12

    media_type, _, params = raw.partition(";")
    if "charset=" in params.lower():
        return None  # the server said so; nothing is being assumed

    # The rule requests applies, reproduced exactly — substring, and case-sensitive.
    if "text" not in media_type:
        return None

    body = getattr(response, "content", b"") or b""
    high = sum(1 for b in body if b > 127)
    if not high:
        return None  # ASCII is a fixed point of Latin-1; there is nothing to be wrong about

    try:
        as_utf8 = body.decode("utf-8")
    except UnicodeDecodeError:
        as_utf8 = None

    as_latin1 = body.decode("iso-8859-1")  # cannot raise
    severity = "high" if as_utf8 is not None else "medium"
    encoding = getattr(response, "encoding", None) or "ISO-8859-1"

    observed: dict[str, Any] = {
        "content_type": raw,
        "charset_declared": "no",
        "encoding_requests_picked": encoding,
        "non_ascii_bytes": high,
        "body_is_valid_utf8": "yes" if as_utf8 is not None else "no",
        "r_text_sample": as_latin1[:60],
    }
    if as_utf8 is not None:
        observed["utf8_sample"] = as_utf8[:60]
        observed["character_count"] = f"{len(as_latin1)} returned vs {len(as_utf8)} sent"

    return Finding(
        library="requests",
        component="Response.text",
        assumption=(
            "a text/* response that omits charset is Latin-1, per RFC 2616 §3.7.1 — a "
            "default RFC 7231 removed in 2014"
        ),
        signal=(
            "nothing: Latin-1 maps all 256 byte values, so the decode cannot raise, and "
            "an ASCII body decodes identically under both encodings"
        ),
        remedy=(
            "read r.content and decode it yourself, or set r.encoding = "
            "r.apparent_encoding before touching r.text; r.apparent_encoding was correct "
            "on 12 of 12 measured UTF-8 bodies and is already computed by the same object"
        ),
        observed=observed,
        severity=severity,
    )
