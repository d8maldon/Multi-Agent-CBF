"""Dynamics-level invariants for v17 (council-vetted Passes 19-30).

Each function in sim.dynamics has a contract; these tests pin those contracts
numerically. v17 specifics:
- State is complex (r, v_a) in C^2 per agent (not real R^d).
- Adaptive law uses complex regressor phi_i = i v_{a,i} u_2^ref.
- Excitation signal is SCALAR (not vector — the v17 control is scalar real
  turn-rate u_2 in R).
- HOCBF residual b_ij^(0) = 2|v|^2 + 2(a1+a2)Re(...) + a1*a2*h (factor-of-2
  corrected per Pass 19/20/21).
- δ_{ij}(t) is per-pair via §3.1.2 residual aggregation.
"""

from __future__ import annotations

import numpy as np

from sim import paper_params as pp
from sim import dynamics as dyn


# ---------------------------------------------------------------------------
# CBF / HOCBF basic shape
# ---------------------------------------------------------------------------

def test_cbf_h_at_boundary():
    """h_{ij} = 0 when |r_i - r_j| = r_safe (v17 complex form)."""
    r_i = 0.0 + 0.0j
    r_j = pp.R_SAFE + 0.0j
    assert np.isclose(dyn.cbf_h(r_i, r_j), 0.0)


def test_cbf_h_dot_finite_difference():
    """dot h_{ij} matches finite-difference of h along trajectories."""
    r_i, r_j = 0.0 + 0.0j, 1.0 + 0.0j
    v_i, v_j = 0.5j, -0.5j           # closing perpendicular components only
    eps = 1e-7
    r_i_dt = r_i + eps * v_i
    r_j_dt = r_j + eps * v_j
    h_dot_fd = (dyn.cbf_h(r_i_dt, r_j_dt) - dyn.cbf_h(r_i, r_j)) / eps
    h_dot_analytic = dyn.cbf_h_dot(r_i, r_j, v_i, v_j)
    assert np.isclose(h_dot_fd, h_dot_analytic, atol=1e-5)


def test_hocbf_residual_factor_of_two():
    """Verify Pass 19/20/21 factor-of-2 correction:
    b_ij^(0) = 2|v|^2 + 2(a1+a2)Re(...) + a1*a2*h.

    Test config: parallel velocities, |v_i - v_j| = 0; only the h-term contributes.
    """
    r_i, r_j = 0.0 + 0.0j, 0.5 + 0.0j
    v_i, v_j = 1.0 + 0.0j, 1.0 + 0.0j
    h_val = dyn.cbf_h(r_i, r_j)        # = 0.25 - 0.16 = 0.09
    b0 = dyn.hocbf_residual(r_i, r_j, v_i, v_j, h_val)
    # |v_i - v_j|^2 = 0; (r_i - r_j) conj(v_i - v_j) = 0
    # b0 = 0 + 0 + ALPHA_1 * ALPHA_2 * h_val = 5*5*0.09 = 2.25
    expected = pp.ALPHA_1 * pp.ALPHA_2 * h_val
    assert np.isclose(b0, expected), f"got b0={b0}, expected {expected}"


def test_hocbf_jacobian_self_zero_at_locus():
    """a_ii = 2 Im((r_i - r_j) conj(v_i)) = 0 at the head-on / tail-on locus.

    Test the §8.1 head-on counter-example: r_1 = -1, r_2 = +1, v_1 = +1, v_2 = -1.
    """
    r_1, r_2 = -1.0 + 0.0j, 1.0 + 0.0j
    v_1 = 1.0 + 0.0j                   # head-on
    a_11 = dyn.hocbf_jacobian_self(r_1, r_2, v_1)
    assert np.isclose(a_11, 0.0), \
        f"head-on locus should give a_11 = 0, got {a_11}"


def test_hocbf_jacobian_other_signs_consistent():
    """a_{ij,j} = -2 Im((r_i - r_j) conj(v_j)). Sign opposite of agent j's
    self-Jacobian when computed in agent i's frame."""
    r_i, r_j = 0.0 + 0.0j, 1.0 + 0.5j
    v_j = 0.0 + 1.0j                    # heading +y
    a_ij = dyn.hocbf_jacobian_other(r_i, r_j, v_j)
    # a_ij = -2 Im((-1 - 0.5j)(0 - 1j)) = -2 Im(1j - 0.5) = -2 * 1 = -2
    assert np.isclose(a_ij, -2.0)


