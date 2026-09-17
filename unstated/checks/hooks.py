"""Which plugin's answer are you actually getting?

Catalogue entry: pluggy, ``firstresult=True`` hookspecs.

A ``firstresult`` hook returns the first non-``None`` value and **discards the rest**.
Which one is first is decided by registration order, and pluggy calls implementations
**LIFO** — the plugin registered *last* runs *first*. Registration order is import order,
which is a property of the installed environment, not of anything the caller declared.

Measured on pluggy 1.6.0 with two plugins that both answer::

    registered catalogue then promotion -> 80    (promotion wins)
    registered promotion then catalogue -> 100   (catalogue wins)

0 warnings, 0 exceptions, and the return value is a bare ``int`` carrying no provenance.
``tryfirst=True`` does not settle it either: two implementations both marked ``tryfirst``
fall back to registration order. And there is **no API that reveals the discarded
answers** — ``get_hookimpls()`` lists the implementations but not their values, and
``add_hookcall_monitoring`` reports only the winner.

33% of pytest's own hookspecs (17 of 52) are ``firstresult``, including
``pytest_fixture_setup`` and ``pytest_ignore_collect``.

The check does not try to pick the right plugin — it cannot know which you meant. It
reports, for the hooks you have actually registered, **where more than one plugin can
answer**, which is the fact the return value does not carry.
"""

from __future__ import annotations

from typing import Any

from .._finding import Finding


def check_hook_precedence(plugin_manager: Any) -> Finding | None:
    """Return a Finding when a ``firstresult`` hook has more than one implementation.

    ``None`` means every first-result hook has at most one implementation, so nothing is
    being silently decided by import order.
    """
    contested: dict[str, list[str]] = {}
    hook_relay = getattr(plugin_manager, "hook", None)
    if hook_relay is None:
        return None

    for name in dir(hook_relay):
        if name.startswith("_"):
            continue
        caller = getattr(hook_relay, name, None)
        spec = getattr(caller, "spec", None)
        if spec is None or not getattr(spec, "opts", {}).get("firstresult"):
            continue
        try:
            impls = caller.get_hookimpls()
        except (AttributeError, TypeError):
            continue
        if len(impls) > 1:
            # LIFO: pluggy calls the last-registered first, so reverse for call order.
            contested[name] = [i.plugin_name for i in reversed(impls)]

    if not contested:
        return None

    worst = max(contested.values(), key=len)
    return Finding(
        library="pluggy",
        component="firstresult hookspecs",
        assumption=(
            "at most one registered plugin answers a first-result hook, so which one "
            "answers does not need to be decided"
        ),
        signal=(
            "nothing: the return value is the bare value the winner produced, with no "
            "provenance, and no API exposes the answers that were discarded — "
            "get_hookimpls() lists implementations but not their results"
        ),
        remedy=(
            "if precedence matters, make it explicit rather than implicit in import "
            "order: use tryfirst/trylast AND control registration, or drop firstresult "
            "and reconcile the full list yourself. Note that two plugins both marked "
            "tryfirst still fall back to registration order"
        ),
        observed={
            "first_result_hooks_contested": len(contested),
            "hooks": ", ".join(sorted(contested)),
            "most_contested_hook": max(contested, key=lambda k: len(contested[k])),
            "its_call_order_first_wins": " > ".join(worst),
            "answers_discarded_per_call": len(worst) - 1,
            "decided_by": "registration order (LIFO), i.e. import order",
        },
        severity="high" if len(worst) > 2 else "medium",
    )
