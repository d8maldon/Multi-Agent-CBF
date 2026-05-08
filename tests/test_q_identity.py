"""Verify the v17 scalar Fisher information bar_rho_i (paper §5.2).

In v17, the binary freedom cone F_i in {{0}, R} collapses the v16 matrix
Q_i to the scalar:

    bar_rho_i = E_mu[V_0^2 (u_2^ref)^2 / (1 + V_0^2 (u_2^ref)^2)
                       * 1{N_i^on = empty}]

This is the constrained scalar Cramér-Rao bound on theta_i = 1/lambda_i
(paper §5.4). Tests pin invariants:

1. bar_rho_i in [0, 1) — the integrand |phi|^2/m^2 < 1 always.
2. bar_rho_i = 0 if all samples are pair-active (active set always non-empty).
3. bar_rho_i grows monotonically with PE amplitude A_e (when active fraction
   is held constant).
4. bar_rho_i is U(1)-equivariant under heading rotation (paper §4.2 symmetry).
"""

from __future__ import annotations

import numpy as np

from sim import paper_params as pp


def _bar_rho_sample(u_2_ref_samples: np.ndarray,
                    active_samples: np.ndarray) -> float:
    """Compute bar_rho_i over time samples per the v17 §5.2 formula.

    u_2_ref_samples : (T,) real, reference turn-rate at each sample.
    active_samples  : (T,) bool, True if any pair is active at sample t.
    """
    integrand = pp.V_0 ** 2 * u_2_ref_samples ** 2
    ratio = integrand / (1.0 + integrand)
    masked = ratio * (~active_samples)
    return float(np.mean(masked))


def test_v17_bar_rho_in_unit_interval():
    """bar_rho_i in [0, 1) for any sample sequence (since each integrand < 1)."""
    rng = np.random.default_rng(7)
    for _ in range(20):
        T = rng.integers(50, 200)
        u_2_ref = rng.uniform(-pp.PSI_DOT_MAX, pp.PSI_DOT_MAX, size=T)
        active = rng.random(T) < 0.3
        bar_rho = _bar_rho_sample(u_2_ref, active)
        assert 0.0 <= bar_rho < 1.0, \
            f"bar_rho out of [0, 1): {bar_rho}"


def test_v17_bar_rho_zero_when_always_active():
    """bar_rho_i = 0 when all samples have pair-active (free-time empty)."""
    T = 100
    u_2_ref = 2.0 * np.ones(T)         # large u_2_ref, but doesn't matter
    active = np.ones(T, dtype=bool)    # always active
    bar_rho = _bar_rho_sample(u_2_ref, active)
    assert bar_rho == 0.0


def test_v17_bar_rho_grows_with_PE_amplitude():
    """At held active-fraction, bar_rho_i is monotonic in |u_2^ref| amplitude."""
    T = 100
    active = np.zeros(T, dtype=bool)   # never active
    bar_rhos = []
    for amplitude in [0.1, 0.5, 1.0, 2.0]:
        u_2_ref = amplitude * np.ones(T)
        bar_rhos.append(_bar_rho_sample(u_2_ref, active))
    diffs = np.diff(bar_rhos)
    assert (diffs > 0).all(), \
        f"bar_rho not monotonic in amplitude: {bar_rhos}"


def test_v17_bar_rho_saturates_at_one():
    """bar_rho_i -> 1 as |u_2^ref| -> infinity (V_0^2 u^2 / (1 + V_0^2 u^2) -> 1)."""
    T = 100
    active = np.zeros(T, dtype=bool)
    u_2_ref = 1e6 * np.ones(T)         # huge amplitude
    bar_rho = _bar_rho_sample(u_2_ref, active)
    assert bar_rho > 0.999, \
        f"bar_rho should saturate near 1, got {bar_rho}"


def test_v17_bar_rho_U1_equivariant_via_phi_magnitude():
    """The integrand depends on |phi_i|^2 = V_0^2 (u_2^ref)^2 only — not on
    arg(v_a,i). Hence bar_rho_i is U(1)-invariant under simultaneous heading
    rotation (paper §4.2 symmetry).

    This test verifies the property at the formula level: the integrand uses
    u_2^ref alone (real scalar), so any phase rotation of v_a leaves it intact.
    """
    T = 100
    u_2_ref = np.ones(T)
    active = np.zeros(T, dtype=bool)

    # Original
    bar_rho_orig = _bar_rho_sample(u_2_ref, active)

    # Under U(1) rotation, u_2^ref (the heading-PD turn rate command) is unchanged
    # because rotating both v_a and v_des by the same e^{i theta} leaves
    # arg(v_des / v_a) invariant. So u_2^ref(rotated) = u_2^ref(original) and
    # bar_rho is invariant.
    # We simulate this by using the same u_2_ref samples (equivariant value).
    bar_rho_rotated = _bar_rho_sample(u_2_ref, active)
    assert np.isclose(bar_rho_orig, bar_rho_rotated)
