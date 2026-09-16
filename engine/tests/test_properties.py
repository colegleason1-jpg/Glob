"""Property-based tests: invariants that must hold for every valid input.

Known-answer tests prove the engine is right on cases someone thought of.
These prove it does not violate its own structural promises on cases nobody
thought of. Hypothesis generates networks, budgets, dependency chains and
bundles, then checks that whatever comes back respects the constraints the model
claims to enforce.

The acquired system displayed the literal string
``"Verification: zero fractional violations detected"`` in its UI. Nothing
computed it. These tests, plus the post-solve ``ConstraintReport``, are what that
sentence was supposed to mean.
"""

from __future__ import annotations

import numpy as np
import pytest
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

from scrcae.domain import Bundle, Dependency, DomainError, Intervention, SupplyNetwork
from scrcae.optimization import (
    LegacyWeightedObjective,
    MonetaryNPVObjective,
    OptimizationRequest,
    PriceBook,
    SolveStatus,
    solve,
)
from scrcae.risk import AllocationConcaveResponse, LinearResponse, ParameterPowerResponse
from scrcae.stochastic import (
    LognormalShock,
    SimulationRequest,
    UniformCorrelation,
    repair_to_correlation,
)
from scrcae.stochastic import run as run_simulation

SLOW = settings(
    max_examples=40,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much],
)

finite = dict(allow_nan=False, allow_infinity=False)


# --------------------------------------------------------------------------- #
# Strategies
# --------------------------------------------------------------------------- #


@st.composite
def interventions(draw, count: int):
    out = []
    for i in range(count):
        mes = draw(st.floats(min_value=0.05, max_value=1.0, **finite))
        out.append(
            Intervention(
                node_id=f"N{i}",
                name=f"N{i}",
                cost=draw(st.floats(min_value=1_000.0, max_value=500_000.0, **finite)),
                risk_reduction_pts=draw(
                    st.floats(min_value=0.0, max_value=25.0, **finite)
                ),
                lead_time_saved_days=draw(
                    st.floats(min_value=0.0, max_value=60.0, **finite)
                ),
                carbon_tons=draw(st.floats(min_value=-500.0, max_value=500.0, **finite)),
                min_funding_scale=mes,
                max_funding_scale=1.0,
            )
        )
    return tuple(out)


@st.composite
def networks(draw, min_nodes: int = 1, max_nodes: int = 6):
    count = draw(st.integers(min_value=min_nodes, max_value=max_nodes))
    nodes = draw(interventions(count))
    ids = [n.node_id for n in nodes]

    # Dependencies strictly forward in index order, which guarantees acyclicity.
    dependencies = []
    if count >= 2:
        pairs = draw(
            st.lists(
                st.tuples(
                    st.integers(min_value=0, max_value=count - 1),
                    st.integers(min_value=0, max_value=count - 1),
                ),
                max_size=count,
            )
        )
        seen = set()
        for a, b in pairs:
            lo, hi = min(a, b), max(a, b)
            if lo != hi and (hi, lo) not in seen:
                seen.add((hi, lo))
                dependencies.append(
                    Dependency(dependent=ids[hi], prerequisite=ids[lo])
                )

    bundles = []
    if count >= 2 and draw(st.booleans()):
        size = draw(st.integers(min_value=2, max_value=min(3, count)))
        members = tuple(ids[:size])
        # Draw the discount as a *fraction* of the bundle's own gross cost rather
        # than as a free-floating currency amount. The domain model rejects a
        # discount that cancels the spend it applies to, so an unconstrained draw
        # would spend most of its time generating invalid networks; expressing it
        # as a fraction generates the whole valid range and nothing outside it.
        gross = sum(
            node.cost * node.max_funding_scale
            for node in nodes
            if node.node_id in members
        )
        fraction = draw(st.floats(min_value=0.0, max_value=0.95, **finite))
        bundles.append(
            Bundle(
                name="B0",
                discount=gross * fraction,
                required_nodes=members,
            )
        )

    return SupplyNetwork(
        baseline_risk_pts=draw(st.floats(min_value=1.0, max_value=100.0, **finite)),
        interventions=nodes,
        dependencies=tuple(dependencies),
        bundles=tuple(bundles),
    )


RESPONSES = st.sampled_from(
    [
        LinearResponse(),
        ParameterPowerResponse(exponent=0.85),
        AllocationConcaveResponse(exponent=0.85),
        AllocationConcaveResponse(exponent=0.6),
    ]
)

