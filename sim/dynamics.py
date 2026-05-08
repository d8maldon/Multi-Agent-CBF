"""Plant + reference + adaptive law + KB auxiliary, v17 (complex-Dubins).

Each function is annotated with the v17 paper section / equation it implements.
State per agent: (r_i, v_{a,i}) in C^2. Position r = x + iy; velocity-along-
heading v_a = V_a exp(i psi). Constant-speed simplification: |v_a| = V_0.
The only effective control per agent is the scalar real turn rate u_2 in R.

Controllability (paper §2.1; Carathéodory 1909 / Chow 1939). The single-input
plant dot v_a = i*lambda*u_2*v_a is reachable on SE(2) via u_2 in R: the Lie
bracket of forward-motion (X_1 = v_a*partial_r) and turning (X_2 = i*v_a*u_2*
partial_{v_a}) generates the missing lateral direction. Chow's theorem (1939)
on bracket-generating systems then gives global controllability on the
constant-speed manifold |v_a| = V_0. This is the foundational reachability
that underlies the §3 safety filter and §5 identifiability constructions.
"""

from __future__ import annotations

import numpy as np

from . import paper_params as pp


def neighbours(i: int, edges: tuple) -> list:
    return [b if a == i else a for (a, b) in edges if i in (a, b)]


def reference_velocity(z: np.ndarray, t_targets: np.ndarray, edges: tuple,
                       t_targets_dot: np.ndarray = None) -> np.ndarray:
    """[§2.3 v17.3]: reference complex velocity command as a function of (z, t).

    v17.3 adds an optional feedforward term `t_targets_dot` (the target's
    instantaneous velocity) so that the reference dynamics can track moving
    formations exactly when the kinematic constraint $V_0 \\ge \\sup_t |\\dot
    t_i|$ is honoured (Carathéodory 1909 reachability).

    The formation feedback acts via the **Kirchhoff Laplacian** L_G (Kirchhoff
    1847) of the communication graph, encoded here through the per-agent
    neighbour sums. The proportional gain K_T contributes K_T*I to the formation
    matrix; the coupling gain K_F contributes K_F*L_G. The smallest non-zero
    eigenvalue lambda_2(L_G) is the Fiedler 1973 algebraic connectivity, the
    effective spring constant for formation cohesion. See §4.3 Step (b)
    Hilbert-Courant min-max for the analytical role of L_G.
    """
    N = z.shape[0]
    v_des = np.zeros(N, dtype=complex)
    for i in range(N):
        v_des[i] = -pp.K_T * (z[i] - t_targets[i])
        for j in neighbours(i, edges):
            v_des[i] -= pp.K_F * ((z[i] - z[j]) - (t_targets[i] - t_targets[j]))
    # Feedforward: add target velocity so steady-state error is zero for
    # moving formations (Pomet-Praly-style velocity feedforward; v17.3).
    if t_targets_dot is not None:
        v_des = v_des + t_targets_dot
    # Cap magnitude at V_0 to respect constant-speed simplification
    norms = np.abs(v_des)
    norms = np.where(norms > pp.V_0, norms, pp.V_0)
    v_des = v_des * (pp.V_0 / np.maximum(norms, 1e-12))
    return v_des


def reference_turn_rate(v_a: np.ndarray, v_des: np.ndarray) -> np.ndarray:
    """[§2.3 v17]: extract the real turn-rate command from the complex velocity error.

    Given the current v_a and a desired complex velocity v_des (both magnitude V_0
    after capping), the heading-error rate is:

        u_2^ref = arg(v_des / v_a) / dt  ~  Im(v_des / v_a) for small heading error
                                         = Im(v_des * conj(v_a)) / |v_a|^2

    This is the heading-PD-controller realisation: drive psi toward arg(v_des).
    """
    # Heading error angle = arg(v_des / v_a) (signed)
    ratio = v_des * np.conj(v_a) / (np.abs(v_a) ** 2 + 1e-12)
    # Atan2-style angle, bounded by maximum turn rate
    psi_err = np.angle(ratio)               # in [-pi, pi]
    # P-controller on heading error with gain K_T (re-using the tracking gain)
    return np.clip(pp.K_T * psi_err, -pp.PSI_DOT_MAX, pp.PSI_DOT_MAX)


