"""Per-agent QP-resolvent (Moreau proximal operator on the time-varying convex
constraint set), line-by-line from §3.2 of v14.

Solves [§3.2 boxed eq lines 109-117]:
    u_i^safe = argmin_u  ||u - (u_i^AC + Proj_F e_i^pe)||^2 + M sum slack_ij^2
    s.t.   c_ij(u_i; ...) >= delta_ij(t),  for j in N_i^on(t),
           ||u||_inf <= u_max,
           slack_ij >= 0
where c_ij is the gauge-fixed constraint [§2.1 eq line 82].
"""

from __future__ import annotations

import numpy as np
import osqp
from scipy import sparse

from . import paper_params as pp
from . import dynamics as dyn


def solve_qp(i: int, x: np.ndarray, theta_hat: np.ndarray, u_AC: np.ndarray,
             pe_projected_i: np.ndarray, pair_active: dict, edges: tuple,
             delta_ij: dict, solver_cache: dict) -> tuple:
    """Solve agent i's per-agent QP-resolvent [§3.2].

    Decision vector v = [u (d,), s_1, ..., s_k] with k = |active pairs|.

    Returns (u_safe_i, slack_vec, status_string).
    """
    d = x.shape[1]
    target = u_AC[i] + pe_projected_i

    active_pairs = [j for j in dyn.neighbours(i, edges)
                    if pair_active.get(frozenset({i, j}), False)]
    k = len(active_pairs)
    n = d + k                                        # decision dimension

    # Quadratic cost Hessian [§3.2 line 116]:
    #   H = diag(2 I_d, 2 M I_k)
    P_diag = np.concatenate([2.0 * np.ones(d), 2.0 * pp.SLACK_PENALTY * np.ones(k)])
    P_mat = sparse.diags(P_diag).tocsc()

    # Linear cost: derived from expansion of  ||u - target||^2 = u^T u - 2 target^T u + const
    q_vec = np.concatenate([-2.0 * target, np.zeros(k)])

    # Constraint rows
    rows = []
    l_vec = []
    u_vec = []

    # CBF constraints, one per active pair  [§2.1 line 82]
    for k_idx, j in enumerate(active_pairs):
        x_diff = x[i] - x[j]
        h_ij = dyn.cbf_h(x[i], x[j])
        # Gauge-fixed constraint:
        #   2(x_i-x_j)^T u_i  +  b_ij  +  alpha theta_i h_ij  +  slack >=  delta_ij
        # where b_ij = -2 (theta_i / theta_j)(x_i-x_j)^T u_j^AC
        b_ij = -2.0 * (theta_hat[i] / theta_hat[j]) * np.dot(x_diff, u_AC[j])
        row = np.zeros(n)
        row[:d] = 2.0 * x_diff
        row[d + k_idx] = 1.0
        rows.append(row)
        rhs = (delta_ij.get(frozenset({i, j}), 0.0)
               - b_ij
               - pp.ALPHA * theta_hat[i] * h_ij)
        l_vec.append(rhs)
        u_vec.append(np.inf)

    # slack >= 0
    for k_idx in range(k):
        row = np.zeros(n)
        row[d + k_idx] = 1.0
        rows.append(row)
        l_vec.append(0.0)
        u_vec.append(np.inf)

    # Saturation: -u_max <= u_dim <= u_max  [§2.1 line 92]
    for k_dim in range(d):
        row = np.zeros(n)
        row[k_dim] = 1.0
        rows.append(row)
        l_vec.append(-pp.U_MAX)
        u_vec.append(pp.U_MAX)

    A_mat = sparse.csc_matrix(np.array(rows)) if rows else sparse.csc_matrix((0, n))
    l_arr = np.array(l_vec)
    u_arr = np.array(u_vec)

    # Solver caching keyed on (agent, active-set signature) [§3.3 numerical scheme]
    cache_key = (i, tuple(active_pairs))
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
        u_safe_fallback = np.clip(target, -pp.U_MAX, pp.U_MAX)
        return u_safe_fallback, np.zeros(k), f"FALLBACK ({res.info.status})"

    return res.x[:d].copy(), res.x[d:].copy(), res.info.status
