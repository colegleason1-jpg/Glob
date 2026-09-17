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
| 9 | idna | protocol, rank 5 | yes (pre-registered) | tbd | — |

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
| 5 | idna | **yes** | encoding decisions branch on properties of the domain string supplied |
| 6 | urllib3 | **yes** | `Retry` behaviour depends on whether the caller's request is idempotent, which the caller supplies implicitly |
| 7 | requests | **yes** | encoding detection, redirect and session behaviour branch on response properties |
| 8 | charset-normalizer | **yes** | its entire job is inferring an assumption about caller-supplied bytes |
| 9 | setuptools | **no** | build-time metadata; no runtime data surface |
| 10 | cryptography | **yes** | key and certificate handling branches on properties of supplied material |

Running rate under the protocol: **2 eligible audited, 2 FINDINGS.** Two data points are
not a rate either. Ranks 3 and 4 (typing-extensions, certifi) were pre-registered
ineligible and are skipped on the record, not silently.

## Standing rules

* The hit rate is reported over **eligible** packages only, and the eligible/ineligible
  split is published alongside it.
* The expectation is that the rate **falls** as obvious targets are exhausted. That decline
  is published, not smoothed.
* No target is skipped because a preliminary look suggests it is clean. Once eligible, it
  is audited and the outcome recorded whatever it is.
