# Audit 7: boto3 — first under the selection protocol

2026-09-17 · **AUDITING: boto3 1.43.96** · protocol rank **1** of 15,000, 3,206,668,324
downloads ([hugovk/top-pypi-packages](https://github.com/hugovk/top-pypi-packages),
dump dated 2026-09-01).

**Pre-registered eligibility**, recorded in `TARGETS.md` before this run: *eligible —
pagination and retry behaviour depend on properties of the caller's request and response
data.* Outcome was not known when that was written.

Run against moto 5.2.3's AWS mock, so what is measured is boto3's own behaviour rather
than a network artefact.

## Assumption

The caller's result set fits in one page.

## S3 — measured

2,500 objects in a bucket, then the call a first draft actually writes:

| | |
| --- | --- |
| objects in the bucket | 2,500 |
| returned by `list_objects_v2(Bucket=...)` | **1,000 (40%)** |
| returned via `get_paginator` | 2,500 (100%) |
| **silently missing** | **1,500** |
| exceptions raised | **0** |
| warnings emitted | **0** |
| signal | `IsTruncated: True`, in the response body |

The response is a valid dict, `Contents` is a list of well-formed objects, the status is
200. A count of 1,000 looks like a number, not like a ceiling.

## DynamoDB — the same class with no learnable ceiling

S3 stops at 1,000, a round number someone might eventually recognise. `scan` stops at
**1 MB**, so its cutoff moves with row width. Same table, same 400 rows, only the item size
changed:

| item size | rows in table | `scan()` returned | % of truth |
| --- | --- | --- | --- |
| 200 B | 400 | 400 | 100% |
| 2,000 B | 400 | 400 | 100% |
| 20,000 B | 400 | **49** | **12%** |

The same code against the same table returns a different fraction after someone adds a
column. And 49 is not a number anyone would recognise as a limit.

## Upstream status

**Documented.** `IsTruncated` and `LastEvaluatedKey` are in the response shape, and
`get_paginator` is the documented answer. What is absent is any signal *at the call site*
that the default is a first page. As with dateutil, the gap is not that the knowledge is
missing — it is that nothing puts it in front of the person writing the line.

## Check

`unstated.check_paginated(response, operation=...)` — takes any AWS response and reports
whether it is one page of a larger set. Generalised across the markers AWS actually uses,
because there is no single field: `IsTruncated`, `NextToken`, `NextMarker`,
`NextContinuationToken`, `LastEvaluatedKey`, `Marker`, `NextPageToken`.

A check that knew only `IsTruncated` would pass DynamoDB, which is the service whose
truncation is hardest to notice.

## Outcome

**FINDING.** Recorded in `TARGETS.md` as audit 7, protocol rank 1.
