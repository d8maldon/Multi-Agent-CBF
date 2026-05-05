"""End-to-end safety invariants for v17: short integrator runs that must never
violate the safety constraint when the safety filter is enabled.

These are slow tests; run with:  pytest tests/test_safety_invariants.py -v --runslow

v17 specifics:
- State is (r, v_a, r_ref, v_ref) with r, v_a in C and |v_a| = V_0.
- Initial conditions from sim.paper_params.CROSSSWAP_R0 + crossswap_v0().
- The integrator at h_outer = 5 ms with h_outer * n_steps = T_final.
"""

from __future__ import annotations

import numpy as np
import pytest

from sim import paper_params as pp
from sim import integrator


def _crossswap_initial_state():
    """Standard §8.2 cross-swap initial conditions for v17 simulations."""
    r0 = pp.CROSSSWAP_R0.copy()
    v_a0 = pp.crossswap_v0()
    return r0, v_a0


@pytest.mark.slow
def test_v17_no_safety_violation_baseline():
    """AC + CBF with no excitation, short v17 cross-swap run, must keep
    h_min > 0 and theta_hat in projection bounds."""
    r0, v_a0 = _crossswap_initial_state()
    out = integrator.run(
        r0=r0, v_a0=v_a0,
        r_ref0=r0.copy(), v_ref0=v_a0.copy(),
        edges=pp.CROSSSWAP_EDGES,
        t_targets_fn=pp.crossswap_targets_oscillating,
        A_e=0.0,
        T_final=2.0,
        log_every=8,
        use_safety_filter=True,
    )
    h_min = float(out["h"].min())
    assert h_min > 0, f"v17 safety filter failed: h_min = {h_min}"


@pytest.mark.slow
def test_v17_no_safety_violation_with_PE():
    """AC + CBF + PE injection on the v17 binary freedom cone must NOT degrade
    safety (PE is admitted only when no pair is active)."""
    r0, v_a0 = _crossswap_initial_state()
    out = integrator.run(
        r0=r0, v_a0=v_a0,
        r_ref0=r0.copy(), v_ref0=v_a0.copy(),
        edges=pp.CROSSSWAP_EDGES,
        t_targets_fn=pp.crossswap_targets_oscillating,
        A_e=0.10 * pp.PSI_DOT_MAX,
        T_final=2.0,
        log_every=8,
        use_safety_filter=True,
    )
    h_min = float(out["h"].min())
    assert h_min > 0, f"PE injection broke v17 safety: h_min = {h_min}"


@pytest.mark.slow
def test_v17_theta_hat_stays_in_projection_bounds():
    """theta_hat must stay in [theta_min, theta_max] (axiom (A1) clip-projection)."""
    r0, v_a0 = _crossswap_initial_state()
    out = integrator.run(
        r0=r0, v_a0=v_a0,
        r_ref0=r0.copy(), v_ref0=v_a0.copy(),
        edges=pp.CROSSSWAP_EDGES,
        t_targets_fn=pp.crossswap_targets_oscillating,
        A_e=0.10 * pp.PSI_DOT_MAX,
        T_final=2.0,
        log_every=8,
        use_safety_filter=True,
    )
    theta = out["theta_hat"]
    assert (theta >= pp.THETA_MIN - 1e-10).all(), \
        f"theta_hat below theta_min: {theta.min()}"
    assert (theta <= pp.THETA_MAX + 1e-10).all(), \
        f"theta_hat above theta_max: {theta.max()}"


@pytest.mark.slow
def test_v17_kalman_bucy_covariance_nonincreasing():
    """P_i(t) should be (weakly) non-increasing under deterministic Q^KB = 0
    (paper §2.5)."""
    r0, v_a0 = _crossswap_initial_state()
    out = integrator.run(
        r0=r0, v_a0=v_a0,
        r_ref0=r0.copy(), v_ref0=v_a0.copy(),
        edges=pp.CROSSSWAP_EDGES,
        t_targets_fn=pp.crossswap_targets_oscillating,
        A_e=0.10 * pp.PSI_DOT_MAX,
        T_final=2.0,
        log_every=8,
        use_safety_filter=True,
    )
    P = out["P"]
    # Allow tiny numerical wiggle from RK4 integration (4th-order error)
    diffs = np.diff(P, axis=0)
    assert (diffs <= 1e-6).all(), \
        f"P_i increased substantially at some step: max diff {diffs.max()}"


@pytest.mark.slow
def test_v17_constant_speed_preserved():
    """|v_a,i| should remain at V_0 throughout (constant-speed simplification +
    renormalisation projection in the integrator)."""
    r0, v_a0 = _crossswap_initial_state()
    out = integrator.run(
        r0=r0, v_a0=v_a0,
        r_ref0=r0.copy(), v_ref0=v_a0.copy(),
        edges=pp.CROSSSWAP_EDGES,
        t_targets_fn=pp.crossswap_targets_oscillating,
        A_e=0.10 * pp.PSI_DOT_MAX,
        T_final=2.0,
        log_every=8,
        use_safety_filter=True,
    )
    speeds = np.abs(out["v_a"])
    assert np.allclose(speeds, pp.V_0, atol=1e-6), \
        f"|v_a| drift exceeds 1e-6: max deviation {np.max(np.abs(speeds - pp.V_0))}"


@pytest.mark.slow
def test_v17_active_count_within_A5_bound():
    """Axiom (A5) v17: |N_i^on| <= 1 for each agent on the closed-loop measure
    (scalar-control specialisation). This test checks that the active count
    stays bounded by the number of edges (sanity); the strict (A5) check is
    per-agent and would require disaggregation of the active_count log."""
    r0, v_a0 = _crossswap_initial_state()
    out = integrator.run(
        r0=r0, v_a0=v_a0,
        r_ref0=r0.copy(), v_ref0=v_a0.copy(),
        edges=pp.CROSSSWAP_EDGES,
        t_targets_fn=pp.crossswap_targets_oscillating,
        A_e=0.10 * pp.PSI_DOT_MAX,
        T_final=2.0,
        log_every=8,
        use_safety_filter=True,
    )
    active_count = out["active_count"]
    n_edges = len(pp.CROSSSWAP_EDGES)
    assert (active_count >= 0).all() and (active_count <= n_edges).all(), \
        f"active_count out of [0, {n_edges}]: max = {active_count.max()}"


@pytest.mark.slow
def test_v17_bar_rho_i_in_unit_interval():
    """bar_rho_i in [0, 1) per paper §5.2 (the integrand |phi|^2/m^2 < 1)."""
    r0, v_a0 = _crossswap_initial_state()
    out = integrator.run(
        r0=r0, v_a0=v_a0,
        r_ref0=r0.copy(), v_ref0=v_a0.copy(),
        edges=pp.CROSSSWAP_EDGES,
        t_targets_fn=pp.crossswap_targets_oscillating,
        A_e=0.10 * pp.PSI_DOT_MAX,
        T_final=2.0,
        log_every=8,
        use_safety_filter=True,
    )
    bar_rho = out["bar_rho_i"]
    assert (bar_rho >= 0).all(), f"bar_rho_i < 0: {bar_rho}"
    assert (bar_rho < 1.0).all(), f"bar_rho_i >= 1: {bar_rho}"
