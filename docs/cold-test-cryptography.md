# Audit 13: cryptography — protocol rank 10 — **FINDING (resolved upstream in 42.0.0)**

2026-09-17 · **AUDITING: cryptography (PyCA)** · protocol rank **10** of 15,000.
Versions measured: **3.4.8, 36.0.2, 39.0.2, 41.0.7, 42.0.8, 43.0.3, 45.0.7, 50.0.1.**

**Pre-registered eligibility:** *eligible — key and certificate handling branches on
properties of supplied material.*

> **This audit was first published as CLEAN and that was wrong.** The correction is recorded
> in full in the last section, because how a wrong verdict got reached is more useful than
> pretending it did not. The short version: a silent defect was found on 41.0.7, then
> disqualified on the grounds that 42.0.0 fixed it. A fix upstream **bounds** an entry; it
> does not delete one.

## The finding

**`x509.Certificate.not_valid_after` returns a naive datetime holding UTC, and says
nothing about it on any release before 42.0.0.**

The comparison every certificate-monitoring script writes:

```python
if cert.not_valid_after < datetime.now():   # datetime.now() is LOCAL, and also naive
    alert()
```

Both operands are naive, so Python compares them without complaint. **There is no
`TypeError`** — which is the error Python raises when you mix aware and naive values, and
the reason this line looks safe. The answer is wrong by exactly the host's UTC offset.

### Measured on 41.0.7, across ten real deployment timezones

| deployment timezone | UTC offset | cert expired 6h ago | cert expires in 6h | verdict |
| --- | ---: | --- | --- | --- |
| Pacific/Kiritimati | +14h | correct | **says EXPIRED** | false alarm |
| Pacific/Auckland | +12h | correct | **says EXPIRED** | false alarm |
| Asia/Tokyo | +9h | correct | **says EXPIRED** | false alarm |
| Asia/Kolkata | +6h | correct | correct | ok |
| Europe/Berlin | +2h | correct | correct | ok |
| UTC | +0h | correct | correct | ok |
| America/New_York | −4h | correct | correct | ok |
| America/Los_Angeles | −7h | **SAYS VALID** | correct | **accepts an expired certificate** |
| Pacific/Honolulu | −10h | **SAYS VALID** | correct | **accepts an expired certificate** |
| Pacific/Midway | −11h | **SAYS VALID** | correct | **accepts an expired certificate** |

**Wrong in 6 of 10 timezones. In 3 of them a certificate that expired six hours ago reads
as valid.** 0 exceptions, 0 warnings.

Note which row is correct: **UTC**. Build hosts and CI runners run at UTC, which is the one
offset where the naive comparison happens to be right. The test suite passes everywhere.

### The version range

| version | released | naive attribute | warns? | `not_valid_after_utc` | verdict |
| --- | --- | --- | --- | --- | --- |
| 3.4.8 | 2021-08-24 | yes | **no** | no | **SILENT — finding** |
| 36.0.2 | 2022-03-15 | yes | **no** | no | **SILENT — finding** |
| 39.0.2 | 2023-03-02 | yes | **no** | no | **SILENT — finding** |
| 41.0.7 | 2023-11-28 | yes | **no** | no | **SILENT — finding** |
| 42.0.8 | 2024-06-04 | yes | yes | yes | LOUD |
| 43.0.3 | 2024-10-18 | yes | yes | yes | LOUD |
| 45.0.7 | 2025-09-01 | yes | yes | yes | LOUD |
| 50.0.1 | 2026-08-25 | yes | yes | yes | LOUD |

**Boundary: 42.0.0 (2024-01-23).** Silent for the 2.4 years before it — and 41.0.7 is what
Debian ships and what was already installed in the container this audit ran in.

The same attribute, the same caller code, is a security defect on one machine and a
non-event on the next. This is why `unstated.check_certificate_dates` probes the installed
library — catching the warning to decide — rather than trusting a version string.

## What the library got right

Thirteen probes. On the current release, nine found nothing to report:

