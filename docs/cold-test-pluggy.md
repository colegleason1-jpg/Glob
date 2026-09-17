# Audit 14: pluggy — protocol rank 12

2026-09-17 · **AUDITING: pluggy** · protocol rank **12** of 15,000.
Versions measured: **0.6.0, 0.13.1, 1.0.0, 1.2.0, 1.4.0, 1.5.0, 1.6.0.**

**Pre-registered eligibility:** *eligible — hook call order and the firstresult rule depend
on properties of the plugins the caller registers.* Registered in
`unstated/protocol/targets.py` with the other 99 top-100 targets, before any audit past
rank 10.

**First audit run through the staged pipeline** — hypotheses written to
`staging/audit-014-pluggy.json` before measuring, measurements recorded there, adversarially
verified, and promoted only after review. See [`staging/README.md`](../staging/README.md).

## Hypotheses, registered before measuring

| | hypothesis | outcome |
| --- | --- | --- |
| H1 | `firstresult=True` silently discards every answer but one | **reproduced** |
| H2 | call order is LIFO, so precedence follows import order | **reproduced** |
| H3 | `tryfirst` is not a total order; ties fall back to registration order | **reproduced** |
| H4 | an exception in one hookimpl aborts the call, losing other contributions | **LOUD** — it raises `ValueError` to the caller. Correct behaviour, no entry. |

H4 is recorded as LOUD rather than quietly dropped. An exception is the library telling you.

## Assumption

At most one registered plugin answers a first-result hook, so which one answers does not
need to be decided.

## Measured

Two plugins, both answering the same `firstresult=True` hook:

```
both plugins' answers          : [80, 100]
firstresult=True returns       : 80
answers discarded              : [100]
warnings emitted               : 0
exceptions                     : 0
```

**Which one wins is decided by registration order, and pluggy calls implementations LIFO —
the plugin registered *last* runs *first*.**

| registration | call order | value returned |
| --- | --- | --- |
| catalogue, then promotion | promotion → catalogue | **80** |
| promotion, then catalogue | catalogue → promotion | **100** |

Registration order is import order: a property of the installed environment, not of
anything the caller declared.

`tryfirst=True` does not settle it. Two implementations both marked `tryfirst`:

```
registered A then B -> 'B'
registered B then A -> 'A'
```

### There is no way to see what was discarded

| | |
| --- | --- |
| the return value | a bare `int` — no provenance |
| `get_hookimpls()` | lists the **implementations**, not their results |
| `add_hookcall_monitoring` | reports `[('resolve', 80)]` — the winner only |

### How much runs on this rule

| | |
| --- | --- |
| pytest hookspecs | 52 |
| of those, `firstresult=True` | **17 (33%)** |

Including `pytest_fixture_setup`, `pytest_ignore_collect`, `pytest_collection`,
`pytest_cmdline_main`, `pytest_cmdline_parse`, `pytest_collect_directory`.

### One more asymmetry

`None` means "no opinion" and falls through to the next plugin. `0` does not — it is an
answer. So a plugin can never legitimately answer `None`, and a plugin that computes `None`
as a real result silently abstains instead.

## Version range

| version | released | order-dependent? | warnings |
| --- | --- | --- | --- |
| 0.6.0 | 2018-04-15 | **yes** | 0 |
| 0.13.1 | 2019-11-21 | **yes** | 0 |
| 1.0.0 | 2021-08-25 | **yes** | 0 |
| 1.2.0 | 2023-06-21 | **yes** | 0 |
| 1.4.0 | 2024-01-24 | **yes** | 0 |
| 1.5.0 | 2024-04-20 | **yes** | 0 |
| 1.6.0 | 2025-05-15 | **yes** | 0 |

**7.1 years, 7 releases measured, unchanged throughout. 1.6.0 is the current latest.**
Seven of pluggy's releases in that range were sampled, not all of them.

## Impact

**Believed:** *My plugin decides this.*

**Actual:** *One of the plugins decides this, and which one is whichever was imported last.*
Measured: with two plugins answering, the value returned flips from 80 to 100 purely by
reversing registration order, with 0 warnings.

**Breaks whatever the hook was deciding, and does it differently per installation.** A
plugin architecture exists so behaviour can be extended — a price resolved, a route chosen,
a record classified, a file's handler selected. When two extensions both answer, one of them
silently loses, and which one depends on what else is installed and in what order. The same
application, same code, same inputs, gives a different answer on a machine where one extra
plugin is present. The value that comes back is a bare number or string with nothing
attached saying who produced it, so the answer cannot be traced even after someone notices
it changed.

**Detection: very poor, and it fails in the direction that looks like success.** There is no
exception, no warning, and no API that reports a contested hook. A single-plugin development
environment behaves correctly and deterministically; the ambiguity appears only once a
second plugin that answers the same hook is installed, which is exactly when nobody is
looking at that hook. Adding an unrelated plugin can change an answer elsewhere in the
system.

## Upstream status

**Documented and by design.** `firstresult` is in pluggy's documentation, the LIFO ordering
is stated, and `tryfirst`/`trylast` exist precisely to influence it. The gap is not that the
rule is hidden — it is that a contested hook is indistinguishable from an uncontested one at
the point the value is used, and pluggy exposes no way to ask.

## Outcome

**FINDING.** `unstated.check_hook_precedence(plugin_manager)` — reports, for the plugins
actually registered, which first-result hooks have more than one implementation and what the
resulting call order is. Silent when every first-result hook has at most one implementation.
Audit 14, protocol rank 12.