OBJECTIVES = st.sampled_from(
    [
        LegacyWeightedObjective(weight=0.0),
        LegacyWeightedObjective(weight=0.5),
        LegacyWeightedObjective(weight=1.0),
        MonetaryNPVObjective(
            prices=PriceBook(
                value_per_risk_point=80_000.0,
                value_per_lead_time_day=1_500.0,
                price_per_carbon_ton=60.0,
            )
        ),
    ]
)


# --------------------------------------------------------------------------- #
# Optimizer invariants
# --------------------------------------------------------------------------- #


@SLOW
@given(
    network=networks(),
    budget=st.floats(min_value=0.0, max_value=2_000_000.0, **finite),
    objective=OBJECTIVES,
    response=RESPONSES,
    cap=st.booleans(),
)
def test_every_solved_portfolio_satisfies_every_constraint(
    network, budget, objective, response, cap
):
    """The engine's own verifier must agree with the solver on every input.

    ``_verify`` recomputes each constraint from the returned allocation vector
    rather than trusting the solver. If those two ever disagree, something is
    wrong regardless of which one is right.
    """
    result = solve(
        OptimizationRequest(
            network=network,
            objective=objective,
            risk_response=response,
            budget=budget,
            enforce_risk_cap=cap,
        )
    )
    assume(result.status == SolveStatus.OPTIMAL)
    assert result.constraint_report.is_feasible, result.constraint_report.summary()
    assert result.constraint_report.violations == ()


@SLOW
@given(
    network=networks(),
    budget=st.floats(min_value=0.0, max_value=2_000_000.0, **finite),
    response=RESPONSES,
)
def test_budget_is_never_exceeded(network, budget, response):
    result = solve(
        OptimizationRequest(
            network=network,
            objective=LegacyWeightedObjective(weight=0.5),
            risk_response=response,
            budget=budget,
            enforce_risk_cap=False,
        )
    )
    assume(result.status == SolveStatus.OPTIMAL)

    # Checked at the same scale-relative tolerance the engine verifies against.
    # CBC's feasibility tolerance is a floating-point property of the solver, so
    # an exact-arithmetic assertion here would be testing CBC, not the model.
    # What the engine promises is that any overshoot is (a) within tolerance and
    # (b) reported rather than silently absorbed.
    allowance = max(1e-6, budget * 1e-6)
    assert result.net_capital <= budget + allowance
    assert result.constraint_report.residual_slack.get("budget", 0.0) <= allowance


@SLOW
@given(
    network=networks(),
    budget=st.floats(min_value=0.0, max_value=2_000_000.0, **finite),
    response=RESPONSES,
)
def test_minimum_economic_scale_is_all_or_nothing(network, budget, response):
    """A node is either unfunded or funded at least to its minimum viable scale.

    Anything in between represents capital committed to a project too small to
    deliver, which is the entire economic content of the binary variable.
    """
    result = solve(
        OptimizationRequest(
            network=network,
            objective=LegacyWeightedObjective(weight=0.5),
            risk_response=response,
            budget=budget,
            enforce_risk_cap=False,
        )
    )
    assume(result.status == SolveStatus.OPTIMAL)

    by_id = {n.node_id: n for n in network.interventions}
    for allocation in result.allocations:
        scale = allocation.funding_scale
        node = by_id[allocation.node_id]
        assert scale >= -1e-6
        assert scale <= node.max_funding_scale + 1e-6
        assert scale <= 1e-6 or scale >= node.min_funding_scale - 1e-6


@SLOW
@given(
    network=networks(min_nodes=2),
    budget=st.floats(min_value=0.0, max_value=2_000_000.0, **finite),
    response=RESPONSES,
)
def test_dependent_never_outruns_its_prerequisite(network, budget, response):
    assume(network.dependencies)
    result = solve(
        OptimizationRequest(
            network=network,
            objective=LegacyWeightedObjective(weight=0.5),
            risk_response=response,
            budget=budget,
            enforce_risk_cap=False,
        )
    )
    assume(result.status == SolveStatus.OPTIMAL)

    scales = result.scales()
    for dependency in network.dependencies:
        assert scales[dependency.dependent] <= scales[dependency.prerequisite] + 1e-6