# ---------------------------------------------------------------------------
# Adaptive law (complex regressor)
# ---------------------------------------------------------------------------

def test_v17_adaptive_law_zero_at_zero_velocity_error():
    """When v_a = v_ref (tilde_v = 0), dot theta_hat = 0 (the adaptive law's
    score function is Re(conj(phi) tilde_v))."""
    N = 4
    theta_hat = 0.5 * (pp.THETA_MIN + pp.THETA_MAX) * np.ones(N)
    r = np.array([0.0 + 0.0j, 1.0, 1.0 + 1.0j, 1.0j])
    r_ref = r.copy()
    v_a = np.array([1.0 + 0.0j, 0.0 + 1.0j, -1.0 + 0.0j, 0.0 - 1.0j])
    v_ref = v_a.copy()                 # tilde_v = 0
    u_2_ref = np.ones(N)
    rates = dyn.adaptive_law_rate(theta_hat, r, r_ref, v_a, v_ref, u_2_ref)
    assert np.allclose(rates, 0.0)


def test_v17_adaptive_law_clamps_at_projection_lower_bound():
    """At theta_hat = theta_min with negative raw rate, the projection clamps."""
    theta_hat = np.array([pp.THETA_MIN])
    r = np.array([0.0 + 0.0j])
    r_ref = np.array([0.0 + 0.0j])
    v_a = np.array([1.0 + 0.0j])
    v_ref = np.array([1.0 + 0.5j])     # tilde_v = -0.5j
    u_2_ref = np.array([1.0])
    # phi = i * v_a * u_2_ref = i; conj(phi) tilde_v = -i * (-0.5j) = -0.5
    # Re(conj(phi) tilde_v) = -0.5. raw = -gamma/m^2 * (-0.5) = +ve
    # That's positive, so doesn't trigger lower-bound clamp. Flip sign:
    v_ref = np.array([1.0 - 0.5j])     # tilde_v = +0.5j
    # Re(conj(phi) tilde_v) = Re(-i * 0.5j) = +0.5. raw = -gamma/m^2 * 0.5 = -ve.
    rates = dyn.adaptive_law_rate(theta_hat, r, r_ref, v_a, v_ref, u_2_ref)
    assert rates[0] >= 0.0, \
        f"projection lower-bound clamp failed: rate = {rates[0]}"


# ---------------------------------------------------------------------------
# Kalman-Bucy filter
# ---------------------------------------------------------------------------

def test_v17_kalman_bucy_riccati_nonincreasing():
    """dP/dt <= 0 for all P, v_a, u_2_ref (deterministic Riccati Q^KB = 0)."""
    rng = np.random.default_rng(0)
    for _ in range(20):
        N = rng.integers(1, 8)
        P = rng.uniform(0.0, 5.0, size=N)
        # Random complex velocities of unit magnitude
        psi = rng.uniform(0, 2 * np.pi, size=N)
        v_a = pp.V_0 * np.exp(1j * psi)
        u_2_ref = rng.uniform(-pp.PSI_DOT_MAX, pp.PSI_DOT_MAX, size=N)
        rates = dyn.kalman_bucy_riccati(P, v_a, u_2_ref)
        assert (rates <= 1e-12).all(), \
            f"KB Riccati not non-increasing: rates = {rates}"


# ---------------------------------------------------------------------------
# Excitation signal (scalar in v17)
# ---------------------------------------------------------------------------

def test_v17_excitation_signal_is_scalar():
    """v17 excitation signal returns a scalar real (the control is scalar)."""
    omegas = np.array([2 * np.pi, 4 * np.pi])
    phases = np.array([0.0, 0.0])
    e = dyn.excitation_signal(0.0, omegas, phases, 1.5)
    assert isinstance(e, float) or (hasattr(e, "shape") and e.shape == ()), \
        f"excitation_signal should return scalar, got {type(e).__name__} with shape {getattr(e, 'shape', None)}"


def test_v17_excitation_amplitude_bounded():
    """|e_pe(t)| <= A_e (sin amplitudes; the (sin + sin)/2 form is bounded by A_e)."""
    omegas = np.array([2 * np.pi, 4 * np.pi])
    phases = np.array([0.0, 0.0])
    A_e = 1.5
    for t in np.linspace(0, 10, 200):
        e = dyn.excitation_signal(t, omegas, phases, A_e)
        assert abs(e) <= A_e + 1e-10


