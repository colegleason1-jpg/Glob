"""Turning an ``infeasible`` status into an answer somebody can act on.

The acquired system's target-risk mode set the budget to 1e9 and then reported
the solver's status verbatim. When a target was unreachable the user saw
``Infeasible``, and because the budget was effectively unlimited but invisible,
the natural inference was that more capital would help. On the shipped default
(``target_risk_goal = 20.0``) it never would: the ceiling is structural.

That is the specific failure this module exists to prevent. ``infeasible`` is an
honest answer to a well-posed question and it stays in :class:`SolveStatus` and in
the audit record untouched. But it is a solver word, not a finance word, and on its
own it points a reader at the wrong remedy. So alongside it we compute:

* the **attainable frontier** — the most reduction this portfolio can deliver, and
  therefore the lowest risk it can reach; and
* a **diagnosis** — which constraint actually bit, distinguishing "no amount of
  capital achieves this" from "this budget does not achieve this", because those
  are different conversations with different remedies.

Two design rules are load-bearing.

**Never silently relax the request.** If the target was missed, the report says so.
A reader who believes they reached 20% when the model reached 38.9% is worse off
than a reader who saw ``Infeasible``, so nothing here substitutes an achievable
goal for the one that was asked for.

**Never claim a diagnosis we cannot support.** If the solver reports infeasible and
none of the checks below explain why, the kind is ``UNDIAGNOSED`` and the
explanation says as much. Guessing here would recreate the acquired system's habit
of printing confident strings that nothing computed.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Mapping

from ..domain.network import SupplyNetwork
from ..risk.response import RiskResponseModel
from .objectives import MaximizeRiskReductionObjective, MinimizeCapitalObjective
from .result import SolveStatus


class InfeasibilityKind:
    """Why a request could not be satisfied.

    The distinction between :attr:`EXCEEDS_STRUCTURAL_CEILING` and
    :attr:`EXCEEDS_BUDGET` is the entire point of this module. The first is a
    portfolio-gap conversation: the interventions on the table cannot get there at
    any price. The second is a funding conversation: they can, for more money than
    was authorised.
    """

    #: The request was satisfiable; no diagnosis needed.
    NONE = "none"
    #: Reduction beyond the baseline risk was requested. Contradictory by
    #: construction, since risk cannot fall below zero.
    EXCEEDS_RISK_CAP = "exceeds_risk_cap"
    #: Unreachable at any budget. More capital does not help.
    EXCEEDS_STRUCTURAL_CEILING = "exceeds_structural_ceiling"
    #: Reachable, but not within the stated budget. More capital does help, and
    #: :attr:`InfeasibilityDiagnosis.capital_required` says how much.
    EXCEEDS_BUDGET = "exceeds_budget"
    #: Solver reported infeasible and none of the above explains it. Reported
    #: honestly rather than guessed at.
    UNDIAGNOSED = "undiagnosed"


@dataclass(frozen=True, slots=True)
class AttainabilityReport:
    """The most this portfolio can deliver, and what it costs to get there.

    ``limited_by`` names the binding constraint at the ceiling: ``"structure"``
    when every node is already at its maximum funding scale (or is held back by a
    dependency), ``"risk_cap"`` when reduction has been clipped at the baseline,
    or ``"budget"`` when a budget was supplied and it bound first.
    """

    max_reduction_pts: float
    attainable_risk_pts: float
    capital_at_ceiling: float
    limited_by: str
    scales: Mapping[str, float]
    baseline_risk_pts: float
    solver_status: str

    @property
    def is_budget_limited(self) -> bool:
        return self.limited_by == "budget"

    def summary(self) -> str:
        return (
            f"Lowest attainable risk {self.attainable_risk_pts:.1f} pts "
            f"(reduction {self.max_reduction_pts:.1f} of a "
            f"{self.baseline_risk_pts:.1f} pt baseline), "
            f"costing {self.capital_at_ceiling:,.0f}, limited by {self.limited_by}."
        )


@dataclass(frozen=True, slots=True)
class InfeasibilityDiagnosis:
    """A CFO-readable account of why a target could not be met.

    ``explanation`` states the fact. ``remedy`` states the class of action that
    would change it — and for :attr:`InfeasibilityKind.EXCEEDS_STRUCTURAL_CEILING`
    that action is explicitly *not* "increase the budget", which is the inference
    the acquired system invited.
    """

    kind: str
    requested_reduction_pts: float
    requested_risk_pts: float | None
    attainable: AttainabilityReport
    budget: float | None
    capital_required: float | None
    explanation: str
    remedy: str

    @property
    def more_capital_would_help(self) -> bool:
        return self.kind == InfeasibilityKind.EXCEEDS_BUDGET

    @property
    def shortfall_pts(self) -> float:
        """How far short of the request the best possible outcome falls."""
        return max(0.0, self.requested_reduction_pts - self.attainable.max_reduction_pts)

    def summary(self) -> str:
        return f"{self.explanation} {self.remedy}"


def _resource_blocks_growth(network: SupplyNetwork, result: Any, resource: Any) -> bool:
    """True when no node can grow into this resource's remaining headroom.

    The smallest step any node could still take, in units of ``resource``:

    * a node at or above its ceiling cannot grow at all, and is skipped;
    * a node that does not draw on this resource is not blocked by it, and is skipped;
    * a node funded between its minimum and its ceiling is continuous there, so any
      positive headroom lets it grow -- step 0;
    * an unfunded node has to clear its own minimum economic scale in one move, so its
      step is ``usage_of(resource) * min_funding_scale``.

    No node left to grow means the portfolio is structurally complete, not
    supply-bound, so the answer is False and the caller reports "structure".
    """
    headroom = float(resource.capacity) - float(result.resource_use.get(resource.name, 0.0))
    if headroom <= 1e-9:
        return True  # exactly tight: the case the original test handled

    scales = result.scales()
    steps: list[float] = []
    for node in network:
        scale = float(scales.get(node.node_id, 0.0))
        if scale >= node.max_funding_scale - 1e-9:
            continue
        per_full = node.usage_of(resource.name)
        if per_full <= 0.0:
            continue
        steps.append(0.0 if scale > 1e-9 else per_full * node.min_funding_scale)

    if not steps:
        return False
    return headroom < min(steps) - 1e-9


def attainable_frontier(
    network: SupplyNetwork,
    risk_response: RiskResponseModel,
    *,
    macro_multiplier: float = 1.0,
    node_macro_multipliers: Mapping[str, float] | None = None,
    budget: float | None = None,
    enforce_risk_cap: bool = True,
    tangent_points: int = 13,
    legacy_bundle_activation: bool = False,
) -> AttainabilityReport:
    """Compute the lowest risk this network can reach, and what it costs.

    Pass ``budget=None`` (the default) for the structural ceiling: the answer to
    "what is the best this portfolio could ever do?", independent of funding. Pass
    a budget to ask the narrower question "what is the best this portfolio can do
    with the money authorised?".

    The two together are what separate a portfolio-gap problem from a funding
    problem, so both are worth surfacing.
    """
    # Imported here rather than at module scope: `optimizer` defers to this module
    # for diagnosis, so a top-level import in both directions would be circular.
    from .optimizer import OptimizationRequest, solve

    result = solve(
        OptimizationRequest(
            network=network,
            objective=MaximizeRiskReductionObjective(),
            risk_response=risk_response,
            budget=budget,
            macro_multiplier=macro_multiplier,
            # The ceiling has to be computed under the same exposure as the solve it
            # is explaining. Omitting this would answer "what is the best this
            # portfolio could ever do?" for a different portfolio than the one the
            # user is looking at, and the frontier is the number we put in front of a
            # CFO in place of the word `infeasible`.
            node_macro_multipliers=dict(node_macro_multipliers or {}),
            enforce_risk_cap=enforce_risk_cap,
            tangent_points=tangent_points,
            legacy_bundle_activation=legacy_bundle_activation,
            diagnose=False,
        )
    )

    # Report against the macro-inflated baseline, because that is the baseline the
    # caller's target was derived from. Using the raw baseline here would describe a
    # target the user typed as 20% back to them as some other number.
    effective_baseline = min(100.0, network.baseline_risk_pts * macro_multiplier)

    reduction = result.raw_risk_reduction_pts
    if enforce_risk_cap:
        reduction = min(reduction, network.baseline_risk_pts)

    # Which constraint actually stopped us. Order matters: report the cap only when
    # it is genuinely what bit, and prefer "budget" when a budget was supplied and
    # the portfolio is not already maxed out, because that is the actionable case.
    at_structural_max = all(
        result.scales().get(node.node_id, 0.0) >= node.max_funding_scale - 1e-9
        for node in network
    )
    # A resource row that is tight while some node is below its maximum is what
    # stopped the portfolio, and "more capital" is the wrong remedy for it: the
    # supply is what has to grow. Checked before the budget for that reason.
    #
    # "Tight" is not "usage reached capacity". This used to test
    # ``resource_use >= capacity - 1e-9``, which is only correct when funding is
    # continuous. With indivisible nodes -- ``min_funding_scale ==
    # max_funding_scale``, which is how a caller models an all-or-nothing item --
    # usage lands on a multiple of one node's demand, so unless capacity happens to
    # be an exact multiple there is stranded headroom no node can use, the row
    # never reads as tight, and the report falls through to "budget": the one
    # remedy this comment says is wrong, recommended under an unlimited budget.
    #
    # Measured before the change, on five indivisible nodes with the budget set high
    # enough that supply was the only possible constraint: across 400 random
    # capacities the supply bound was real 400 times and named 0 times. It fired
    # only on exact multiples of node demand, which is measure-zero for real
    # capacities.
    #
    # The right question is whether anything can still grow into what is left. A
    # node already funded below its ceiling can absorb any amount, so any headroom
    # helps it; an unfunded node must clear its own minimum economic scale in one
    # step. The row is binding when the headroom covers neither.
    tight_resources = tuple(
        resource.name
        for resource in network.resources
        if _resource_blocks_growth(network, result, resource)
        and network.resource_demand_at_full_scale(resource.name) > resource.capacity + 1e-9
    )
    if enforce_risk_cap and reduction >= network.baseline_risk_pts - 1e-9:
        limited_by = "risk_cap"
    elif tight_resources and not at_structural_max:
        limited_by = "resource:" + ",".join(tight_resources)
    elif budget is not None and not at_structural_max:
        limited_by = "budget"
    else:
        limited_by = "structure"

    return AttainabilityReport(
        max_reduction_pts=reduction,
        attainable_risk_pts=max(0.0, effective_baseline - reduction),
        capital_at_ceiling=result.net_capital,
        limited_by=limited_by,
        scales=result.scales(),
        baseline_risk_pts=effective_baseline,
        solver_status=result.status,
    )


def diagnose(request) -> InfeasibilityDiagnosis:
    """Explain why ``request`` could not be satisfied.

    Safe to call on a satisfiable request; it returns
    :attr:`InfeasibilityKind.NONE`. Callers that only want the frontier should use
    :func:`attainable_frontier` directly, which is cheaper.
    """
    from .optimizer import OptimizationRequest, solve

    network = request.network
    required = request.required_risk_reduction_pts or 0.0
    # The reduction floor was derived by the caller from the macro-inflated
    # baseline, so percentages must be reported against the same figure or the
    # diagnosis will quote a target back at the user that they never typed.
    baseline = request.effective_baseline_risk_pts
    requested_risk = baseline - required if request.required_risk_reduction_pts else None

    # Establish that there is anything to explain. Callers reach this either from
    # solve() (already known infeasible) or directly, so we cannot assume.
    probe = solve(replace(request, diagnose=False))

    frontier = attainable_frontier(
        network,
        request.risk_response,
        macro_multiplier=request.macro_multiplier,
        node_macro_multipliers=request.node_macro_multipliers,
        budget=None,
        enforce_risk_cap=request.enforce_risk_cap,
        tangent_points=request.tangent_points,
        legacy_bundle_activation=request.legacy_bundle_activation,
    )

    def build(kind: str, explanation: str, remedy: str, capital: float | None = None):
        return InfeasibilityDiagnosis(
            kind=kind,
            requested_reduction_pts=required,
            requested_risk_pts=requested_risk,
            attainable=frontier,
            budget=request.budget,
            capital_required=capital,
            explanation=explanation,
            remedy=remedy,
        )

    if probe.status == SolveStatus.OPTIMAL:
        return build(
            InfeasibilityKind.NONE,
            "The request was satisfied; there is no infeasibility to explain.",
            "No action required.",
            capital=probe.net_capital,
        )

    # -- 1. Asked for more reduction than there is risk to remove ------------- #
    # Compared against the *raw* baseline, because that is what the in-model cap
    # actually constrains (see OptimizationRequest.effective_baseline_risk_pts).
    cap_baseline = network.baseline_risk_pts
    if request.enforce_risk_cap and required > cap_baseline + 1e-9:
        return build(
            InfeasibilityKind.EXCEEDS_RISK_CAP,
            f"The request asks for {required:.1f} points of risk reduction against a "
            f"risk cap of {cap_baseline:.1f} points. Risk cannot fall below zero, so "
            "no portfolio can satisfy this.",
            "Set a target of 0 or above, or revisit the baseline risk figure.",
        )

    # -- 2. Unreachable at any price ------------------------------------------ #
    if required > frontier.max_reduction_pts + 1e-6:
        target_text = (
            f"A target of {requested_risk:.1f}% risk"
            if requested_risk is not None
            else f"A reduction of {required:.1f} points"
        )
        if frontier.limited_by.startswith("resource:"):
            # The ceiling is a capped supply, not the portfolio's shape. More capital
            # still does not help, but the remedy is different and worth naming.
            bound = frontier.limited_by.split(":", 1)[1]
            return build(
                InfeasibilityKind.EXCEEDS_STRUCTURAL_CEILING,
                f"{target_text} is not reachable while the capacity of {bound} binds. "
                f"Within that capacity the portfolio delivers at most "
                f"{frontier.max_reduction_pts:.1f} points of reduction, taking risk from "
                f"{baseline:.1f}% only as low as {frontier.attainable_risk_pts:.1f}% at a "
                f"cost of {frontier.capital_at_ceiling:,.0f}. The request is short by "
                f"{required - frontier.max_reduction_pts:.1f} points.",
                "This is not a budget constraint: additional capital does not change it. "
                f"Raising the capacity of {bound}, or moving usage to a supply with room, "
                "is what changes it.",
            )
        return build(
            InfeasibilityKind.EXCEEDS_STRUCTURAL_CEILING,
            f"{target_text} is not reachable with the current intervention "
            f"portfolio. Funding every intervention to its maximum delivers "
            f"{frontier.max_reduction_pts:.1f} points of reduction, which takes risk "
            f"from {baseline:.1f}% only as low as {frontier.attainable_risk_pts:.1f}% "
            f"at a cost of {frontier.capital_at_ceiling:,.0f}. The request is short by "
            f"{required - frontier.max_reduction_pts:.1f} points.",
            "This is not a budget constraint: additional capital does not change it. "
            "Reaching the target requires interventions that are not currently on the "
            "table, or a revised target.",
        )

    # -- 3. Reachable, but not for this money -------------------------------- #
    # Only meaningful when a risk floor was actually requested. Without one there is
    # no "cost to reach the target" to compute, and MinimizeCapitalObjective would
    # reject the substitution anyway -- correctly, since minimising capital against
    # no floor trivially allocates nothing.
    if required > 0.0 and request.budget is not None:
        # Re-solve with the target and no budget. If that succeeds, the target is
        # affordable in principle and the budget is what bit, so we can say exactly
        # how much it would take -- the question a reader asks next.
        unfunded = solve(
            replace(
                request,
                objective=MinimizeCapitalObjective(),
                budget=None,
                diagnose=False,
            )
        )
        needed = unfunded.net_capital
        if unfunded.status == SolveStatus.OPTIMAL and needed > request.budget + 1e-6:
            return build(
                InfeasibilityKind.EXCEEDS_BUDGET,
                f"The target is achievable but not within the authorised budget. "
                f"Reaching it costs {needed:,.0f} against a budget of "
                f"{request.budget:,.0f}, a shortfall of "
                f"{needed - request.budget:,.0f}.",
                "Additional capital would resolve this. The figure above is the "
                "minimum required, not an estimate.",
                capital=needed,
            )

    # -- 3b. Mandatory minimum spend alone exceeds the budget ----------------- #
    # Nodes with a minimum funding scale cost something the moment they activate, and
    # bundles or dependencies can force activation. When the floor those rules impose
    # is above the budget, no allocation exists regardless of the risk target.
    if request.budget is not None and frontier.solver_status == SolveStatus.OPTIMAL:
        floor_probe = attainable_frontier(
            network,
            request.risk_response,
            macro_multiplier=request.macro_multiplier,
            node_macro_multipliers=request.node_macro_multipliers,
            budget=request.budget,
            enforce_risk_cap=request.enforce_risk_cap,
            tangent_points=request.tangent_points,
            legacy_bundle_activation=request.legacy_bundle_activation,
        )
        if floor_probe.solver_status != SolveStatus.OPTIMAL:
            return build(
                InfeasibilityKind.EXCEEDS_BUDGET,
                f"No allocation fits within a budget of {request.budget:,.0f}. The "
                "interventions available carry minimum funding levels, and the "
                "cheapest permissible combination costs more than this budget.",
                "Raise the budget, or relax the minimum funding levels on the "
                "interventions concerned.",
            )

    # -- 4. Honest failure to explain ---------------------------------------- #
    return build(
        InfeasibilityKind.UNDIAGNOSED,
        "The solver reported the problem infeasible, and none of the engine's "
        "diagnostic checks — risk cap, structural ceiling, budget — accounts for it.",
        "Treat this as a defect in the model or the inputs and report it rather "
        "than working around it. No diagnosis is being inferred here.",
    )