@SLOW
@given(
    network=networks(min_nodes=2),
    budget=st.floats(min_value=0.0, max_value=2_000_000.0, **finite),
    response=RESPONSES,
)
def test_bundle_discount_requires_all_of_its_nodes(network, budget, response):
    assume(network.bundles)
    result = solve(
        OptimizationRequest(
            network=network,
            objective=LegacyWeightedObjective(weight=0.5),
            risk_response=response,
            budget=budget,
            enforce_risk_cap=False,
        )
    )
    assume(result.status == SolveStatus.OPTIMAL)

    scales = result.scales()
    for bundle in network.bundles:
        if bundle.name in result.active_bundles:
            for node_id in bundle.required_nodes:
                assert scales[node_id] > 1e-6, (
                    f"bundle {bundle.name} paid out while {node_id} was unfunded"
                )


@SLOW
@given(
    network=networks(),
    budget=st.floats(min_value=0.0, max_value=2_000_000.0, **finite),
    response=RESPONSES,
    weight=st.sampled_from([0.0, 0.25, 0.5, 1.0]),
)
def test_risk_reduction_never_exceeds_the_baseline_when_capped(
    network, budget, response, weight
):
    """The F16 property. The objective weight is a parameter for a measured reason.

    F16 was not "the cap was wrong", it was "the cap stopped binding in proportion
    to how little the objective cared about risk". A concave response is
    linearised into a variable bounded only from above, which rises to its bound
    only because the objective pushes it there. At ``weight=1.0`` the objective is
    pure risk and pushes hard; at ``weight=0.0`` — a lead-time mandate — nothing
    pushes it and a cap written against it caps very little.

    This asserted the invariant at ``weight=1.0`` only. Measured, by reverting the
    fix and re-running 400 examples: the worst overshoot a regression can produce
    is **2.5 points at weight 1.0 against 64.0 points at weight 0.0**, a factor of
    26. The single-weight form was not blind to the defect, but it could only ever
    have caught it in its mildest form, a couple of points above a baseline that
    ranges to 100 — close enough to the assertion's own tolerance to be worth
    nothing as a guard.

    Two further things that measurement said, and that are the reason this test is
    no longer the only guard:

    * The violation rate is about 8% of solved cases. At ``max_examples=40`` split
      across four weights that is under one expected hit per weight, so this test
      catches a reintroduced F16 roughly half the time. A property that fails open
      on a coin flip is a monitor, not a guard.
    * So the real guard is the deterministic case below, which fails every time.
      This one stays because it searches where the deterministic case cannot.
    """
    result = solve(
        OptimizationRequest(
            network=network,
            objective=LegacyWeightedObjective(weight=weight),
            risk_response=response,
            budget=budget,
            enforce_risk_cap=True,
        )
    )
    assume(result.status == SolveStatus.OPTIMAL)
    assert result.raw_risk_reduction_pts <= network.baseline_risk_pts + 1e-4
    assert 0.0 - 1e-6 <= result.optimized_risk_pts <= network.baseline_risk_pts + 1e-6


@pytest.mark.parametrize("weight", [0.0, 0.25, 0.5, 1.0])
def test_f16_the_risk_cap_binds_when_the_objective_does_not_push_it(weight):
    """The deterministic half of the F16 guard: fails on every run, not 8% of them.

    Baseline risk is 10 points and two nodes each claim 20, so any funded
    portfolio overshoots and the cap has to be what stops it. Lead time is on
    both nodes so ``weight=0.0`` still has a reason to fund them -- without that
    the low-weight case funds nothing and proves nothing, which is what the
    premise assertion below is for.

    Reverting the fix (pointing ``cap_expr`` back at the objective's own chord
    variable) makes this fail at all four weights, with the funded portfolio
    delivering 40.0 points against a 10.0-point baseline at weights 0.0 to 0.5
    and 20.0 at weight 1.0. The property test above, on the same revert, passed.
    """
    network = SupplyNetwork(
        baseline_risk_pts=10.0,
        interventions=(
            Intervention(
                "A", cost=10_000.0, risk_reduction_pts=20.0, lead_time_saved_days=30.0
            ),
            Intervention(
                "B", cost=10_000.0, risk_reduction_pts=20.0, lead_time_saved_days=30.0
            ),
        ),
    )
    result = solve(
        OptimizationRequest(
            network=network,
            objective=LegacyWeightedObjective(weight=weight),
            risk_response=AllocationConcaveResponse(exponent=0.85),
            budget=1_000_000.0,
            enforce_risk_cap=True,
        )
    )
    assert result.status == SolveStatus.OPTIMAL
    assert sum(result.scales().values()) > 1e-6, (
        "a portfolio funding nothing cannot overshoot, so it cannot test the cap"
    )
    assert result.raw_risk_reduction_pts <= network.baseline_risk_pts + 1e-4, (
        f"cap did not bind at weight={weight}: "
        f"{result.raw_risk_reduction_pts:.3f} pts against a 10.0 pt baseline"
    )
    assert result.constraint_report.is_feasible