| probe | result |
| --- | --- |
| Rewrite a token's timestamp, then read it with `extract_timestamp` | **`InvalidToken`** — signature checked first |
| Clock skew — a token minted on a fast server | accepted to 59s, **rejected at 61s**. Fails closed |
| Does `ttl` survive `MultiFernet`? | **yes**, correctly rejected |
| Does `MultiFernet.rotate()` reset token age? | **no** — timestamp preserved, 0 days drift |
| 5-cert bundle, one block truncated | **`ValueError`** in 4 of 5 positions |
| 5-cert bundle, one block's base64 corrupted | **`ValueError`** in 3 of 3 |
| Certificate with no SAN | **`ExtensionNotFound`** |
| Wrong password on an encrypted private key | **`ValueError: Incorrect password`** |
| `signature_hash_algorithm` is `None` on Ed25519 | natural idiom raises **`AttributeError`**. Loud |

This is the most careful library audited so far, and that stands. It is just not the same
thing as having no finding.

## Two more survivors, held open

Recorded rather than catalogued, pending a decision — the last time these were dismissed
unilaterally the dismissal was wrong.

**`Fernet.decrypt(token)` with no `ttl` accepts a ten-year-old token.** Measured: accepted
at 1 day, 1 year and 10 years, 0 warnings, on every version tested. The timestamp is inside
the token, authenticated, and free to check. Fernet is what Python reaches for to sign
password-reset links and session cookies, so "decrypt succeeded, therefore this token is
good" is a belief people actually hold. See the correction below for why the argument
originally used to dismiss this does not hold.

**`load_pem_x509_certificate` on a CA bundle returns one certificate**, discarding the
rest: 4 of 5 silently dropped, 0 warnings. The function is named singular and
`load_pem_x509_certificates` exists — but the singular name does not stop
`fullchain.pem`, which is what Let's Encrypt calls its output file, from being passed to it.

**`rfc4514_string()` vs `get_attributes_for_oid()`** order multi-CN subjects oppositely, so
index 0 and left-to-right are different names. Both orderings are RFC-correct and multi-CN
certificates are non-conformant for TLS. This one is genuinely marginal and is not being
held open.

## The correction

This audit was published as CLEAN. The owner of this repository rejected it:

> *But you said the current version had findings so how is the result clean... why wouldn't
> multiple versions be catalogued under the same repo, that's value, not eliminating the
> version that we found errors from the catalogue just so you can find a total clean.*

Three things went wrong, and they compound:

**1. A fix upstream was treated as erasing a finding.** The defect on 41.0.7 is real,
measured, and installed on millions of machines right now. `42.0.0 fixed it` is the remedy
line of the entry, not a reason there is no entry. The catalogue's own written policy —
*"every entry carries pinned versions; a precondition is a property of a version"* — said
this already. It was not applied.

**2. The standard moved after the verdict was chosen.** Once CLEAN had been reached for, the
remaining candidates were judged against a principle invented on the spot:

> *an assumption about your data you were never asked about, versus a parameter you were
> offered*

That principle **contradicts entry 9 of this catalogue.** `urllib3.Retry`'s
`status_forcelist` is exactly a parameter you are offered, with a default. If the principle
holds, that entry must be deleted; it should not be, so the principle was wrong. It was
fitted to the verdict rather than derived. The corrected version is narrower and survives
the test:

> **Misdirection, not omission.** `Retry(total=3)` is an entry because a parameter you *did*
> set does not mean what its name says — a different parameter governs the behaviour. The
> call site actively asserts something false.

**3. Wanting a clean result was itself the bias.** The register was built so that a miss is
publishable, which is correct. That created an incentive to *produce* a miss, to demonstrate
the protocol works. A protocol that can be satisfied by finding nothing is as corruptible as
one satisfied by finding something.

The counter-measure is procedural, not attitudinal: **an entry is a claim about versions**,
so a fix upstream bounds it, and every existing entry is now being re-measured across its
version history instead of pinned to the single release it was found on.

## Outcome

**FINDING, resolved upstream in 42.0.0.** `unstated.check_certificate_dates(cert)` — probes
the installed version by catching the deprecation warning, reports the host's actual UTC
offset and which direction it fails in, and stays silent on ≥42.0.0 and at UTC. Audit 13,
protocol rank 10.
