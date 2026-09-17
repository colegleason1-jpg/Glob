# Audit 13: cryptography — protocol rank 10 — **CLEAN**

2026-09-17 · **AUDITING: cryptography 50.0.1 (PyCA)** · protocol rank **10** of 15,000.

**Pre-registered eligibility:** *eligible — key and certificate handling branches on
properties of supplied material.*

**Outcome: CLEAN.** Thirteen probes across Fernet and X.509. The library behaved correctly
or raised on nine of them. Nothing rose to catalogue grade, and this is published exactly
as a finding would be — that was the deal when [the protocol](TARGETS.md) was written.

The installed version was 41.0.7 (Debian's). A top-10 package deserves a current
measurement, so 50.0.1 was installed in a clean venv and audited there. **That decision
turned out to matter — see the last section.**

## Hypotheses, registered before measuring

| | hypothesis | outcome |
| --- | --- | --- |
| H1 | `Fernet.decrypt(token)` with no `ttl` accepts an arbitrarily old token, silently | **reproduced**, but see the verdict below |
| H2 | `MultiFernet.rotate()` resets the token timestamp, defeating a `ttl` check | **not reproduced** — the timestamp is preserved exactly; age reset was 0 days |
| H3 | `not_valid_after` is naive; compared against local-time `now()` it is wrong by the UTC offset | **LOUD** — emits `CryptographyDeprecationWarning`, and `not_valid_after_utc` exists |
| H4 | `load_pem_x509_certificate` on a concatenated chain silently returns only the first | **reproduced narrowly** — see below |

## What the library got right

Nine probes where the natural failure mode simply is not there:

| probe | result |
| --- | --- |
| Is `extract_timestamp` authenticated, or can a token's timestamp be rewritten? | **`InvalidToken`.** The signature is checked before the timestamp is returned. |
| Clock skew — a token minted on a server whose clock is fast | Accepted to 59s, **rejected at 61s** (`MAX_CLOCK_SKEW`). Fails closed. |
| Does `ttl` still apply through `MultiFernet`? | **Yes**, correctly rejected. |
| Does `rotate()` reset the age? | **No.** Timestamp preserved to the second. |
| A 5-cert bundle with one block truncated | **`ValueError`** in 4 of 5 positions |
| A 5-cert bundle with one block's base64 corrupted | **`ValueError`** in 3 of 3 positions |
| A certificate with no SAN | **`ExtensionNotFound`** |
| Wrong password on an encrypted private key | **`ValueError: Incorrect password`**; missing password gives `TypeError` |
| `signature_hash_algorithm` is `None` on Ed25519 — does a weak-algorithm check break? | The natural idiom `alg.name in WEAK` raises **`AttributeError`**. Loud. |

Seven of eight bundle-damage cases raise. The one that does not is truncation of the
**final** block, which is indistinguishable from trailing garbage and is the defined
stopping point.

## The three survivors, and why none of them qualifies

### `Fernet.decrypt()` with no `ttl` accepts a ten-year-old token

Measured, and it does:

| token age | `decrypt()` no ttl | `decrypt(ttl=3600)` | warnings |
| --- | --- | --- | --- |
| just now | accepted | accepted | 0 |
| 1 day | **ACCEPTED** | rejected | 0 |
| 1 year | **ACCEPTED** | rejected | 0 |
| 10 years | **ACCEPTED** | rejected | 0 |

The timestamp is inside the token, authenticated, and free to check. This has the shape of
[audit 11](cold-test-requests.md), where the right answer sat on the same object and was
not consulted.

**It does not qualify, and the reason is worth stating because it sharpens what this
catalogue is for:**

> Every entry so far is an assumption a library makes **about your data**, that you were
> never asked about. dateutil never asks whether a column is day-first — it decides per
> string. requests never asks whether a body is UTF-8 — it assumes. charset-normalizer
> never says its answer is a guess — it reports 1.000.
>
> `ttl=None` is a question you **were** asked, at the call site, by name, and answered by
> omission. The library cannot know whether your token should live an hour or a decade, and
> a default would break every legitimate long-lived use.

That is a real line, and applying it here rather than stretching to an eleventh entry is
the point of having it.

### `load_pem_x509_certificate` on a CA bundle returns one certificate

A 5-certificate bundle loads as one, with 0 warnings and 0 exceptions — **4 of 5 silently
discarded (80%)**. Trailing garbage and a truncated block after the first certificate are
both ignored.

**It does not qualify:** the function is named singular, `load_pem_x509_certificates`
exists and returns all five, and the plural form raises on almost every kind of damage. The
caller asked for one certificate and got one.

### `rfc4514_string()` and `get_attributes_for_oid()` disagree about order

A certificate with two common names:

```
get_attributes_for_oid(CN) -> ['real.example.com', 'evil.example.com']
subject.rfc4514_string()   ->  CN=evil.example.com,CN=real.example.com
```

The first name by index and the first name read left-to-right are **different names**, so a
log line built one way and a policy check built the other disagree about which certificate
this is. Both orderings are correct — RFC 4514 specifies most-specific-first, which reverses
DER order.

**It does not qualify:** multi-CN certificates are non-conformant for TLS, the CA/Browser
Forum forbids them, and no TLS stack has matched on CN for years. The blast radius needs a
caller already doing something the ecosystem abandoned. Recorded, not catalogued.

## The methodology result: an entry's verdict is version-indexed

H3 was disqualified because cryptography **warns**. That is true of 50.0.1. It is not true
of the version that was already installed on this machine:

| | 41.0.7 (Debian's) | 50.0.1 (current) |
| --- | --- | --- |
| `not_valid_after` emits a warning | **no** | yes |
| `not_valid_after_utc` exists | **no** | yes |

**On 41.0.7 this is a FINDING. On 50.0.1 it is LOUD.** Same check, same code, opposite
verdicts — and the version where it is a finding is the one Debian ships and the one that
was sitting in this container.

This is the first hard data on a question [PLAN.md](PLAN.md) raised and could not answer:

> *entries invalidated by a new library version — this is the subscription logic. If entries
> never go stale, there is no recurring product.*

They go stale. In both directions. A catalogue entry is a claim about a **version**, not
about a library, and the pinned-version policy that was adopted on principle turns out to
be load-bearing. It also means the answer a user needs depends on what they have installed,
not on what is current — which is an argument for running the checks against their
environment rather than handing them a document.

## Outcome

**CLEAN.** No catalogue entry, no check. Audit 13, protocol rank 10.

The register's running rate is now **7 eligible audited, 6 findings.** This is the decline
that was predicted in writing before audit 7, arriving on schedule at the most carefully
maintained library on the list.
