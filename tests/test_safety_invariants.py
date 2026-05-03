"""End-to-end safety invariants: short integrator runs that must never violate
the safety constraint when the safety filter is enabled.

These are slow tests; run with:  pytest tests/test_safety_invariants.py -v
"""

from __future__ import annotations

import numpy as np
import pytest

from sim import paper_params as pp
from sim import integrator


@pytest.mark.slow
def test_no_safety_violation_baseline():
    """AC + CBF with no excitation, short run, must keep h_min > 0."""
    out = integrator.run(
        x0=pp.CROSSSWAP_X0,
        z0=pp.CROSSSWAP_X0.copy(),
        edges=pp.CROSSSWAP_EDGES,
        t_targets_fn=pp.crossswap_targets_oscillating,
        A_e=0.0,
        T_final=2.0,
        log_every=8,
        use_safety_filter=True,
    )
    h_min = float(out["h"].min())
    assert h_min > 0, f"safety filter failed: h_min = {h_min}"


@pytest.mark.slow
def test_no_safety_violation_with_PE():
    """AC + CBF + PE on the freedom cone must NOT degrade safety."""
    out = integrator.run(
        x0=pp.CROSSSWAP_X0,
        z0=pp.CROSSSWAP_X0.copy(),
        edges=pp.CROSSSWAP_EDGES,
        t_targets_fn=pp.crossswap_targets_oscillating,
        A_e=0.10 * pp.U_MAX,
        T_final=2.0,
        log_every=8,
        use_safety_filter=True,
    )
    h_min = float(out["h"].min())
    assert h_min > 0, f"PE injection broke safety: h_min = {h_min}"


@pytest.mark.slow
def test_disabling_safety_filter_does_collide():
    """Sanity: disabling the safety filter MUST produce a collision (h < 0)."""
    out = integrator.run(
        x0=pp.CROSSSWAP_X0,
        z0=pp.CROSSSWAP_X0.copy(),
        edges=pp.CROSSSWAP_EDGES,
        t_targets_fn=pp.crossswap_targets_oscillating,
        A_e=0.0,
        T_final=2.0,
        log_every=8,
        use_safety_filter=False,
    )
    h_min = float(out["h"].min())
    assert h_min < 0, f"expected collision without safety filter, but h_min = {h_min}"


@pytest.mark.slow
def test_theta_hat_stays_in_projection_bounds():
    """theta_hat must stay in [theta_min, theta_max] always."""
    out = integrator.run(
        x0=pp.CROSSSWAP_X0,
        z0=pp.CROSSSWAP_X0.copy(),
        edges=pp.CROSSSWAP_EDGES,
        t_targets_fn=pp.crossswap_targets_oscillating,
        A_e=0.10 * pp.U_MAX,
        T_final=2.0,
        log_every=8,
        use_safety_filter=True,
    )
    theta = out["theta_hat"]
    assert (theta >= pp.THETA_MIN - 1e-10).all()
    assert (theta <= pp.THETA_MAX + 1e-10).all()


@pytest.mark.slow
def test_kalman_bucy_covariance_nonincreasing_under_pe():
    """P_i(t) should be (weakly) non-increasing under deterministic Q^KB = 0."""
    out = integrator.run(
        x0=pp.CROSSSWAP_X0,
        z0=pp.CROSSSWAP_X0.copy(),
        edges=pp.CROSSSWAP_EDGES,
        t_targets_fn=pp.crossswap_targets_oscillating,
        A_e=0.10 * pp.U_MAX,
        T_final=2.0,
        log_every=8,
        use_safety_filter=True,
    )
    P = out["P"]
    # Allow tiny numerical wiggle
    diffs = np.diff(P, axis=0)
    assert (diffs <= 1e-9).all(), f"P_i increased at some step: max diff {diffs.max()}"
