"""Paper-vs-sim consistency tests, v17 (council-vetted Passes 19-30).

Each function in sim.paper_params has a corresponding paper section/equation.
These tests pin the contract: if the paper changes a parameter, the test
catches the drift; if the code drifts from the paper, the test catches that
too.
"""

from __future__ import annotations

import numpy as np

from sim import paper_params as pp


def test_lambda_in_axiom_A1_range():
    """Axiom (A1) v17: lambda_i in [lambda_min, 1] with lambda_min > 0
    (LOE on turn-rate channel)."""
    assert (pp.LAMBDA_TRUE > 0).all(), "axiom (A1) requires lambda_i > 0"
    assert (pp.LAMBDA_TRUE <= 1.0).all(), "axiom (A1) requires lambda_i <= 1"


def test_inv_lambda_in_projection_bounds():
    """1/lambda_i must lie in [theta_min, theta_max] for theta_hat to converge
    (axiom (A1) projection-compatibility)."""
    inv = 1.0 / pp.LAMBDA_TRUE
    assert (inv >= pp.THETA_MIN).all(), \
        f"1/lambda = {inv}; below theta_min = {pp.THETA_MIN}"
    assert (inv <= pp.THETA_MAX).all(), \
        f"1/lambda = {inv}; above theta_max = {pp.THETA_MAX}"


def test_kappa_lambda_consistent():
    """kappa_lambda = theta_max / theta_min (axiom (A1))."""
    expected = pp.THETA_MAX / pp.THETA_MIN
    assert np.isclose(pp.KAPPA_LAMBDA, expected)


def test_v17_eta_feasibility_at_8_3_parameters():
    """v17 §4.3 gain condition: K_T * lambda_min > mu_bar^2 * L_QP*^2.

    With v17 L_QP* = (1 + kappa_lambda) / eta_a_practical and
    eta_a_practical ~ 1.6 (paper §8.3 estimate from min |a_ii| on closed loop):
        L_QP* ~ 3 / 1.6 ~ 1.88
        threshold ~ 0.3^2 * 1.88^2 ~ 0.32
    With K_T = 4 and lambda_min = 0.6: K_T * lambda_min = 2.4 > 0.32 (margin 7.5x).
    """
    Lambda_min = float(pp.LAMBDA_TRUE.min())
    eta_a_practical = 1.6        # paper §8.3 / §3.1.1
    L_QP_star = (1.0 + pp.KAPPA_LAMBDA) / eta_a_practical
    mu_bar = 0.30
    threshold = mu_bar ** 2 * L_QP_star ** 2
    margin = (pp.K_T * Lambda_min) / threshold
    assert pp.K_T * Lambda_min > threshold, \
        f"v17 eta-feasibility fails: {pp.K_T * Lambda_min} <= {threshold}"
    assert margin >= 5.0, \
        f"v17 eta-feasibility margin {margin:.2f}x is below 5x (paper claims 7.5x)"


def test_zeta_definition():
    """(A3'') initial-condition margin: zeta = 0.5 * r_safe^2 (paper §8.3)."""
    assert np.isclose(pp.ZETA, 0.5 * pp.R_SAFE ** 2)


def test_eps_hyst_in_paper_3_1_window():
    """eps_hyst in (delta_ij + tol, 0.1 r_safe^2] (paper §3.1.3)."""
    assert pp.EPS_HYST > 0
    assert pp.EPS_HYST <= 0.1 * pp.R_SAFE ** 2


def test_pe_omegas_per_agent_distinct():
    """Per-agent PE frequencies must differ across agents (paper §8.3)."""
    omegas = pp.pe_omegas(4)
    seen = set()
    for w in omegas:
        key = (round(w[0], 4), round(w[1], 4))
        assert key not in seen, f"duplicate per-agent omega pair: {key}"
        seen.add(key)


def test_v17_dubins_constants_positive():
    """V_0 (cruise speed) and psi_dot_max (max turn rate) must be positive
    for the constant-speed Dubins simplification (paper §2.1)."""
    assert pp.V_0 > 0, f"V_0 = {pp.V_0}; must be > 0 for constant-speed Dubins"
    assert pp.PSI_DOT_MAX > 0, \
        f"psi_dot_max = {pp.PSI_DOT_MAX}; must be > 0 for the Dubins turn limit"


def test_v17_hocbf_alphas_positive():
    """alpha_1, alpha_2 > 0 are linear class-K gains (paper §3.1)."""
    assert pp.ALPHA_1 > 0
    assert pp.ALPHA_2 > 0


def test_v17_crossswap_geometry():
    """CROSSSWAP_R0 places agents at the four corners of (-3,-3), (3,3) box
    (paper §8.2)."""
    r0 = pp.CROSSSWAP_R0
    assert r0.shape == (4,), f"expected 4 agents, got {r0.shape}"
    assert r0.dtype == complex, f"expected complex, got {r0.dtype}"
    # All corners at distance 3*sqrt(2) from origin
    norms = np.abs(r0)
    assert np.allclose(norms, 3.0 * np.sqrt(2)), \
        f"expected |r_0| = 3*sqrt(2), got {norms}"


def test_v17_crossswap_v0_constant_speed():
    """crossswap_v0() returns initial velocities with |v_a,i| = V_0 (paper §2.1
    constant-speed simplification)."""
    v0 = pp.crossswap_v0()
    assert v0.shape == (4,), f"expected 4 velocities, got {v0.shape}"
    assert np.allclose(np.abs(v0), pp.V_0), \
        f"|v_a,i(0)| = {np.abs(v0)}, expected {pp.V_0}"


def test_paper_consistency_sweep_returns_all_OK():
    """The aggregate verify_paper_consistency() must return all OK on v17."""
    checks = pp.verify_paper_consistency()
    failed = [(k, detail) for k, (ok, detail) in checks.items() if not ok]
    assert not failed, f"Paper consistency failures: {failed}"
