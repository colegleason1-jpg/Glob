"""Which plugin's answer are you actually getting, and what never ran?

Catalogue entry: pluggy, ``firstresult=True`` hookspecs.

A ``firstresult`` hook returns the first non-``None`` value **and stops**. ``_multicall``
breaks at that point, so the remaining implementations are **never called at all** — their
answers are not computed and their side effects do not happen.

Which one is reached first is decided by pluggy's six ordered buckets — ``tryfirst`` →
plain → ``trylast``, wrappers before non-wrappers within each — and **within a bucket** by
registration order: later-registered wins among ``tryfirst`` and plain implementations,
**earlier**-registered wins among ``trylast`` ones. Measured::

    all plain    A,B,C -> C,B,A        all tryfirst A,B,C -> C,B,A
    all trylast  A,B,C -> A,B,C        (FIFO — the opposite)

Registration order is a property of the installed environment. In pytest it is a hardcoded
builtin tuple, then ``PYTEST_PLUGINS``, then ``-p`` arguments, then entry points, then
conftest discovery.

**Contested hooks are normal, not pathological.** On stock pytest 9.1.1, 9 of the 17
first-result hookspecs already have more than one answering implementation, because
abstaining by returning ``None`` is the designed idiom and it works. So this check does not
claim a contested hook is wrong. It reports where **order decides**, which is the fact the
return value does not carry — and that is enough: installing one unrelated third-party
plugin (``pytest-subtests``) was measured to change the deciding implementation of 3 of 3
hooks it joined, with 0 warnings.

The contention **can** be investigated after the fact, and ``measure_contention`` below does
exactly that using pluggy's public API. An earlier version of this file claimed no such API
existed; that was wrong.
"""

from __future__ import annotations

from typing import Any

from .._finding import Finding


def _answering(impls) -> list:
    """Implementations that can actually produce a value. Wrappers cannot."""
    return [i for i in impls
            if not (getattr(i, "hookwrapper", False) or getattr(i, "wrapper", False))]


def _first_result_hooks(plugin_manager: Any):
    """Yield (name, caller, answering impls in call order) for each first-result hook."""
    relay = getattr(plugin_manager, "hook", None)
    if relay is None:
        return
    for name in dir(relay):
        if name.startswith("_"):
            continue
        try:
            caller = getattr(relay, name)
        except Exception:                      # a relay attribute may raise on access
            continue
        spec = getattr(caller, "spec", None)
        opts = getattr(spec, "opts", None)
        if not isinstance(opts, dict) or not opts.get("firstresult"):
            continue
        try:
            impls = caller.get_hookimpls()
        except Exception:
            continue
        # _multicall iterates reversed(hook_impls), so reversed() is the true call order.
        yield name, caller, _answering(list(reversed(impls)))


def check_hook_precedence(plugin_manager: Any) -> Finding | None:
    """Return a Finding when a first-result hook has more than one *answering* plugin.

    ``None`` means every first-result hook has at most one implementation that can produce
    a value — wrappers are excluded, because a wrapper cannot answer and its presence does
    not make a hook contested.
    """
    contested = {
        name: [getattr(i, "plugin_name", None) or f"<unnamed {id(i):x}>" for i in impls]
        for name, _caller, impls in _first_result_hooks(plugin_manager)
        if len(impls) > 1
    }
    if not contested:
        return None

    worst_name = max(contested, key=lambda k: len(contested[k]))
    worst = contested[worst_name]

    return Finding(
        library="pluggy",
        component="firstresult hookspecs",
        assumption=(
            "the caller knows which registered plugin answers a first-result hook, and "
            "that the others were considered"
        ),
        signal=(
            "nothing at the point the value is used: the return value is the bare value "
            "the winner produced, with no provenance, and the losing implementations are "
            "never called, so they emit nothing either"
        ),
        remedy=(
            "make precedence explicit rather than implicit in import order — tryfirst / "
            "trylast AND controlled registration, or drop firstresult and reconcile the "
            "full list. Two plugins both marked tryfirst still fall back to registration "
            "order. To see what the losers would have said, call measure_contention()"
        ),
        observed={
            "first_result_hooks_contested": len(contested),
            "hooks": ", ".join(sorted(contested)),
            "most_contested_hook": worst_name,
            "call_order_first_wins": " > ".join(str(p) for p in worst),
            "plugins_that_will_not_run_on_it": len(worst) - 1,
            "decided_by": (
                "bucket order (tryfirst > plain > trylast), then registration order "
                "within a bucket"
            ),
            "note": (
                "a contested hook is normal — abstaining with None is the designed idiom. "
                "What is unstated is that order decides and the losers never run."
            ),
        },
        severity="medium",
    )


def measure_contention(plugin_manager: Any, hook_name: str, **kwargs) -> dict[str, Any]:
    """Actually call the losers and report what they would have answered.

    **This calls hook implementations, so it runs their side effects.** It is opt-in for
    that reason and is not used by ``check_hook_precedence``.

    Uses ``subset_hook_caller(name, remove_plugins=[...])`` — public pluggy API — to ask
    each implementation in turn what it would return once the ones ahead of it are removed.
    """
    relay = getattr(plugin_manager, "hook", None)
    caller = getattr(relay, hook_name, None)
    if caller is None:
        raise ValueError(f"no hook named {hook_name!r}")

    impls = _answering(list(reversed(caller.get_hookimpls())))
    answers: list[tuple[str, Any]] = []
    removed: list[Any] = []
    for impl in impls:
        try:
            sub = plugin_manager.subset_hook_caller(hook_name, remove_plugins=removed)
            answers.append((getattr(impl, "plugin_name", "?"), sub(**kwargs)))
        except Exception as exc:               # a plugin may refuse the arguments
            answers.append((getattr(impl, "plugin_name", "?"), f"<{type(exc).__name__}>"))
        removed.append(impl.plugin)

    distinct = {repr(v) for _, v in answers if v is not None}
    return {
        "hook": hook_name,
        "answers_in_call_order": answers,
        "winner": answers[0] if answers else None,
        "implementations_that_never_ran": max(0, len(answers) - 1),
        "distinct_non_none_answers": len(distinct),
        "genuinely_ambiguous": len(distinct) > 1,
    }
