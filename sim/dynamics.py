"""Plant + adaptive law + Kalman-Bucy auxiliary, line-by-line from §2 of v14.

Each function is annotated with the paper section / equation it implements.
"""

from __future__ import annotations

import numpy as np

from . import paper_params as pp


def neighbours(i: int, edges: tuple) -> list:
    """Return list of j such that {i,j} is an edge of the comm graph."""
    return [b if a == i else a for (a, b) in edges if i in (a, b)]


def reference_velocity(z: np.ndarray, t_targets: np.ndarray, edges: tuple) -> np.ndarray:
    """[§2 line 60-61]:
        u_i^ref = -K_T (z_i - t_i) - K_F sum_{j ∈ N_i} [(z_i - z_j) - (t_i - t_j)]
    """
    N = z.shape[0]
    u_ref = np.zeros_like(z)
    for i in range(N):
        u_ref[i] = -pp.K_T * (z[i] - t_targets[i])
        for j in neighbours(i, edges):
            u_ref[i] -= pp.K_F * ((z[i] - z[j]) - (t_targets[i] - t_targets[j]))
    return u_ref


def adaptive_law_rate(theta_hat: np.ndarray, x: np.ndarray, z: np.ndarray,
                      u_ref: np.ndarray) -> np.ndarray:
    """[§2 line 64]:
        d theta_hat_i / dt = Proj_[theta_min, theta_max] (
            -(gamma / m_i^2) * (u_i^ref)^T * (x_i - z_i)
        )
        m_i^2 := 1 + ||u_i^ref||^2
    Returns the rate vector (N,) AFTER smooth projection [Krstic-Kanellakopoulos-Kokotovic 1995 §4].
    """
    N = theta_hat.shape[0]
    e = x - z                                     # (N, d) MRAC error
    rates = np.zeros(N)
    for i in range(N):
        m_sq = 1.0 + np.dot(u_ref[i], u_ref[i])
        raw = -(pp.GAMMA / m_sq) * np.dot(u_ref[i], e[i])
        # Smooth projection [§A1 + KKK 1995 §4]: clamp rate at boundary
        if theta_hat[i] <= pp.THETA_MIN and raw < 0:
            rates[i] = 0.0
        elif theta_hat[i] >= pp.THETA_MAX and raw > 0:
            rates[i] = 0.0
        else:
            rates[i] = raw
    return rates


def kalman_bucy_riccati(P: np.ndarray, u_ref: np.ndarray) -> np.ndarray:
    """[§2 lines 70-72]:
        dP_i/dt = -P_i * ||u_i^ref||^2 / m_i^2 * P_i + Q^KB
    with Q^KB = 0 (deterministic Riccati; matches Anderson 1985 framework).

    For scalar parameter with scalar regressor magnitude, this reduces to the
    Bertsekas-style scalar Riccati.
    """
    N = P.shape[0]
    rates = np.zeros(N)
    for i in range(N):
        m_sq = 1.0 + np.dot(u_ref[i], u_ref[i])
        rates[i] = -P[i] ** 2 * np.dot(u_ref[i], u_ref[i]) / m_sq
    return rates


def excitation_signal(t: float, omegas_i: np.ndarray, phases_i: np.ndarray,
                      A_e: float) -> np.ndarray:
    """[§8.3 v16]:
        e_i^pe(t) = A_e [sin(omega_i^1 t + phi_i^1), sin(omega_i^2 t + phi_i^2)]^T
    where omega_i^k is per-agent (staggered) and phases_i are per-agent.
    Returns (d,) vector for one agent.
    """
    return A_e * np.array([
        np.sin(omegas_i[0] * t + phases_i[0]),
        np.sin(omegas_i[1] * t + phases_i[1]),
    ])


def freedom_cone_projector(active_normals: list, d: int) -> np.ndarray:
    """[§3.2 line 102]:
        F_i(t) := (span{2(x_i - x_j) : j in N_i^on(t)})^perp
    Returns the orthogonal projector onto F_i. Empty active set → identity.
    """
    if not active_normals:
        return np.eye(d)
    G = np.array(active_normals)            # (k, d)
    GGt = G @ G.T
    try:
        invGGt = np.linalg.inv(GGt)
    except np.linalg.LinAlgError:
        invGGt = np.linalg.pinv(GGt)
    return np.eye(d) - G.T @ invGGt @ G


def cbf_h(x_i: np.ndarray, x_j: np.ndarray) -> float:
    """[§Notation line 30]:
        h_ij(x) := ||x_i - x_j||^2 - r_safe^2
    """
    return float(np.dot(x_i - x_j, x_i - x_j)) - pp.R_SAFE ** 2


def update_hysteresis(x: np.ndarray, theta_hat: np.ndarray, u_AC: np.ndarray,
                      pair_active_in: dict, edges: tuple) -> dict:
    """[§3.1 line 92, gauge-fixed CBF c_ij defined at line 82]:
        Engagement when c_ij <= eps; disengagement when c_ij >= 2 eps.
        eps in [delta_ij + tol_QP, 0.1 r_safe^2]; we use eps = 0.05 r_safe^2 [§8.3].

    The gauge-fixed constraint LHS for agent i [§2.1 eq line 82]:
        c_ij = 2(x_i - x_j)^T u_i
               - 2 (theta_i / theta_j)(x_i - x_j)^T u_j^AC
               + alpha theta_i h_ij(x)
    Evaluated at u_i = u_i^AC (proxy for "would the constraint bite").
    """
    new_active = dict(pair_active_in)
    for (i, j) in edges:
        x_diff = x[i] - x[j]
        h_ij = np.dot(x_diff, x_diff) - pp.R_SAFE ** 2
        c_i = (2 * np.dot(x_diff, u_AC[i])
               - 2 * (theta_hat[i] / theta_hat[j]) * np.dot(x_diff, u_AC[j])
               + pp.ALPHA * theta_hat[i] * h_ij)
        c_j = (-2 * np.dot(x_diff, u_AC[j])
               - 2 * (theta_hat[j] / theta_hat[i]) * (-np.dot(x_diff, u_AC[i]))
               + pp.ALPHA * theta_hat[j] * h_ij)
        c_min = min(c_i, c_j)
        key = frozenset({i, j})
        currently_active = new_active.get(key, False)
        if currently_active:
            if c_min >= 2 * pp.EPS_HYST:
                new_active[key] = False
        else:
            if c_min <= pp.EPS_HYST:
                new_active[key] = True
    return new_active


def cbf_tightening_delta(P_i: float, D_max: float, d: int) -> float:
    """[§2.1 line 84 + Lemma 5.2]:
        delta_ij(t) = 2 D_max * (sqrt(P_i)/theta_min)
                      * (sqrt(d) u_max + theta_max u_max^ref)
    where u_max^ref is bounded by the saturation u_max [§2.2].
    """
    u_max_ref = pp.U_MAX  # conservative: u^ref bounded by u_max
    return (2.0 * D_max * np.sqrt(max(P_i, 0.0)) / pp.THETA_MIN
            * (np.sqrt(d) * pp.U_MAX + pp.THETA_MAX * u_max_ref))