# ---------------------------------------------------------------------------
# CBF tightening (paper §3.1.2 residual aggregation)
# ---------------------------------------------------------------------------

def test_v17_cbf_tightening_vanishes_as_P_decays():
    """δ_{ij}(t) → ζ_0 baseline as P_i, P_j → 0 (Anderson 1985 PE-decay)."""
    P_i, P_j = 1e-9, 1e-9
    a_ii, a_ij = 1.0, -1.0
    theta_i, theta_j = 1.5, 1.5
    delta = dyn.cbf_tightening_delta(P_i, P_j, a_ii, a_ij, theta_i, theta_j,
                                       tau_d=0.0, zeta_0=1e-3)
    # With P -> 0, eps_1 -> 0 and eps_2 -> 0; only zeta_0 baseline remains
    # (modulo small numerical residuals from sqrt(1e-9))
    assert delta < 1e-2, \
        f"tightening doesn't vanish at P -> 0: delta = {delta}"


def test_v17_cbf_tightening_grows_with_P():
    """δ_{ij}(t) increases monotonically with P_i, P_j."""
    a_ii, a_ij = 1.0, -1.0
    theta_i, theta_j = 1.5, 1.5
    deltas = []
    for P_val in [0.001, 0.01, 0.1, 1.0]:
        d = dyn.cbf_tightening_delta(P_val, P_val, a_ii, a_ij,
                                       theta_i, theta_j, tau_d=0.0)
        deltas.append(d)
    diffs = np.diff(deltas)
    assert (diffs > 0).all(), \
        f"tightening not monotonic in P: deltas = {deltas}"


def test_v17_cbf_tightening_includes_latency_residual():
    """For tau_d > 0, the latency term R3 adds positive contribution to δ_{ij}."""
    P_i, P_j = 0.1, 0.1
    a_ii, a_ij = 1.0, -1.0
    theta_i, theta_j = 1.5, 1.5
    d_no_delay = dyn.cbf_tightening_delta(P_i, P_j, a_ii, a_ij,
                                            theta_i, theta_j, tau_d=0.0)
    d_with_delay = dyn.cbf_tightening_delta(P_i, P_j, a_ii, a_ij,
                                              theta_i, theta_j, tau_d=0.005)
    assert d_with_delay > d_no_delay, \
        f"latency residual didn't add: no-delay {d_no_delay}, delay {d_with_delay}"


# ---------------------------------------------------------------------------
# Hysteresis active set (paper §3.1.3 K-P play operator)
# ---------------------------------------------------------------------------

def test_v17_hysteresis_engagement_threshold():
    """Hysteresis engages when c_{ij} <= eps. Construct a config where
    the gauge-fixed c_{ij} value is well below eps and verify activation."""
    # Two agents very close, head-on closing; c_{ij} should be very negative.
    r = np.array([0.0 + 0.0j, 0.5 + 0.0j])
    v_a = np.array([1.0 + 0.0j, -1.0 + 0.0j])
    theta_hat = np.array([1.5, 1.5])
    u_2_AC = np.array([0.0, 0.0])
    edges = ((0, 1),)
    pair_active_in = {frozenset({0, 1}): False}
    new_active = dyn.update_hysteresis(r, v_a, theta_hat, u_2_AC,
                                         pair_active_in, edges)
    # In this geometry, c_{ij} is dominated by the negative b_{ij}^(0) term
    # (since dot h is very negative as agents close head-on). It should be
    # well below eps_hyst, triggering engagement.
    assert new_active[frozenset({0, 1})] is True, \
        "hysteresis didn't engage at extreme head-on closing config"


def test_v17_hysteresis_disengagement_threshold():
    """Hysteresis disengages when c_{ij} >= 2 eps. Construct a config where
    pairs are far apart and c_{ij} >> 2 eps; the previously-active pair should
    disengage."""
    r = np.array([0.0 + 0.0j, 100.0 + 0.0j])      # far apart
    v_a = np.array([1.0 + 0.0j, 0.0 - 1.0j])
    theta_hat = np.array([1.5, 1.5])
    u_2_AC = np.array([0.0, 0.0])
    edges = ((0, 1),)
    pair_active_in = {frozenset({0, 1}): True}     # currently engaged
    new_active = dyn.update_hysteresis(r, v_a, theta_hat, u_2_AC,
                                         pair_active_in, edges)
    assert new_active[frozenset({0, 1})] is False, \
        "hysteresis didn't disengage at far-apart config"
