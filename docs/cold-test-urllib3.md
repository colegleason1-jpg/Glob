# Audit 10: urllib3 — protocol rank 6

2026-09-17 · **AUDITING: urllib3 2.6.3** · protocol rank **6** of 15,000, 1,793,872,890
downloads.

**Pre-registered eligibility:** *eligible — `Retry` behaviour depends on whether the
caller's request is idempotent, which the caller supplies implicitly.*

Measured against a local HTTP server returning 503 to everything, counting the requests
that actually arrive. What is recorded is what went on the wire.

## Assumption

The caller wants connection-level retries only, spaced by nothing, on methods the library
judged idempotent.

## Measured

| client configuration | requests | elapsed | outcome |
| --- | --- | --- | --- |
| `Retry(total=3)` — what a first draft writes | **1** | 0.00s | returned 503 to the caller |
| `Retry(total=3)` on a POST | 1 | 0.00s | returned 503 to the caller |
| `Retry(total=3, status_forcelist=[503])` | 4 | **0.00s** | raised MaxRetryError |
| …`+ backoff_factor=0.5` | 4 | 3.00s | raised MaxRetryError |

**`Retry(total=3)` against a 503 sends one request.** No retry at all. `status_forcelist`
is empty by default, so HTTP error statuses are not retried — only connection and read
errors are.

Three mechanisms, isolated separately so they are not conflated:

```
GET,  status_forcelist=[503]                       -> 4 requests
POST, status_forcelist=[503]                       -> 1 request    (allowed_methods excludes POST)
POST, status_forcelist=[503], allowed_methods=None -> 4 requests   (non-idempotent, replayed)
```

Defaults: `status_forcelist=set()`, `backoff_factor=0`, `allowed_methods` excludes POST.

## Impact

**Believed:** *I configured retries, so transient failures are handled.*

**Actual:** *I configured retries for connection and read errors.* Against a 503,
`Retry(total=3)` sent one request and returned the error.

**Breaks three different things — and fixing the first tends to cause the others:**

* A service that reports it has retries surfaces every upstream 503 as a hard failure, so
  an operator tunes timeouts and capacity against a resilience layer that was never
  engaged.
* Once statuses are retried with no backoff, a struggling dependency receives four times
  the traffic in the instant it is least able to serve it. **The retry layer amplifies the
  outage it was added to survive.**
* Once methods are opened up so a POST will retry, a non-idempotent request is replayed:
  an order placed four times, a stock movement recorded four times, a payment instruction
  submitted four times. The server saw four valid requests and has no way to know three
  were the same intent.

**Detection: poor for the first, inverted for the third.** A retry that never happened
looks exactly like one that did not help, so missing retries surface as an error rate
nobody attributes to configuration. The duplicate-POST case is worse — **nothing fails at
all.** Every request returned 2xx, the client is satisfied, and the duplicates are found
later by whoever reconciles the records.

## Upstream status

**Documented**, and each default is defensible in isolation: not retrying statuses avoids
surprising the caller, zero backoff is the conservative starting point, excluding POST is
correct. What no default can do is tell the call site that `Retry(total=3)` and "retry on
failure" are different things.

## Outcome

**FINDING.** `unstated.check_retry(retry)` — flags all three gaps and stays silent on a
configuration that names its statuses, spaces its attempts, and leaves the method set
alone. Audit 10, protocol rank 6.
