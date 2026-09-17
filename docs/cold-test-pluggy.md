# Audit 14: pluggy — protocol rank 12

2026-09-17 · **AUDITING: pluggy** · protocol rank **12** of 15,000.

> **This audit was refuted on its first pass and rewritten.** The original claimed pluggy
> *discards* the losing answers (it never computes them), described the ordering rule as
> LIFO (it is not), asserted that no API exposes the contention (three do), gave the wrong
> release date for 0.6.0, and shipped a check that fired at high severity on a stock pytest
> install. All of it is recorded in `staging/audit-014-pluggy.json` under `verifier` and
> `owner_review`, with each defect re-measured directly before being accepted. The wrong
> version stays on the record.

**Pre-registered eligibility:** *eligible — hook call order and the firstresult rule depend
on properties of the plugins the caller registers.* Registered in
`unstated/protocol/targets.py` with the other 99 top-100 targets before any audit past rank 10.

## Hypotheses, registered before measuring

| | hypothesis | outcome |
| --- | --- | --- |
| H1 | `firstresult=True` silently discards every answer but one | **reproduced, but the mechanism is different** — the losers are never *called*; nothing is discarded |
| H2 | call order is LIFO, so precedence follows import order | **refuted as stated** — LIFO holds only within a bucket, and `trylast` is FIFO |
| H3 | `tryfirst` is not a total order; ties fall back to registration order | **reproduced** |
| H4 | an exception in one hookimpl aborts the call | **LOUD** — it raises. Correct behaviour, no entry. |

## Assumption

The caller knows which registered plugin answers a first-result hook, and that the others
were considered.

## Measured

Two plugins, both able to answer the same `firstresult=True` hook, instrumented to record
entry:

```
registered catalogue, promotion -> value=80    implementations that actually ran: ['promotion']
registered promotion, catalogue -> value=100   implementations that actually ran: ['catalogue']
```

**Only one implementation ever runs.** `_callers.py:_multicall` breaks at the first
non-`None`. The loser's function body never executes, so its answer is never computed —
**and its side effects never happen.** That is a stronger fact than "discarded", and the
original write-up had it wrong.

### The ordering rule is buckets, not LIFO

```
all plain     A,B,C -> C,B,A      (looks LIFO)
all tryfirst  A,B,C -> C,B,A      (looks LIFO)
all trylast   A,B,C -> A,B,C      (FIFO — the opposite)
```

pluggy's own comment in `_hooks.py:HookCaller.__init__` states it: implementations are
filed into six buckets — trylast non-wrappers, non-wrappers, tryfirst non-wrappers, then
the same three for wrappers — and the list is **iterated in reverse**. Registration order
breaks ties **within a bucket only**.

`tryfirst` does not settle it either. Two implementations both marked `tryfirst`, **2 of 2
orderings produced a different winner**: A-then-B → `'B'`, B-then-A → `'A'`.

### Registration order is not import order

In pytest — the ecosystem this entry cites — it is a hardcoded builtin tuple
(`essential_plugins`, then `default_plugins`), then `PYTEST_PLUGINS`, then `-p` arguments,
then entry points, then conftest discovery.

### The contention *can* be investigated — three ways

The original claimed no API exposed it. Measured, all three work:

| | |
| --- | --- |
| `get_hookimpls()` + `spec.opts['firstresult']` | identifies a contested hook — this is how the check works |
| `add_hookcall_monitoring(before, after)` | passes the **full implementation list** to *both* callbacks |
| `subset_hook_caller(name, remove_plugins=[winner])` | returns **100** — the loser's answer, exactly |

What survives is narrower and still true: **the returned value carries no provenance, and
nothing warns at the point it is used.**

### Contested hooks are normal

On **stock pytest 9.1.1 with no third-party plugins**, 9 of the 17 first-result hookspecs
already have more than one answering implementation. Abstaining by returning `None` is the
designed idiom and it works — across 56 first-result calls in a real pytest run, no call
produced more than one answer. A contested hook is not a pathology.

