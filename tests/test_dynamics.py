"""Dynamics-level invariants: each function in sim.dynamics has a contract.

These tests pin those contracts numerically.
"""

from __future__ import annotations

import numpy as np

from sim import paper_params as pp
from sim import dynamics as dyn


def test_freedom_cone_projector_idempotent():
    """Proj_F is an orthogonal projector: P^2 = P, P^T = P."""
    rng = np.random.default_rng(0)
    for _ in range(10):
        # random unit normals (1 or 2 active)
        k = rng.integers(0, 3)
        normals = [rng.standard_normal(2) for _ in range(k)]
        normals = [n / np.linalg.norm(n) for n in normals]
        P = dyn.freedom_cone_projector(normals, d=2)
        assert np.allclose(P, P.T, atol=1e-10)
        assert np.allclose(P @ P, P, atol=1e-9)


def test_freedom_cone_kills_active_normals():
    """For each active normal n, Proj_F @ n == 0."""
    rng = np.random.default_rng(1)
    n = rng.standard_normal(2); n /= np.linalg.norm(n)
    P = dyn.freedom_cone_projector([n], d=2)
    assert np.allclose(P @ n, 0.0, atol=1e-10)


def test_freedom_cone_no_active_is_identity():
    P = dyn.freedom_cone_projector([], d=3)
    assert np.allclose(P, np.eye(3))


def test_cbf_h_at_boundary():
    """h_ij = 0 when ||x_i - x_j|| = r_safe."""
    x_i = np.array([0.0, 0.0])
    x_j = np.array([pp.R_SAFE, 0.0])
    assert np.isclose(dyn.cbf_h(x_i, x_j), 0.0)


def test_adaptive_law_zero_at_zero_error():
    """e = 0 implies dot theta_hat = 0."""
    N, d = 4, 2
    theta_hat = 0.5 * (pp.THETA_MIN + pp.THETA_MAX) * np.ones(N)
    x = np.zeros((N, d))
    z = np.zeros((N, d))                              # e = 0
    u_ref = np.ones((N, d))
    rates = dyn.adaptive_law_rate(theta_hat, x, z, u_ref)
    assert np.allclose(rates, 0.0)


def test_adaptive_law_clamps_at_projection_boundary():
    """At theta_hat = theta_min with raw rate < 0, output is clamped to 0."""
    theta_hat = np.array([pp.THETA_MIN])
    x = np.array([[1.0, 0.0]])                        # x ahead of z along u^ref
    z = np.array([[0.0, 0.0]])
    u_ref = np.array([[1.0, 0.0]])                    # would push theta_hat down
    rates = dyn.adaptive_law_rate(theta_hat, x, z, u_ref)
    assert rates[0] >= 0.0  # cannot push below theta_min


def test_kalman_bucy_riccati_decreasing_under_pe():
    """dP/dt <= 0 always (deterministic Q^KB = 0)."""
    P = np.array([1.0, 1.0])
    u_ref = np.array([[2.0, 0.0], [0.0, 2.0]])
    rates = dyn.kalman_bucy_riccati(P, u_ref)
    assert (rates <= 0).all()


def test_excitation_signal_amplitude_bounded():
    """||e_pe(t)||_inf <= A_e for all t (sin amplitude)."""
    omegas = np.array([2 * np.pi, 4 * np.pi])
    phases = np.array([0.0, 0.0])
    A_e = 1.5
    for t in np.linspace(0, 10, 200):
        e = dyn.excitation_signal(t, omegas, phases, A_e)
        assert np.max(np.abs(e)) <= A_e + 1e-10
