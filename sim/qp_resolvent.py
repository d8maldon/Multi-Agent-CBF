"""Per-agent QP-resolvent (Moreau proximal operator on the time-varying convex
constraint set), v17 scalar-u_2 / HOCBF form, council-vetted (Passes 19-21).

Solves [§3.2 v17 boxed equation, after gauge-fixing of §3.1]:
    u_{2,i}^{safe} = argmin_{u_2}  (u_2 - (u_{2,i}^{AC} + tilde_e_i^{pe}))^2
                                   + M sum_{j in N_i^on} s_{ij}^2
    s.t.   c_{ij}(u_{2,i}; r, v_a, hat_theta) >= delta_{ij}(t),  for j in N_i^on(t),
           |u_{2,i}| <= psi_dot_max,
           s_{ij} >= 0
where, with a_ii = +2 Im((r_i - r_j) conj(v_{a,i})) and
       a_ij = -2 Im((r_i - r_j) conj(v_{a,j})):
    c_{ij}(u_{2,i}; r, v_a, hat_theta)
        := a_ii * u_{2,i}
         + (hat_theta_i / hat_theta_j) * a_ij * u_{2,j}^{safe}(t^-)
         + hat_theta_i * b_{ij}^{(0)}                      [§3.1 v17 boxed]
    b_{ij}^{(0)} := 2|v_{a,i} - v_{a,j}|^2
                  + 2(alpha_1 + alpha_2) Re((r_i - r_j) conj(v_{a,i} - v_{a,j}))
                  + alpha_1 * alpha_2 * h_{ij}             [§3.1 v17 corrected]

(Earlier drafts had every term in b_{ij}^{(0)} halved by 2 — caught by Pass 19
Tao + Pass 20 Klein equivariance check. The form above is consistent with
a_ii = 2 Im(...) and the HOCBF condition multiplied through by hat_theta_i.)

The decision variable is the scalar real turn rate u_{2,i} in R; one slack
s_{ij} >= 0 per active pair. Cf. v16 (single-integrator, vector-u) where the
decision was u_i in R^d.

Cross-term semantics (Pass 21 / Egerstedt):
    Per axiom (A4) v17, agent i receives u_{2,j}^{safe}(t^-) — the most-recent
    past broadcast of agent j's safety-filtered command. This avoids algebraic
    loops: the v17 integrator stores last-step u_{2,j}^{safe} in
    `state.last_u_safe` and passes it here as `u_2_neighbour_broadcast`.
    With tau_d=0 (continuous-time broadcast), this is u_{2,j}^{safe}(t).
    With tau_d > 0, the broadcast residual is absorbed into delta_{ij}(t)
    via dynamics.cbf_tightening_delta (eps_3 term, §3.1.2).
"""

from __future__ import annotations

import numpy as np
import osqp
from scipy import sparse

from . import paper_params as pp
from . import dynamics as dyn