| pytest | hookspecs | `firstresult` |
| --- | --- | --- |
| 7.4.4 | 52 | 16 (30.8%) |
| 8.3.5 | 52 | 17 (32.7%) |
| 9.1.1 | 52 | **17 (32.7%)** |

### One unrelated plugin changes who decides

The original asserted this and never measured it. Measured now, by registering and
unregistering `pytest-subtests` — a plugin about subtests:

| hook | without subtests | with subtests | decider changed? |
| --- | --- | --- | --- |
| `pytest_report_teststatus` | skipping, runner, terminal | **subtests**, skipping, runner, terminal | **yes** |
| `pytest_report_to_serializable` | reports | **subtests**, reports | **yes** |
| `pytest_report_from_serializable` | reports | **subtests**, reports | **yes** |

**3 of 3.** pytest's own `pytest_report_teststatus` no longer runs first. 0 warnings.

*(First measured wrongly: `pytest-timeout`, `pytest-xdist` and `pytest-cov` appeared to
change nothing, but xdist and cov never loaded under `get_config([])`. That was a broken
probe reading as a negative, and is recorded rather than dropped.)*

### `None` abstains; every other falsy value answers

The test is `if res is not None` — identity, not truthiness.

| values offered | returned | implementations run |
| --- | --- | --- |
| `[None, 100]` | `100` | 1 of 2 |
| `[None, 0]` | `0` | 1 of 2 |
| `[None, False]` | `False` | 1 of 2 |
| `[None, '']` | `''` | 1 of 2 |
| `[None, None]` | `None` | 2 of 2 |

So a plugin that legitimately computes `None` as its answer silently abstains instead.

## Version range

**Exhaustive over the span: all 17 releases** from **0.6.0 (2017-11-24)** through **1.6.0
(2025-05-15, current latest)** — **7.5 years**. Every one: order-dependent, 0 warnings,
`tryfirst` tie unbroken, `trylast` FIFO, `None` falls through, `0` wins.

**0.6.0 is the earliest measured, not the onset.** 0.3.0 (2015-05-07) and 0.4.0 reproduce
identically; 0.5.0–0.5.2 cannot run on Python 3.11 (`inspect.getargspec` removed) and are
untestable here, not unaffected.

*(The original gave 0.6.0 as 2018-04-15 — a later **file** on the same release. The fetch
took `releases[v][0]` from an unordered list.)*

## Impact

**Believed:** *My plugin decides this, and the others were considered.*

**Actual:** *One implementation decides it and the rest never run.* Which one is decided by
bucket order, then by registration order within a bucket — a property of what happens to be
installed. Measured: the value flips from 80 to 100 by reversing registration, and
installing one unrelated third-party plugin changed the decider on 3 of 3 hooks it joined.

**Breaks whatever the hook decides, and differently per installation — and the losers'
side effects do not happen either.** A plugin architecture exists so behaviour can be
extended: a price resolved, a route chosen, a record classified. When two extensions can
both answer, one is never invoked at all — so a plugin that was also supposed to log, count
or cache as a side effect of answering silently does none of it. The same application, same
code, same inputs, behaves differently on a machine where one extra plugin is installed,
and the returned value carries nothing saying who produced it.

**Detection: poor at the point of use, recoverable afterwards.** No exception, no warning,
and the value has no provenance. It is not undiscoverable — `get_hookimpls()`,
`add_hookcall_monitoring` and `subset_hook_caller` all expose the contention — but nothing
prompts anyone to ask, and a contested hook is indistinguishable from an uncontested one
until someone does.

## Upstream status

**Documented and by design.** `firstresult` is documented, the bucket ordering is stated in
the source, and `tryfirst`/`trylast` exist to influence it. The gap is that a contested hook
looks exactly like an uncontested one at the point the value is used.

## Outcome

**FINDING.** `unstated.check_hook_precedence(plugin_manager)` reports which first-result
hooks have more than one *answering* implementation (wrappers excluded, because a wrapper
cannot answer) and what the resulting call order is.
`unstated.measure_contention(pm, hook_name, **kwargs)` goes further and uses
`subset_hook_caller` to ask each loser what it would have returned — opt-in, because it runs
their side effects. Audit 14, protocol rank 12.