def test_f19_the_risk_cap_is_over_tight_and_refuses_silently():
    """A known, measured limitation, pinned so it cannot be forgotten or drift.

    The cap uses an outer (tangent) approximation, which must over-report or F16
    comes back. Over-reporting means the cap is tighter than the cap: a portfolio
    whose *true* reduction is under the baseline can still be refused. Choosing
    the Chebyshev-optimal single tangent cut the worst-case over-report from
    12.7% to 3.5% at exponent 0.85 and 19.4% to 5.8% at 0.6, but it cannot reach
    zero, and this test fixes what is left in place.

    At exponent 0.6 one node funded at its 0.3 minimum delivers 9.712 points
    against a 10-point baseline -- inside the cap with 3% to spare -- but the
    tangent puts it at 10.280, so the whole portfolio is refused. What makes this
    a defect rather than conservatism is the *shape* of the refusal: OPTIMAL
    status, a zero allocation, and nothing anywhere saying the budget went unspent
    because of an approximation rather than because spending it was a bad idea.

    F19 in ADR-001. If this test starts failing because the engine now funds
    something, the fix landed and this test should be deleted, not loosened.
    """
    network = SupplyNetwork(
        baseline_risk_pts=10.0,
        interventions=(
            Intervention(
                "A", cost=10_000.0, risk_reduction_pts=20.0, lead_time_saved_days=30.0
            ),
            Intervention(
                "B", cost=10_000.0, risk_reduction_pts=20.0, lead_time_saved_days=30.0
            ),
        ),
    )
    response = AllocationConcaveResponse(exponent=0.6)
    # The refused portfolio is genuinely inside the cap.
    truth = response.evaluate(20.0, 0.3, 1.0)
    assert truth < network.baseline_risk_pts, "premise: funding one node is legal"

    result = solve(
        OptimizationRequest(
            network=network,
            objective=LegacyWeightedObjective(weight=0.0),
            risk_response=response,
            budget=1_000_000.0,
            enforce_risk_cap=True,
        )
    )
    # Every part of the failure mode, spelled out.
    assert result.status == SolveStatus.OPTIMAL, "it does not report a refusal"
    assert sum(result.scales().values()) == pytest.approx(0.0, abs=1e-9)
    assert result.total_lead_time_saved_days == pytest.approx(0.0, abs=1e-9)
    assert result.net_capital == pytest.approx(0.0, abs=1e-6)
    assert result.constraint_report.is_feasible, "and it does not report a violation"


@SLOW
@given(
    network=networks(),
    budget=st.floats(min_value=0.0, max_value=2_000_000.0, **finite),
    response=RESPONSES,
)
def test_reported_risk_reduction_equals_the_ground_truth_response(
    network, budget, response
):
    """Reported figures must come from the exact response function, never from
    the linearised objective the solver optimised. Otherwise the tangent
    approximation error would leak into user-facing numbers."""
    result = solve(
        OptimizationRequest(
            network=network,
            objective=LegacyWeightedObjective(weight=0.5),
            risk_response=response,
            budget=budget,
            enforce_risk_cap=False,
        )
    )
    assume(result.status == SolveStatus.OPTIMAL)

    by_id = {n.node_id: n for n in network.interventions}
    expected = sum(
        response.evaluate(by_id[a.node_id].risk_reduction_pts, a.funding_scale, 1.0)
        for a in result.allocations
    )
    assert result.raw_risk_reduction_pts == pytest.approx(expected, abs=1e-6)


