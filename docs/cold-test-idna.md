# Audit 9: idna — protocol rank 5

2026-09-17 · **AUDITING: idna 3.11** against CPython's built-in `"idna"` codec · protocol
rank **5** of 15,000, 1,801,007,240 downloads.

**Pre-registered eligibility:** *eligible — encoding decisions branch on properties of the
domain string supplied.*

## Assumption

Encoding a domain name is deterministic: one input, one host.

## What is actually installed

The `idna` package implements **IDNA 2008**. Python's built-in `str.encode("idna")`
implements **IDNA 2003**. Both are reachable from the same interpreter, and the two
standards deliberately differ on several characters.

## Measured

12 internationalised domains, chosen to span both the characters the standards changed and
the ones they did not:

> **Correction, 2026-09-17.** This section previously said "13 internationalised domains"
> and reported **8 of 13 (62%)** disagreeing, of which **4** produce two registrable names.
> Those numbers are wrong and were internally inconsistent — 4 + 2 does not reach 8. The
> table has always held **12** domains (one row carries two), and re-measurement gives
> **7 of 12 (58%)**, of which **5** produce two registrable names and **2** are refusals:
> 5 + 2 = 7. The error was found by the adversarial verifier in the version-range sweep,
> re-measured directly before being applied, and the original figures are kept here rather
> than replaced. The version range below was established by the same sweep.

| input | idna 3.11 (2008) | `.encode("idna")` (2003) | same? |
| --- | --- | --- | --- |
| `straße.de` | `xn--strae-oqa.de` | `strasse.de` | **NO** |
| `faß.de` | `xn--fa-hia.de` | `fass.de` | **NO** |
| `groß.example` | `xn--gro-7ka.example` | `gross.example` | **NO** |
| `weiß.example` | `xn--wei-7ka.example` | `weiss.example` | **NO** |
| `ς.example` | `xn--3xa.example` | `xn--4xa.example` | **NO** |
| `ﬁ.example` | *InvalidCodepoint* | `fi.example` | **NO** |
| `İ.example` | *InvalidCodepoint* | `xn--i-9bb.example` | **NO** |
| `bücher.de` | `xn--bcher-kva.de` | `xn--bcher-kva.de` | yes |
| `café.fr` | `xn--caf-dma.fr` | `xn--caf-dma.fr` | yes |
| `日本.jp` | `xn--wgv71a.jp` | `xn--wgv71a.jp` | yes |
| `ñandú.ar`, `zürich.ch` | identical | identical | yes |

| | |
| --- | --- |
| domains disagreeing | **7 of 12 (58%)** |
| …producing two valid, separately registrable names | **5** |
| …where one encoder accepts and the other refuses | 2 |
| exceptions on the disagreeing paths | **0** |
| warnings | **0** |

**`uts46=True` does not reconcile them.** The documented compatibility mode still returns
the IDNA 2008 result: `idna.encode("straße.de", uts46=True)` is `xn--strae-oqa.de`.

## Version range

Measured **exhaustively, not sampled**: every one of the 34 releases that installs on
CPython 3.11, from **0.6 (2014-04-29)** through **3.20 (2026-09-17, current latest)** —
**12.4 years**, all 12 per-domain outputs byte-for-byte identical at every version. No
release fixes it, warns about it, or narrows it.

Eight releases (0.2–0.5, 0.7–1.0) will not install on a modern interpreter, so 0.6 is an
install island rather than a contiguous floor. The `uts46=True` result holds from 2.0
onward; the kwarg does not exist at 0.6 or 1.1, where it raises `TypeError`.

**Not resolved — upstream treats the divergence as by design.**

## Impact

**Believed:** *I am talking to the domain the user gave me.*

**Actual:** *I am talking to one of two different domains, decided by which code path
encoded it.* `xn--strae-oqa.de` and `strasse.de` are not the same place, and both can be
registered.

**Breaks** anything that encodes a name in one place and uses it in another:

* an allowlist or blocklist checked with one encoder and dereferenced with the other
  compares two different hosts, so a name can be absent from the list that was checked and
  present in the request that was sent
* a log or audit trail records a host that was not the one contacted
* deduplication counts one domain as two, or two as one
* certificate matching, mail routing and cache keys inherit the same split
* the ligature and dotted-capital cases go further — one encoder refuses the name outright
  while the other resolves it, so a validation step and a fetch step disagree about
  whether the input is a domain at all

**Detection: very poor, and the usual test data hides it.** Umlauts, accents and CJK
encode identically under both standards. A suite exercising `bücher.de`, `café.fr` or a
Japanese name passes cleanly. Only the handful of changed characters expose it, and both
outputs are well-formed names that resolve.

## Upstream status

**By design.** The standards differ deliberately, and both implementations document which
one they follow. What neither says is that the other is also installed and one import away.

## Scope note

This records that two encoders disagree and that both outputs are registrable. It does
**not** demonstrate an exploit against any particular system — that would need a specific
allowlist implementation and a registered domain, neither of which was tested here.

## Outcome

**FINDING.** `unstated.check_domain_encoding(domains)`. Audit 9, protocol rank 5.
