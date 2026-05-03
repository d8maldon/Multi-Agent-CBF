"""Verify the trace identity for the joint second moment Q_i.

    tr(Q_i) = E_mu[||Proj_F u_ref||^2]

This is the headline claim of paper §5 / Lemma 5.5. It must hold by linearity
of trace and expectation, regardless of dynamics.
"""

from __future__ import annotations

import numpy as np

from sim import dynamics as dyn


def test_q_trace_identity_static():
    """Static (no-dynamics) check: build Q from outer products, verify tr."""
    rng = np.random.default_rng(7)
    d = 2
    n_samples = 1000

    Q = np.zeros((d, d))
    sq_norm_sum = 0.0
    for _ in range(n_samples):
        # random projector (random active normal or none)
        if rng.random() < 0.3:
            n = rng.standard_normal(d); n /= np.linalg.norm(n)
            P = dyn.freedom_cone_projector([n], d=d)
        else:
            P = np.eye(d)
        u = rng.standard_normal(d)
        Pu = P @ u
        Q += np.outer(Pu, Pu)
        sq_norm_sum += np.dot(Pu, Pu)

    Q_avg = Q / n_samples
    sq_norm_avg = sq_norm_sum / n_samples

    assert np.isclose(np.trace(Q_avg), sq_norm_avg, atol=1e-12), \
        f"tr(Q) = {np.trace(Q_avg)}, expected {sq_norm_avg}"


def test_q_psd():
    """Q_i is symmetric PSD (sum of vv^T outer products)."""
    rng = np.random.default_rng(11)
    Q = np.zeros((2, 2))
    for _ in range(50):
        v = rng.standard_normal(2)
        Q += np.outer(v, v)
    Q /= 50
    assert np.allclose(Q, Q.T, atol=1e-12)
    eigs = np.linalg.eigvalsh(Q)
    assert (eigs >= -1e-12).all()


def test_q_o_d_equivariance():
    """Klein invariance: Q_i transforms as R Q_i R^T under simultaneous rotation R."""
    rng = np.random.default_rng(13)
    d = 2
    # Build a base Q
    Q = np.zeros((d, d))
    samples = []
    for _ in range(50):
        n = rng.standard_normal(d); n /= np.linalg.norm(n)
        u = rng.standard_normal(d)
        P = dyn.freedom_cone_projector([n], d=d)
        Pu = P @ u
        samples.append((n, u, Pu))
        Q += np.outer(Pu, Pu)
    Q /= 50

    # Apply rotation R to all samples and rebuild Q'
    theta = 0.7
    R = np.array([[np.cos(theta), -np.sin(theta)],
                  [np.sin(theta),  np.cos(theta)]])
    Q_rot = np.zeros((d, d))
    for (n, u, _) in samples:
        n_r = R @ n
        u_r = R @ u
        P_r = dyn.freedom_cone_projector([n_r], d=d)
        Pu_r = P_r @ u_r
        Q_rot += np.outer(Pu_r, Pu_r)
    Q_rot /= 50

    # Check Q_rot ≈ R Q R^T
    expected = R @ Q @ R.T
    assert np.allclose(Q_rot, expected, atol=1e-10), \
        f"Klein equivariance violated: ||Q_rot - R Q R^T|| = {np.linalg.norm(Q_rot - expected)}"
