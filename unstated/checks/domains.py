"""Does this domain name encode to one host, or two?

Catalogue entry: idna 3.11 against Python's built-in ``"idna"`` codec.

The `idna` package implements IDNA 2008. Python's built-in ``str.encode("idna")``
implements IDNA 2003. The two standards deliberately differ on several characters, so a
program that encodes a domain in two places can hold two different hosts for one input —
and both are syntactically valid, registrable names.
"""

from __future__ import annotations

from typing import Iterable

from .._finding import Finding


def _encode_both(domain: str) -> tuple[str | None, str | None]:
    """(IDNA 2008 via the package, IDNA 2003 via the stdlib codec); None where refused."""
    try:
        import idna as _idna
    except ImportError:  # pragma: no cover
        return None, None
    try:
        new = _idna.encode(domain).decode("ascii")
    except Exception:
        new = None
    try:
        old = domain.encode("idna").decode("ascii")
    except Exception:
        old = None
    return new, old


def check_domain_encoding(domains: Iterable[str]) -> Finding | None:
    """Return a Finding when any domain encodes differently under the two standards.

    ``None`` means every name examined encodes identically, which is true of most
    internationalised domains — umlauts, accents and CJK are unaffected.
    """
    examined = both_valid_differ = one_refused = 0
    examples: list[str] = []
    for raw in domains:
        text = str(raw).strip()
        if not text:
            continue
        new, old = _encode_both(text)
        if new is None and old is None:
            continue
        examined += 1
        if new == old:
            continue
        if new is None or old is None:
            one_refused += 1
        else:
            both_valid_differ += 1
            if len(examples) < 3:
                examples.append(f"{text!r} -> {new!r} or {old!r}")

    if not examined or not (both_valid_differ or one_refused):
        return None

    return Finding(
        library="idna",
        component="encode (IDNA 2008) vs the stdlib 'idna' codec (IDNA 2003)",
        assumption=(
            "encoding a domain name is deterministic — that one input yields one host"
        ),
        signal=(
            "nothing: both encoders return a syntactically valid domain, and neither "
            "mentions that the other exists or that the standards differ"
        ),
        remedy=(
            "encode in exactly one place and pass the encoded form onward. Never compare "
            "a name encoded by one path against a name encoded by the other. Note that "
            "uts46=True does not reconcile them — it still returns the IDNA 2008 result"
        ),
        observed={
            "domains_examined": examined,
            "both_valid_but_different": both_valid_differ,
            "one_encoder_refused": one_refused,
            "examples": "; ".join(examples),
        },
        severity="high" if both_valid_differ else "medium",
    )
