# Target selection protocol and register

2026-09-17 · **written before audit 7, and not edited afterwards except to record outcomes.**

## Why this exists

The first six targets were chosen by intuition, by someone with reason to suspect each of
them. Six findings from six targets is therefore a selection artefact, not a hit rate, and
any competent reviewer will say so. This protocol exists so that from audit 7 onward the
rate means something — which requires that a **miss is as publishable as a hit**.

## Ordering

Packages are worked in descending PyPI download order. Source:
[hugovk/top-pypi-packages](https://github.com/hugovk/top-pypi-packages), the monthly dump
of the 15,000 most-downloaded packages, as reported 2026-03-01.

**Resolved 2026-09-17.** The first fetch attempt was blocked (`hugovk.github.io`, egress
policy). The raw GitHub path works, and the live ranking was retrieved: 15,000 packages,
dump dated 2026-09-01, source ClickHouse. The ordering below is therefore real, not
approximate. True top 20, for the record:

boto3, packaging, typing-extensions, certifi, idna, urllib3, requests, charset-normalizer,
setuptools, cryptography, cffi, pluggy, pygments, pyyaml, botocore, python-dateutil, six,
pydantic, numpy, click.

Note that python-dateutil (audit 4) is rank 16, so one pre-protocol audit did land on a
genuine top-20 package.

## Eligibility filter — applied and recorded BEFORE the audit

A package is **eligible** when it exposes a callable that:

1. takes caller-supplied data or configuration, **and**
2. returns a value the caller acts on — not only transport or plumbing, **and**
3. has at least one branch whose behaviour depends on a property of that data.

A package is **ineligible** when it has no runtime data surface (a certificate bundle,
build metadata), is pure transport with no interpretation, or is a compatibility shim.

Ineligible packages are **recorded, never silently skipped.** Eligibility is decided from
the package's API before any measurement, so it cannot be used to retro-fit a good rate.

## Outcomes

| outcome | meaning |
| --- | --- |
| **FINDING** | assumption confirmed, cost measured, failure silent, check written |
| **CLEAN** | eligible, audited, nothing found. Published the same as a finding. |
| **LOUD** | the component raises or warns when the assumption breaks — correct behaviour, no entry |
| **INELIGIBLE** | no applicable surface, with the reason recorded |

## Register

Audits 1–6 are recorded for completeness and are explicitly **outside** the protocol.

| # | package | selected by | eligible | outcome | evidence |
| --- | --- | --- | --- | --- | --- |
| 1 | imbalanced-learn (SMOTE) | intuition — pre-protocol | yes | FINDING | `cold-test-smote.md` |
| 2 | optuna (TPESampler) | intuition — pre-protocol | yes | CLEAN — sound, 43/45 | `cold-test-optuna.md` |
| 3 | optuna (MedianPruner) | intuition — pre-protocol | yes | FINDING | `cold-test-optuna.md` |
| 4 | python-dateutil | intuition — pre-protocol | yes | FINDING | `cold-test-dateutil.md` |
| 5 | pandas (merge) | intuition — pre-protocol | yes | FINDING | `cold-test-pandas.md` |
| 6 | scikit-learn (train_test_split) | intuition — pre-protocol | yes | FINDING | `cold-test-sklearn.md` |
| 7 | **boto3** | **protocol, rank 1** | yes (pre-registered) | **FINDING** | `cold-test-boto3.md` |
| 8 | **packaging** | **protocol, rank 2** | yes (pre-registered) | **FINDING** | `cold-test-packaging.md` |
| 9 | **idna** | **protocol, rank 5** | yes (pre-registered) | **FINDING** | `cold-test-idna.md` |
| 10 | **urllib3** | **protocol, rank 6** | yes (pre-registered) | **FINDING** | `cold-test-urllib3.md` |
| 11 | **requests** | **protocol, rank 7** | yes (pre-registered) | **FINDING** | `cold-test-requests.md` |
| 12 | **charset-normalizer** | **protocol, rank 8** | yes (pre-registered) | **FINDING** | `cold-test-charset-normalizer.md` |
| 13 | **cryptography** | **protocol, rank 10** | yes (pre-registered) | **CLEAN — 13 probes, 9 correct or loud** | `cold-test-cryptography.md` |
| 14 | pluggy | protocol, rank 12 | yes (pre-registered) | tbd | — |

Note that audit 2 is already a clean pass. It was published as one, and that is the
precedent this register formalises.

## Pre-registered eligibility for the first protocol ranks

Recorded now, before any of them is audited.

| rank | package | eligible | reasoning |
| --- | --- | --- | --- |
| 1 | boto3 | **yes** | pagination and retry behaviour depend on properties of the caller's request and response data — **audited, FINDING** |
| 2 | packaging | **yes** | version comparison and specifier matching branch on the shape of the version string supplied — **audited, FINDING** |
| 3 | typing-extensions | **no** | type constructs resolved at definition time; nothing is computed from caller data |
| 4 | certifi | **no** | a certificate bundle; nothing is computed from caller data |
| 5 | idna | **yes** | encoding decisions branch on properties of the domain string supplied — **audited, FINDING** |
| 6 | urllib3 | **yes** | `Retry` behaviour depends on whether the caller's request is idempotent, which the caller supplies implicitly — **audited, FINDING** |
| 7 | requests | **yes** | encoding detection, redirect and session behaviour branch on response properties — **audited, FINDING** |
| 8 | charset-normalizer | **yes** | its entire job is inferring an assumption about caller-supplied bytes — **audited, FINDING** |
| 9 | setuptools | **no** | build-time metadata; no runtime data surface |
| 10 | cryptography | **yes** | key and certificate handling branches on properties of supplied material — **audited, CLEAN** |

Running rate under the protocol: **7 eligible audited, 6 FINDINGS, 1 CLEAN.** Ranks 3
and 4 (typing-extensions, certifi) were pre-registered ineligible and are skipped on the
record, not silently.

**The predicted decline arrived at audit 13.** cryptography (PyCA) came back CLEAN after
thirteen probes, nine of which found the library raising, warning or simply behaving
correctly. It was written down before audit 7 that the rate would fall and that the fall
would be published rather than smoothed; this is that, and it arrived at the most carefully
maintained library on the list, which is where it should.

The CLEAN also did more work than a finding would have. It forced the catalogue's boundary
to be stated:

> An entry is an assumption a library makes **about your data**, that you were never asked
> about. `Fernet(ttl=None)` is a question you **were** asked, at the call site, by name, and
> answered by omission. That is not an entry, however sharp the consequence.

Applying that line instead of stretching for an eleventh entry is what the register is for.

**Hypotheses are now registered per audit, not just eligibility.** Audit 12 wrote down four
before measuring and **two did not reproduce** (input length, chunked sampling). Both are
published in `cold-test-charset-normalizer.md`. A protocol that only publishes the
hypotheses that worked is not a protocol, and the finding rate above is a rate over
*packages*, not over guesses — the guess-level rate is visibly worse, which is the honest
picture.

**Ranks 11–15, pre-registered now, before any of them is looked at** — so the filter
cannot be fitted to the results later:

| rank | package | eligible | reasoning |
| --- | --- | --- | --- |
| 11 | cffi | **no** | a foreign-function build and binding layer; behaviour is decided by the C declarations, not by runtime caller data |
| 12 | pluggy | **yes** | hook call order and the first-result rule depend on properties of the plugins registered by the caller — **next** |
| 13 | pygments | **yes** | lexer selection is inferred from filename and content, which is an assumption about caller-supplied data |
| 14 | pyyaml | **yes** | scalar resolution branches on the shape of the supplied string — the Norway problem is the canonical instance |
| 15 | botocore | **defer** | boto3 (rank 1) is a thin layer over it and was audited at rank 1; auditing it separately would double-count one codebase unless a surface outside boto3's is chosen |

**Note on rank 8, written before the audit and kept.** charset-normalizer is the
detector that was measured at 12/12 in audit 11 — it produced the correct answer on every
body requests got wrong. Auditing it next is uncomfortable in a useful way: the protocol
requires the target be audited on its own terms whatever audit 11 said about it, and a
CLEAN outcome there would be the more interesting result.

**Resolved: FINDING, and both audits are consistent.** Audit 11's corpus was UTF-8, where
detection is structurally verifiable and scored 20/20 on a wider corpus here. Audit 12's
finding is about the legacy single-byte encodings, where a successful decode is evidence of
nothing and the round-trip rate is 12/20 — reported at confidence 1.000 either way. The
12/12 in audit 11 stands; it measured the case that can be verified.

## Standing rules

* The hit rate is reported over **eligible** packages only, and the eligible/ineligible
  split is published alongside it.
* The expectation is that the rate **falls** as obvious targets are exhausted. That decline
  is published, not smoothed.
* No target is skipped because a preliminary look suggests it is clean. Once eligible, it
  is audited and the outcome recorded whatever it is.