def adaptive_law_rate(theta_hat: np.ndarray, r: np.ndarray, r_ref: np.ndarray,
                      v_a: np.ndarray, v_ref: np.ndarray,
                      u_2_ref: np.ndarray) -> np.ndarray:
    """[§2.4 v17]:
        d theta_hat_i / dt = Proj_[theta_min, theta_max] (
            -(gamma / m_i^2) * Re( conj(i v_a u_2^ref) * tilde_v )
        )
        m_i^2 := 1 + |v_a u_2^ref|^2
        tilde_v := v_a - v_ref
    """
    N = theta_hat.shape[0]
    rates = np.zeros(N)
    tilde_v = v_a - v_ref
    for i in range(N):
        regressor = 1j * v_a[i] * u_2_ref[i]   # complex regressor for theta_hat
        m_sq = 1.0 + np.abs(regressor) ** 2
        # Real-positive-definite swapped-signal gradient
        raw = -(pp.GAMMA / m_sq) * np.real(np.conj(regressor) * tilde_v[i])
        # Smooth projection
        if theta_hat[i] <= pp.THETA_MIN and raw < 0:
            rates[i] = 0.0
        elif theta_hat[i] >= pp.THETA_MAX and raw > 0:
            rates[i] = 0.0
        else:
            rates[i] = raw
    return rates


def kalman_bucy_riccati(P: np.ndarray, v_a: np.ndarray, u_2_ref: np.ndarray) -> np.ndarray:
    """[§2.5 v17]:
        dP/dt = -P^2 * |v_a u_2^ref|^2 / m^2  (Q^KB = 0)
    """
    N = P.shape[0]
    rates = np.zeros(N)
    for i in range(N):
        regressor_sq = np.abs(v_a[i] * u_2_ref[i]) ** 2
        m_sq = 1.0 + regressor_sq
        rates[i] = -P[i] ** 2 * regressor_sq / m_sq
    return rates


def excitation_signal(t: float, omegas_i: np.ndarray, phases_i: np.ndarray,
                      A_e: float) -> float:
    """[§8.3 v17]:
        e_i^pe(t) = A_e * (sin(w_i^1 t + phi_i^1) + sin(w_i^2 t + phi_i^2)) / 2
    Returns a SCALAR (the v17 control is u_2 in R, so PE is scalar too).
    """
    return 0.5 * A_e * (
        np.sin(omegas_i[0] * t + phases_i[0])
        + np.sin(omegas_i[1] * t + phases_i[1])
    )


def cbf_h(r_i: complex, r_j: complex) -> float:
    """[§3.1 v17]: h_ij = |r_i - r_j|^2 - r_safe^2."""
    return float(np.abs(r_i - r_j) ** 2) - pp.R_SAFE ** 2


def cbf_h_dot(r_i: complex, r_j: complex, v_i: complex, v_j: complex) -> float:
    """[§3.1 v17]: dot h_ij = 2 Re( (r_i - r_j) conj(v_i - v_j) )."""
    return 2.0 * float(np.real((r_i - r_j) * np.conj(v_i - v_j)))


def hocbf_residual(r_i: complex, r_j: complex,
                   v_i: complex, v_j: complex, h_val: float) -> float:
    """[§3.1 v17, council Pass 19/20/21]: theta-independent part of the HOCBF
    condition (everything except the u_2 terms), in the corrected form:

        b_ij^(0) = 2|v_i - v_j|^2
                 + 2(alpha_1 + alpha_2) Re((r_i - r_j) conj(v_i - v_j))
                 + alpha_1 * alpha_2 * h_ij.

    Earlier drafts had every term halved by 2 (factor-of-2 inconsistency caught
    by Pass 19 Tao + Pass 20 Klein-equivariance check). The correct factors come
    from substituting ddot h = 2|v|^2 + ... and dot h = 2 Re(...) into the HOCBF
    inequality ddot h + (a1+a2) dot h + a1*a2 h >= 0, then multiplying by hat_theta_i.
    """
    return (2.0 * np.abs(v_i - v_j) ** 2
            + 2.0 * (pp.ALPHA_1 + pp.ALPHA_2) * np.real((r_i - r_j) * np.conj(v_i - v_j))
            + pp.ALPHA_1 * pp.ALPHA_2 * h_val)