def solve_qp(i: int, r: np.ndarray, v_a: np.ndarray, theta_hat: np.ndarray,
             u_2_AC: np.ndarray, pe_projected_i: float, pair_active: dict,
             edges: tuple, delta_ij: dict, solver_cache: dict,
             obstacles: tuple = ()) -> tuple:
    """Solve agent i's per-agent QP-resolvent [§3.2 v17].

    Parameters
    ----------
    i               : agent index.
    r               : (N,) complex array, positions r_j = x_j + i y_j.
    v_a             : (N,) complex array, velocity-along-heading v_{a,j}.
    theta_hat       : (N,) real array, parameter estimates (1/lambda_j).
    u_2_AC          : (N,) real array, neighbour broadcast for the cross-term.
                      Per axiom (A4) v17, this should be u_{2,j}^{safe}(t^-) —
                      the most-recent past broadcast of agent j's safety-filtered
                      command, stored by the integrator in `state.last_u_safe`.
                      The legacy v16 callers passed u_{2,j}^{AC} = theta_j *
                      u_{2,j}^{ref} (the assumed-correct command); the residual
                      from this substitution is absorbed into delta_{ij}(t)
                      (eps_2 term in dynamics.cbf_tightening_delta, §3.1.2).
                      Param name kept as `u_2_AC` for backward compat.
    pe_projected_i  : scalar real, freedom-cone-projected PE for agent i.
                      In 1-D control space the freedom cone is either {0} or R;
                      caller is expected to pass 0 when any pair is active
                      (axiom (A2'') free-time dwell condition gates PE injection).
    pair_active     : {frozenset({i,j}): bool} hysteretic active set
                      (Krasnosel'skii-Pokrovskii 1989 play operator).
    edges           : tuple of (i,j) pairs.
    delta_ij        : {frozenset({i,j}): float} CBF tightening, computed via
                      dynamics.cbf_tightening_delta (§3.1.2 residual aggregation).
    solver_cache    : per-agent OSQP problem cache, keyed on active-set sig.

    Returns
    -------
    u_2_safe_i      : scalar safe turn rate.
    slack_vec       : (k,) array of slack values, k = |active pairs|.
    status_string   : OSQP status (or "FALLBACK (...)" if QP failed).
    """
    target = float(u_2_AC[i] + pe_projected_i)

    active_pairs = [j for j in dyn.neighbours(i, edges)
                    if pair_active.get(frozenset({i, j}), False)]
    k = len(active_pairs)
    # v17.7: also include static-obstacle constraints (Pass 47 council).
    # Obstacles are always active (no hysteresis on obstacles since they
    # don't move and the relative-degree-2 HOCBF is well-behaved).
    n_obs = len(obstacles)
    k_total = k + n_obs                            # total slack count
    n = 1 + k_total                                 # decision dim: u_2 + slacks

    # Quadratic cost Hessian [§3.2 v17]:
    #   0.5 v^T P v + q^T v with P = diag(2, 2M, ..., 2M)
    P_diag = np.concatenate([[2.0], 2.0 * pp.SLACK_PENALTY * np.ones(k_total)])
    P_mat = sparse.diags(P_diag).tocsc()

    # Linear cost: from (u_2 - target)^2 = u_2^2 - 2 target u_2 + const
    q_vec = np.concatenate([[-2.0 * target], np.zeros(k_total)])

    rows = []
    l_vec = []
    u_vec = []

    # HOCBF constraints, one per active pair  [paper §3.1 line 159-162]
    for k_idx, j in enumerate(active_pairs):
        h_val = dyn.cbf_h(r[i], r[j])
        b0_ij = dyn.hocbf_residual(r[i], r[j], v_a[i], v_a[j], h_val)
        a_ii = dyn.hocbf_jacobian_self(r[i], r[j], v_a[i])
        a_ij = dyn.hocbf_jacobian_other(r[i], r[j], v_a[j])

        # Gauge-fixed cross-term carries factor (hat_theta_i / hat_theta_j)
        # [§3.1 v17 line 161]; the decision-variable coefficient itself is
        # hat_theta-INDEPENDENT, exactly as in v16 [§3.1 v17 line 168].
        cross_term = (theta_hat[i] / theta_hat[j]) * a_ij * float(u_2_AC[j])
        rhs_const = (delta_ij.get(frozenset({i, j}), 0.0)
                     - cross_term
                     - theta_hat[i] * b0_ij)

        row = np.zeros(n)
        row[0] = a_ii
        row[1 + k_idx] = 1.0                       # +slack_{ij}
        rows.append(row)
        l_vec.append(rhs_const)
        u_vec.append(np.inf)

    # v17.7 STATIC OBSTACLE constraints (Pass 47 council). Each obstacle
    # contributes one HOCBF constraint with its own slack:
    #   theta_hat[i] * b0_obs + a_obs * u_2 + s_obs >= 0
    # No cross-term (obstacle has no control).
    for o_idx, (r_obs, r_obs_radius) in enumerate(obstacles):
        h_obs = dyn.cbf_h_obstacle(r[i], r_obs, r_obs_radius)
        b0_obs = dyn.hocbf_residual_obstacle(r[i], r_obs, v_a[i], h_obs)
        a_obs = dyn.hocbf_jacobian_obstacle(r[i], r_obs, v_a[i])
        rhs_const = -theta_hat[i] * b0_obs
        row = np.zeros(n)
        row[0] = a_obs
        row[1 + k + o_idx] = 1.0                   # +slack_obs
        rows.append(row)
        l_vec.append(rhs_const)
        u_vec.append(np.inf)

    # slack >= 0 (for both pair and obstacle slacks)
    for k_idx in range(k_total):
        row = np.zeros(n)
        row[1 + k_idx] = 1.0
        rows.append(row)
        l_vec.append(0.0)
        u_vec.append(np.inf)

    # Saturation: -psi_dot_max <= u_2 <= psi_dot_max  [§3.1 v17 line 174]
    sat_row = np.zeros(n)
    sat_row[0] = 1.0
    rows.append(sat_row)
    l_vec.append(-pp.PSI_DOT_MAX)
    u_vec.append(pp.PSI_DOT_MAX)

    A_mat = sparse.csc_matrix(np.array(rows))
    l_arr = np.array(l_vec)
    u_arr = np.array(u_vec)

    # Solver caching keyed on (agent, active-set signature, obstacle count)
    cache_key = (i, tuple(active_pairs), n_obs)
    cached = solver_cache.get(cache_key)
    if cached is None:
        prob = osqp.OSQP()
        prob.setup(P_mat, q_vec, A_mat, l_arr, u_arr,
                   eps_abs=pp.QP_TOL, eps_rel=pp.QP_TOL,
                   max_iter=20000, verbose=False, polishing=False,
                   warm_starting=True)
        solver_cache[cache_key] = prob
    else:
        prob = cached
        prob.update(q=q_vec, l=l_arr, u=u_arr)

    res = prob.solve()
    if res.info.status_val not in (1, 2):
        # Fallback: clipped target. Slack = 0 by convention.
        u_safe_fallback = float(np.clip(target, -pp.PSI_DOT_MAX, pp.PSI_DOT_MAX))
        return u_safe_fallback, np.zeros(k), f"FALLBACK ({res.info.status})"

    return float(res.x[0]), res.x[1:].copy(), res.info.status


