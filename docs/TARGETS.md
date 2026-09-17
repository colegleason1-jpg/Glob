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
| **FINDING** | assumption confirmed, cost measured, failure silent **at one or more measured versions**, check written. The entry carries the affected range. |
| **RESOLVED** | a FINDING that upstream has since fixed, at a known version. **Still an entry.** The affected range is still installed, and the entry now ships with the remedy attached. |
| **CLEAN** | eligible, audited, nothing found **at any measured version**. Published the same as a finding. |
| **LOUD** | the component raises or warns **at every measured version** — correct behaviour, no entry |
| **INELIGIBLE** | no applicable surface, with the reason recorded |

**A verdict is only as wide as the versions measured.** An audit that tests one version
yields a claim about one version, and must say so. This rule was added after audit 13,
which got it wrong — see below.

### The correction that produced this rule

Audit 13 was first recorded as CLEAN. It was not. The audit found
`Certificate.not_valid_after` returning a **silent naive datetime** on cryptography 41.0.7,
then disqualified it because **42.0.0 emits a deprecation warning** — reasoning that a
newer release being fixed made the finding not count.

That is backwards, and it was caught by the repository's owner rather than by the protocol:

> *why wouldn't multiple versions be catalogued under the same repo, that's value, not
> eliminating the version that we found errors from the catalogue just so you can find a
> total clean.*

Correct. The behaviour was then ranged properly across eight releases: **silent in every
version from 3.4.8 (2021-08) through 41.0.7 (2023-11), warning from 42.0.0 (2024-01)** —
a 2.4-year span that Debian stable still ships. Someone on that range has the defect today;
"42 fixed it" is the answer they need, not grounds for deleting the entry.

Two things changed as a result:

1. `CatalogueEntry` carries `affected_versions` and `resolved_in` as fields. A fix upstream
   **bounds** an entry, it does not delete one.
2. Every existing entry is being re-measured across versions rather than pinned to the one
   release it was found on. A single-version entry is an under-specified claim.

The failure mode worth naming: once **CLEAN** had been reached for, the remaining candidates
got judged against a standard invented to justify it. Three survivors were disqualified on a
principle — *"an assumption about your data you were never asked about, versus a parameter
you were offered"* — that **contradicts entry 9**, `urllib3.Retry`, where `status_forcelist`
is exactly a parameter you are offered with a default. The principle was fitted to the
verdict. The corrected distinction is narrower and survives the contradiction:

> **Misdirection, not omission.** `Retry(total=3)` is an entry because a parameter you *did*
> set does not mean what its name says — a different parameter governs the behaviour. That
> is the call site actively asserting something false.

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
| 13 | **cryptography** | **protocol, rank 10** | yes (pre-registered) | **FINDING (RESOLVED in 42.0.0)** — first recorded CLEAN in error, corrected | `cold-test-cryptography.md` |
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
| 10 | cryptography | **yes** | key and certificate handling branches on properties of supplied material — **audited, FINDING (resolved upstream in 42.0.0)** |

Running rate under the protocol: **7 eligible audited, 7 FINDINGS** — one of which
(cryptography) is **RESOLVED upstream in 42.0.0** and is catalogued with that boundary
rather than dropped. Ranks 3 and 4 (typing-extensions, certifi) were pre-registered
ineligible and are skipped on the record, not silently.

**The predicted decline has NOT yet arrived.** It was briefly recorded as having arrived at
audit 13, and that was an error of judgement rather than of measurement — see *The
correction that produced this rule* above. The honest position is that 7 of 7 eligible
packages have yielded a finding, which is still an uncomfortably high rate for a protocol
whose stated expectation is that it falls. It has not fallen yet. That is what the register
says, and it is not smoothed in either direction.

What audit 13 *did* legitimately establish is that cryptography is the most carefully
maintained library audited: thirteen probes, and on the current release nine of them found
the library raising, warning, or simply behaving correctly. That belongs in the record too,
and it is in `cold-test-cryptography.md`.

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