def hocbf_jacobian_self(r_i: complex, r_j: complex, v_i: complex) -> float:
    """[§3.1 v17]: coefficient of u_{2,i} in the HOCBF constraint:
        a_{ij,i} = 2 * Im( (r_i - r_j) * conj(v_i) )
    (The lambda_i factor is absorbed into the gauge-fixing step.)
    """
    return 2.0 * float(np.imag((r_i - r_j) * np.conj(v_i)))


def hocbf_jacobian_other(r_i: complex, r_j: complex, v_j: complex) -> float:
    """[§3.1 v17]: coefficient of u_{2,j} in agent i's HOCBF constraint:
        a_{ij,j} = -2 * Im( (r_i - r_j) * conj(v_j) )
    """
    return -2.0 * float(np.imag((r_i - r_j) * np.conj(v_j)))


# ---------------------------------------------------------------------------
# v17.7 STATIC OBSTACLE CBF helpers (Pass 47 council APPROVED)
# ---------------------------------------------------------------------------
# Each obstacle is a fixed circle (centre, radius). For agent i, the CBF is
#   h_obs(r_i) = |r_i - r_obs|^2 - (r_safe + r_obs)^2
# Treating the obstacle as a virtual agent with v_obs = 0, dot v_obs = 0 gives:
#   dot h_obs   = 2 Re((r_i - r_obs) * conj(v_i))
#   ddot h_obs  = 2 |v_i|^2 + 2 (r_i - r_obs) . dot v_i
# The HOCBF-2 condition is: ddot h + (alpha_1 + alpha_2) dot h + alpha_1*alpha_2*h >= 0.
# The obstacle has NO control input, so only the agent's u_2 appears in the
# linear (jacobian) term.

def cbf_h_obstacle(r_i: complex, r_obs: complex, r_obs_radius: float) -> float:
    """h_obs = |r_i - r_obs|^2 - (r_safe + r_obs)^2 (static obstacle)."""
    return float(np.abs(r_i - r_obs) ** 2) - (pp.R_SAFE + r_obs_radius) ** 2


def hocbf_residual_obstacle(r_i: complex, r_obs: complex, v_i: complex,
                             h_val: float) -> float:
    """Theta-independent (b0) part of the HOCBF for static obstacle. Same form
    as the pairwise hocbf_residual but with v_obs = 0:
        b0_obs = 2 |v_i|^2 + 2(alpha_1+alpha_2) Re((r_i - r_obs) conj(v_i))
                 + alpha_1*alpha_2*h_obs.
    """
    return (2.0 * np.abs(v_i) ** 2
            + 2.0 * (pp.ALPHA_1 + pp.ALPHA_2) * np.real((r_i - r_obs) * np.conj(v_i))
            + pp.ALPHA_1 * pp.ALPHA_2 * h_val)


def hocbf_jacobian_obstacle(r_i: complex, r_obs: complex, v_i: complex) -> float:
    """Coefficient of u_{2,i} in the static-obstacle HOCBF constraint. Same as
    hocbf_jacobian_self but with r_j replaced by r_obs:
        a_obs_self = 2 Im((r_i - r_obs) conj(v_i)).
    """
    return 2.0 * float(np.imag((r_i - r_obs) * np.conj(v_i)))