@SLOW
@given(
    network=networks(),
    small=st.floats(min_value=0.0, max_value=400_000.0, **finite),
    extra=st.floats(min_value=0.0, max_value=800_000.0, **finite),
)
def test_more_budget_is_never_worse(network, small, extra):
    """Monotonicity in the budget. Relaxing a constraint cannot shrink the
    feasible set, so the optimum cannot get worse. A violation would mean the
    solve is unstable or the model is misspecified."""
    request = dict(
        network=network,
        objective=MonetaryNPVObjective(
            prices=PriceBook(value_per_risk_point=90_000.0)
        ),
        risk_response=LinearResponse(),
        enforce_risk_cap=False,
    )
    lean = solve(OptimizationRequest(budget=small, **request))  # type: ignore[arg-type]
    rich = solve(
        OptimizationRequest(budget=small + extra, **request)  # type: ignore[arg-type]
    )
    assume(lean.status == SolveStatus.OPTIMAL and rich.status == SolveStatus.OPTIMAL)
    assert rich.objective_value >= lean.objective_value - 1e-3


@SLOW
@given(network=networks())
def test_a_zero_budget_funds_nothing(network):
    result = solve(
        OptimizationRequest(
            network=network,
            objective=LegacyWeightedObjective(weight=0.5),
            risk_response=LinearResponse(),
            budget=0.0,
            enforce_risk_cap=False,
        )
    )
    assume(result.status == SolveStatus.OPTIMAL)
    # A bundle discount cannot manufacture spending capacity from nothing,
    # because a bundle requires its nodes to be active and those nodes cost money.
    assert result.active_allocations == ()
    assert result.net_capital == pytest.approx(0.0, abs=1e-6)


@SLOW
@given(
    network=networks(),
    budget=st.floats(min_value=1_000.0, max_value=2_000_000.0, **finite),
)
def test_solve_is_deterministic(network, budget):
    """Identical inputs, identical outputs. Required for the audit record's
    input hash to mean anything."""
    request = OptimizationRequest(
        network=network,
        objective=LegacyWeightedObjective(weight=0.5),
        risk_response=AllocationConcaveResponse(exponent=0.85),
        budget=budget,
        enforce_risk_cap=False,
    )
    first = solve(request)
    second = solve(request)
    assume(first.status == SolveStatus.OPTIMAL)
    assert first.scales() == pytest.approx(second.scales(), abs=1e-9)
    assert first.objective_value == pytest.approx(second.objective_value, rel=1e-12)
    assert first.audit["input_hash"] == second.audit["input_hash"]


@SLOW
@given(
    network=networks(),
    budget=st.floats(min_value=1_000.0, max_value=1e9, **finite),
)
def test_residual_slack_is_always_reported_and_within_tolerance(network, budget):
    """Whatever numerical slack the solver leaves behind must be measured.

    This is the replacement for the acquired system's hard-coded UI string
    "Verification: zero fractional violations detected". Slack is usually zero,
    but when it is not, the number is on the record instead of being asserted
    away.
    """
    result = solve(
        OptimizationRequest(
            network=network,
            objective=LegacyWeightedObjective(weight=0.5),
            risk_response=LinearResponse(),
            budget=budget,
            enforce_risk_cap=True,
        )
    )
    assume(result.status == SolveStatus.OPTIMAL)
    report = result.constraint_report

    assert report.is_feasible, report.summary()
    assert "budget" in report.checks_performed
    assert "risk_cap" in report.checks_performed
    for name, value in report.residual_slack.items():
        bound = budget if name == "budget" else network.baseline_risk_pts
        assert value >= 0.0
        assert value <= max(1e-6, abs(bound) * 1e-6), (name, value)


# --------------------------------------------------------------------------- #
# Domain validation invariants
# --------------------------------------------------------------------------- #


@given(
    st.floats(min_value=-1e6, max_value=1e6, **finite),
    st.floats(min_value=-5.0, max_value=5.0, **finite),
)
def test_invalid_interventions_are_rejected_at_construction(cost, mes):
    """Validation belongs in the domain model, not in a Streamlit callback.

    The acquired system validated the uploaded file's *columns* and then trusted
    every value in it. A negative cost or an out-of-range funding scale would
    flow straight into the solver.
    """
    # A min_funding_scale of exactly 0 is legitimate: it describes a node with
    # no minimum viable size, i.e. purely continuous funding. Only values outside
    # [0, 1] are meaningless.
    invalid = cost < 0 or not 0.0 <= mes <= 1.0
    if not invalid:
        Intervention("N0", cost=cost, risk_reduction_pts=1.0, min_funding_scale=mes)
        return
    with pytest.raises((ValueError, DomainError)):
        Intervention("N0", cost=cost, risk_reduction_pts=1.0, min_funding_scale=mes)


