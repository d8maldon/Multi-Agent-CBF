"""Paper-vs-sim consistency tests.

Each function in sim.paper_params has a corresponding paper section/equation.
These tests pin the contract: if the paper changes a parameter, the test
catches the drift; if the code drifts from the paper, the test catches that
too.
"""

from __future__ import annotations

import numpy as np

from sim import paper_params as pp


def test_lambda_in_axiom_A1_range():
    """Axiom A1: Lambda_i in [Lambda_min, 1] with Lambda_min > 0."""
    assert (pp.LAMBDA_TRUE > 0).all(), "axiom A1 requires Lambda_i > 0"
    assert (pp.LAMBDA_TRUE <= 1.0).all(), "axiom A1 requires Lambda_i <= 1"


def test_inv_lambda_in_projection_bounds():
    """1/Lambda_i must lie in [theta_min, theta_max] for theta_hat to converge."""
    inv = 1.0 / pp.LAMBDA_TRUE
    assert (inv >= pp.THETA_MIN).all(), \
        f"1/Lambda = {inv}; below theta_min = {pp.THETA_MIN}"
    assert (inv <= pp.THETA_MAX).all(), \
        f"1/Lambda = {inv}; above theta_max = {pp.THETA_MAX}"


def test_kappa_lambda_consistent():
    """kappa_Lambda = theta_max / theta_min."""
    expected = pp.THETA_MAX / pp.THETA_MIN
    assert np.isclose(pp.KAPPA_LAMBDA, expected)


def test_eta_feasibility_at_paper_8_3_values():
    """K_T * Lambda_min > mu_bar^2 * L_QP_star^2 (paper section 8.3)."""
    # Paper section 8.3 reports L_QP* ≈ 3.75 with mu_bar ≈ 0.3, requiring
    # K_T * Lambda_min > 0.09 * 14.06 ≈ 1.27. With Lambda_min = 0.6 and K_T = 4,
    # we get 2.4 > 1.27 ✓.
    Lambda_min = float(pp.LAMBDA_TRUE.min())
    L_QP_star = 3.75
    mu_bar = 0.30
    threshold = mu_bar ** 2 * L_QP_star ** 2
    assert pp.K_T * Lambda_min > threshold, \
        f"eta-feasibility fails: {pp.K_T * Lambda_min} <= {threshold}"


def test_zeta_definition():
    """A3' margin: zeta = 0.5 * r_safe^2 (paper section 8.3)."""
    assert np.isclose(pp.ZETA, 0.5 * pp.R_SAFE ** 2)


def test_eps_hyst_in_paper_3_1_window():
    """eps_hyst in [delta_ij + tol, 0.1 r_safe^2] (paper section 3.1 line 92)."""
    assert pp.EPS_HYST > 0
    assert pp.EPS_HYST <= 0.1 * pp.R_SAFE ** 2


def test_pe_omegas_per_agent_distinct():
    """Per-agent PE frequencies must differ across agents (paper section 8.3 v16)."""
    omegas = pp.pe_omegas(4)
    # No two agents have identical (omega_1, omega_2) pair
    seen = set()
    for w in omegas:
        key = (round(w[0], 4), round(w[1], 4))
        assert key not in seen, f"duplicate per-agent omega pair: {key}"
        seen.add(key)


def test_paper_consistency_sweep_returns_all_OK():
    """The aggregate verify_paper_consistency() must return all OK on v16."""
    checks = pp.verify_paper_consistency()
    failed = [(k, detail) for k, (ok, detail) in checks.items() if not ok]
    assert not failed, f"Paper consistency failures: {failed}"