def update_hysteresis(r: np.ndarray, v_a: np.ndarray, theta_hat: np.ndarray,
                      u_2_AC: np.ndarray, pair_active_in: dict, edges: tuple) -> dict:
    """[§3.1 v17]: hysteretic active-set selection. Engagement when c_ij <= eps,
    disengagement when c_ij >= 2 eps; eps = paper §8.3 value.

    The c_{ij} value evaluated here matches the gauge-fixed constraint LHS in
    qp_resolvent.solve_qp (paper §3.1 line 159), including the theta_i/theta_j
    factor on the cross-coupled neighbour term."""
    new_active = dict(pair_active_in)
    for (i, j) in edges:
        h_val = cbf_h(r[i], r[j])
        # Agent i's view of the constraint
        b0_i = hocbf_residual(r[i], r[j], v_a[i], v_a[j], h_val)
        a_ii = hocbf_jacobian_self(r[i], r[j], v_a[i])
        a_ij = hocbf_jacobian_other(r[i], r[j], v_a[j])
        c_i = (a_ii * u_2_AC[i]
               + (theta_hat[i] / theta_hat[j]) * a_ij * u_2_AC[j]
               + theta_hat[i] * b0_i)
        # Symmetric for agent j (b0 is symmetric: |v_i - v_j|^2 etc.)
        b0_j = hocbf_residual(r[j], r[i], v_a[j], v_a[i], h_val)
        a_jj = hocbf_jacobian_self(r[j], r[i], v_a[j])
        a_ji = hocbf_jacobian_other(r[j], r[i], v_a[i])
        c_j = (a_jj * u_2_AC[j]
               + (theta_hat[j] / theta_hat[i]) * a_ji * u_2_AC[i]
               + theta_hat[j] * b0_j)
        c_min = min(c_i, c_j)
        key = frozenset({i, j})
        if new_active.get(key, False):
            if c_min >= 2 * pp.EPS_HYST:
                new_active[key] = False
        else:
            if c_min <= pp.EPS_HYST:
                new_active[key] = True
    return new_active


def cbf_tightening_delta(P_i: float, P_j: float,
                          a_ii: float, a_ij: float,
                          theta_i: float, theta_j: float,
                          tau_d: float = 0.0,
                          zeta_0: float = 1e-3) -> float:
    """[§3.1.2 v17, council Pass 19/20/21]: time-varying CBF tightening with
    explicit residual aggregation.

        delta_ij(t) = psi_dot_max * (|a_ii| * eps_1 + |a_ij| * eps_2)
                    + (theta_i / theta_j) * |a_ij| * eps_3(tau_d)
                    + zeta_0

    where:
        eps_1   = theta_max * sqrt(P_i) / theta_min            [LHS-coeff residual]
        eps_2   = theta_max^2 * sqrt(P_j) / theta_min^2        [cross-term residual]
        eps_3   = L_QP * tau_d  ~  (1+kappa_lambda) * psi_dot_max * tau_d
                                                                [latency residual]
        zeta_0  = small positive baseline (Lemma 5.2 baseline; default 1e-3)

    Vanishes as P_i, P_j -> 0 (estimator convergence) and tau_d -> 0
    (continuous-time broadcast).

    For tau_d = 0 (the default in this codebase), eps_3 contribution is zero.

    Earlier v16 / draft-v17 used a single-scalar form
        delta_ij(t) = 2 * D_max * sqrt(P_i) / theta_min * V_0 * psi_dot_max
    which used worst-case D_max bounds instead of the per-pair |a_ii|, |a_ij|
    entries; the v17 form here is tighter on the closed-loop trajectory.
    """
    eps_1 = pp.THETA_MAX * np.sqrt(max(P_i, 0.0)) / pp.THETA_MIN
    eps_2 = pp.THETA_MAX ** 2 * np.sqrt(max(P_j, 0.0)) / pp.THETA_MIN ** 2
    delta = pp.PSI_DOT_MAX * (abs(a_ii) * eps_1 + abs(a_ij) * eps_2) + zeta_0
    if tau_d > 0.0:
        L_qp_upper = (1.0 + pp.KAPPA_LAMBDA) * pp.PSI_DOT_MAX
        eps_3 = L_qp_upper * tau_d
        delta += (theta_i / theta_j) * abs(a_ij) * eps_3
    return delta