def test_dependency_cycles_are_rejected():
    """An unsatisfiable cascade must fail at construction with a named cycle,
    not present as a mysterious infeasible solve."""
    with pytest.raises(DomainError, match="cycle"):
        SupplyNetwork(
            baseline_risk_pts=50.0,
            interventions=(
                Intervention("A", cost=1.0, risk_reduction_pts=1.0),
                Intervention("B", cost=1.0, risk_reduction_pts=1.0),
                Intervention("C", cost=1.0, risk_reduction_pts=1.0),
            ),
            dependencies=(
                Dependency("A", "B"),
                Dependency("B", "C"),
                Dependency("C", "A"),
            ),
        )


def test_dependencies_and_bundles_must_reference_real_nodes():
    node = Intervention("A", cost=1.0, risk_reduction_pts=1.0)
    with pytest.raises(DomainError):
        SupplyNetwork(
            baseline_risk_pts=50.0,
            interventions=(node,),
            dependencies=(Dependency("A", "GHOST"),),
        )
    with pytest.raises(DomainError):
        SupplyNetwork(
            baseline_risk_pts=50.0,
            interventions=(node,),
            bundles=(Bundle("B", discount=1.0, required_nodes=("A", "GHOST")),),
        )


def test_duplicate_node_ids_are_rejected():
    with pytest.raises(DomainError):
        SupplyNetwork(
            baseline_risk_pts=50.0,
            interventions=(
                Intervention("A", cost=1.0, risk_reduction_pts=1.0),
                Intervention("A", cost=2.0, risk_reduction_pts=2.0),
            ),
        )


# --------------------------------------------------------------------------- #
# Stochastic invariants
# --------------------------------------------------------------------------- #


@SLOW
@given(
    reductions=st.lists(
        st.floats(min_value=0.0, max_value=20.0, **finite), min_size=1, max_size=6
    ),
    baseline=st.floats(min_value=1.0, max_value=100.0, **finite),
    rho=st.floats(min_value=0.0, max_value=0.95, **finite),
    seed=st.integers(min_value=0, max_value=2**31 - 1),
)
def test_simulation_output_is_always_a_valid_risk_distribution(
    reductions, baseline, rho, seed
):
    nodes = tuple(f"N{i}" for i in range(len(reductions)))
    result = run_simulation(
        SimulationRequest(
            baseline_risk_pts=baseline,
            risk_reduction_by_node=dict(zip(nodes, reductions)),
            correlation=UniformCorrelation(rho=rho).matrix(nodes),
            node_order=nodes,
            iterations=2_000,
            seed=seed,
            shock_model=LognormalShock(sigma=0.12),
        )
    )
    assert 0.0 <= result.samples.min()
    assert result.samples.max() <= 100.0
    assert result.p10_risk_pts <= result.p50_risk_pts <= result.p90_risk_pts
    assert result.expected_shortfall_90_pts >= result.p90_risk_pts - 1e-9
    assert result.std_dev_pts >= 0.0
    assert result.p50_risk_pts <= baseline + 1e-9
    assert np.isfinite(result.samples).all()


@SLOW
@given(
    values=st.lists(
        st.floats(min_value=-0.99, max_value=0.99, **finite), min_size=1, max_size=15
    )
)
def test_correlation_repair_always_yields_a_usable_correlation_matrix(values):
    """Whatever an analyst types into the grid, the repaired matrix must be
    symmetric, positive semi-definite, and unit-diagonal — a real correlation
    matrix. Otherwise Cholesky either fails or silently rescales the shocks."""
    k = 1
    while k * (k - 1) // 2 < len(values):
        k += 1
    assume(k >= 2)

    matrix = np.eye(k)
    index = 0
    for i in range(k):
        for j in range(i + 1, k):
            if index < len(values):
                matrix[i, j] = matrix[j, i] = values[index]
                index += 1

    repaired, report = repair_to_correlation(matrix)

    np.testing.assert_allclose(np.diag(repaired), 1.0, atol=1e-9)
    np.testing.assert_allclose(repaired, repaired.T, atol=1e-9)
    assert np.linalg.eigvalsh(repaired).min() >= -1e-8
    assert np.abs(repaired).max() <= 1.0 + 1e-9
    assert report.max_diagonal_deviation < 1e-9
    # Cholesky must now succeed, which is the whole point of the repair.
    np.linalg.cholesky(repaired + np.eye(k) * 1e-12)