def closed_form_two_agent(i: int, j: int, r: np.ndarray, v_a: np.ndarray,
                          theta_hat: np.ndarray, u_2_AC: np.ndarray,
                          pe_projected_i: float, delta_val: float) -> float:
    """Closed-form Karush-Kuhn-Tucker (KKT) solution for N=2, single active pair
    [paper §3.3 v17.1; Karush 1939 dissertation; Kuhn-Tucker 1951
    Berkeley Symp. on Math. Statist. and Probab.].

    Used as a unit test for the OSQP wrapper before scaling to N >= 3.

    For agent i with one active CBF constraint vs j and no saturation binding,
    the KKT conditions give the closed-form solution:
        u_{2,i}^{safe} = (u_{2,i}^{AC} + tilde_e_i^{pe})  +  mu_ij^* * a_{ii}
        mu_ij^* = max(0, (delta - c(u_AC + e_pe)) / a_ii^2)
    where mu_ij^* >= 0 is the KKT multiplier for the inequality constraint,
    satisfying complementary slackness mu_ij^* * (c_ij - delta_ij) = 0,
    and c(*) is the LHS of the gauge-fixed HOCBF constraint at u = u_AC + e_pe.

    Returns u_{2,i}^{safe} (NOT clipped to saturation; caller clips if needed).
    """
    h_val = dyn.cbf_h(r[i], r[j])
    b0_ij = dyn.hocbf_residual(r[i], r[j], v_a[i], v_a[j], h_val)
    a_ii = dyn.hocbf_jacobian_self(r[i], r[j], v_a[i])
    a_ij = dyn.hocbf_jacobian_other(r[i], r[j], v_a[j])
    target = float(u_2_AC[i] + pe_projected_i)
    cross_term = (theta_hat[i] / theta_hat[j]) * a_ij * float(u_2_AC[j])
    c_at_target = a_ii * target + cross_term + theta_hat[i] * b0_ij
    if c_at_target >= delta_val:
        return target
    if abs(a_ii) < 1e-12:
        # Degenerate: constraint independent of u_2 at this state; cannot fix.
        return target
    mu = (delta_val - c_at_target) / (a_ii ** 2)
    return target + mu * a_ii
