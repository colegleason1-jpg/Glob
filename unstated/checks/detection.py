"""Was the encoding detected, or was it guessed?

Catalogue entry: charset-normalizer 3.4.6, ``detect`` / ``from_bytes(...).best()``.

Detection works on two entirely different kinds of evidence, and the return value does not
distinguish them.

*UTF-8 and the multi-byte encodings are verifiable.* Most byte sequences are not valid
UTF-8 — of 12 legacy-encoded sentences measured, 0 were also valid UTF-8 — so a successful
decode is real evidence. Measured over 20 texts encoded UTF-8: 20/20 round-trip.

*The single-byte encodings are not.* Every byte value 0-255 decodes in ISO-8859-1, and 251
of 256 in CP1250, so a successful decode is evidence of nothing. Measured over the same 20
texts in their own legacy encodings: **8 of 20 round-trip to a different string**, with 0
exceptions and 0 warnings.

``detect()`` reports ``confidence = 1.0 - chaos``, and ``chaos`` measures whether the
decoded output *looks like* coherent text — which a wrong single-byte decode also does.
Measured: 7 of the 8 wrong answers came back at confidence **1.000**, and no threshold
separates right from wrong (wrong 0.900-1.000, correct 0.938-1.000).

So this check does not try to detect better. It reports, for the caller's own bytes,
**how many different strings the plausible encodings produce** — which is the number the
confidence field does not carry.
"""

from __future__ import annotations

from typing import Any

from .._finding import Finding

#: Single-byte encodings in wide use for text that predates UTF-8. Nothing in the bytes
#: can rule any of them out, which is the whole point.
_SINGLE_BYTE = (
    "cp1250", "cp1251", "cp1252", "cp1253", "cp1254", "cp1255", "cp1256", "cp1257",
    "cp1258", "cp850", "cp866", "iso-8859-1", "iso-8859-2", "iso-8859-5", "iso-8859-7",
    "iso-8859-9", "iso-8859-15", "koi8-r", "mac-roman",
)

_BOMS = (b"\xef\xbb\xbf", b"\xff\xfe", b"\xfe\xff", b"\xff\xfe\x00\x00", b"\x00\x00\xfe\xff")


def check_detected_encoding(payload: bytes, detected: str | None = None) -> Finding | None:
    """Return a Finding when the detected encoding cannot be verified from the bytes.

    ``payload`` is the byte string that was detected. ``detected`` is what the detector
    said, if you have it — it is reported back but not trusted.

    ``None`` means the answer rests on evidence: the bytes carry a BOM, are pure ASCII, or
    are valid UTF-8, or no single-byte reading disagrees with the detected one.
    """
    if not payload:
        return None

    if any(payload.startswith(b) for b in _BOMS):
        return None  # declared, not inferred

    if not any(b > 127 for b in payload):
        return None  # ASCII is the same string under every candidate

    try:
        payload.decode("utf-8")
        return None  # structurally verified: most byte strings are not valid UTF-8
    except UnicodeDecodeError:
        pass

    readings: dict[str, str] = {}
    decodable = 0
    for candidate in _SINGLE_BYTE:
        try:
            reading = payload.decode(candidate)
        except (UnicodeDecodeError, LookupError):
            continue
        decodable += 1
        readings.setdefault(reading, candidate)

    if len(readings) < 2:
        return None  # every candidate agrees; there is nothing being decided

    chosen = None
    if detected:
        try:
            chosen = payload.decode(detected)
        except (UnicodeDecodeError, LookupError, TypeError):
            chosen = None

    distinct = sorted(readings.items(), key=lambda kv: kv[1])
    if chosen is not None:
        others = [(s, e) for s, e in distinct if s != chosen]
    else:
        others = distinct[1:]

    sample_a = (chosen if chosen is not None else distinct[0][0])[:48]
    sample_b = others[0][0][:48] if others else ""

    return Finding(
        library="charset-normalizer",
        component="detect / from_bytes(...).best()",
        assumption=(
            "the caller's bytes are UTF-8 or a multi-byte encoding, where a successful "
            "decode is evidence; for a single-byte encoding every byte decodes under "
            "every candidate, so nothing in the bytes can confirm the answer"
        ),
        signal=(
            "nothing, and worse than nothing: detect() reports confidence = 1.0 - chaos, "
            "and chaos measures whether the output looks like text — which a wrong "
            "single-byte decode also does. 7 of 8 wrong answers measured at confidence "
            "1.000"
        ),
        remedy=(
            "get the encoding from outside the bytes — a Content-Type charset, an upload "
            "form field, a per-source configured default — and record which one you used; "
            "if you must detect, keep the raw bytes so the decision can be revisited, "
            "because a re-decode is impossible once the string is stored"
        ),
        observed={
            "bytes": len(payload),
            "valid_utf8": "no",
            "detected": detected or "not supplied",
            "single_byte_candidates_that_decode": f"{decodable} of {len(_SINGLE_BYTE)}",
            "distinct_strings_produced": len(readings),
            "reading_a": sample_a,
            "reading_b": sample_b,
        },
        severity="high" if len(readings) > 2 else "medium",
    )
