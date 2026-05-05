"""Outer-loop RK4 integrator for v17 complex-Dubins multi-agent LOE-adaptive HOCBF
safety filter at h_outer = 5 ms [paper §3.3 + §8.3].

The closed loop is the Moreau (1971) sweeping process [paper §3.1.3, §3.2];
in continuous time we discretise via fixed-step RK4 using the inner OSQP solve
at each derivative evaluation.

Per paper §3.3 (council-vetted Passes 19-30):
    - Outer step h = 5 ms  [pp.H_OUTER]
    - Inner OSQP tolerance 1e-7  [pp.QP_TOL]
    - Slack penalty M = 1e4  [pp.SLACK_PENALTY]
    - Numerical-scheme error: ||x_n - x(t_n)|| <= C1 h + C2 tol/h + C3 / sqrt(M)
      [Brezis 1973 Cor 4.2 + Hager 1979 + Tikhonov 1963 / Engl-Hanke-Neubauer 1996]

Records every observable that the §8.4 figure plan needs, plus the running
scalar identifiability gain bar_rho_i [paper §5.2] for verifying §8.2 numbers.

State space (per agent):
    (r_i, v_{a,i}) in C^2  [plant: position + velocity-along-heading; |v_{a,i}| = V_0]
    (r_ref,i, v_ref,i) in C^2  [reference Dubins agent following the formation target]
    hat_theta_i in [theta_min, theta_max]  [parameter estimate of 1/lambda_i]
    P_i >= 0  [Kalman-Bucy covariance]
    pair_active: hysteresis state
    last_u_safe: previous-sub-step u_{2,j}^safe broadcast for axiom (A4) cross-term

Cf. v16: state was (x, z, theta_hat, P) with x in R^d single-integrator.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np

from . import paper_params as pp
from . import dynamics as dyn
from . import qp_resolvent as qpr


@dataclass
class State:
    """Closed-loop state for the v17 integrator.

    All complex arrays are 1-D over agents (shape (N,)). The plant lives in
    C^2 per agent; the reference Dubins agent lives in C^2 per agent.
    """
    t: float                      # time (s)
    r: np.ndarray                 # (N,) complex plant positions
    v_a: np.ndarray               # (N,) complex plant velocities, |v_{a,i}| = V_0
    r_ref: np.ndarray             # (N,) complex reference positions
    v_ref: np.ndarray             # (N,) complex reference velocities, |v_ref| = V_0
    theta_hat: np.ndarray         # (N,) parameter estimates (1/lambda_i)
    P: np.ndarray                 # (N,) KB filter covariances
    last_u_safe: np.ndarray       # (N,) previous-sub-step u_{2,j}^safe broadcast
                                  #      (axiom (A4) v17: u_{2,j}^safe(t^-) into c_ij)
    pair_active: dict             # {frozenset({i,j}): bool} hysteresis
    broadcast_history: Optional[list] = None
        # For comm_delay > 0: list of (t, r, v_a, theta_hat, last_u_safe) snapshots.


def _renormalise_velocity(v_a: np.ndarray) -> np.ndarray:
    """Project v_a onto the constant-speed circle |v_{a,i}| = V_0.

    The plant dot v_a = i lambda u_2 v_a preserves |v_a| analytically, but
    RK4 introduces 4th-order numerical drift. This projection corrects the
    drift each outer step (cheap; magnitude < 1e-6 per step at H_OUTER = 5 ms).
    """
    norms = np.abs(v_a)
    safe_norms = np.where(norms > 1e-12, norms, 1.0)
    return pp.V_0 * v_a / safe_norms


def _delayed_view(state: State, comm_delay: float) -> tuple:
    """Look up the most-recent broadcast snapshot at time <= t - comm_delay.

    Returns (r_delayed, v_a_delayed, theta_delayed, u_safe_delayed).
    For comm_delay = 0 (default), returns the current state.
    """
    if comm_delay <= 0.0 or not state.broadcast_history:
        return state.r, state.v_a, state.theta_hat, state.last_u_safe
    target_t = state.t - comm_delay
    for (t_h, r_h, v_h, th_h, us_h) in reversed(state.broadcast_history):
        if t_h <= target_t:
            return r_h, v_h, th_h, us_h
    # Fallback: oldest snapshot
    t0, r0, v0, th0, us0 = state.broadcast_history[0]
    return r0, v0, th0, us0


def _compute_u_2_ref(r_ref: np.ndarray, v_a: np.ndarray, t_targets: np.ndarray,
                     edges: tuple) -> np.ndarray:
    """Compute u_2^ref[i] for all agents via paper §2.3 reference-feedback law.

    1. v_des = formation-feedback complex velocity (capped at V_0).
    2. u_2^ref = heading-PD command toward v_des direction, clipped to psi_dot_max.

    The reference Dubins agent (r_ref, v_ref) tracks v_des through u_2^ref;
    the heading-PD law is implemented in dyn.reference_turn_rate.
    """
    v_des = dyn.reference_velocity(r_ref, t_targets, edges)
    return dyn.reference_turn_rate(v_a, v_des)


def _eval(state: State,
          t_targets_fn: Callable[[float], np.ndarray],
          edges: tuple,
          A_e: float,
          omegas: np.ndarray,
          phases: np.ndarray,
          solver_cache: dict,
          use_safety_filter: bool = True,
          comm_delay: float = 0.0) -> tuple:
    """Compute u^safe and all derivatives at the current state.

    Returns (deriv_dict, info_dict) where deriv_dict has keys
    {dr, dv_a, dr_ref, dv_ref, dtheta, dP} and info_dict has keys
    {u_2_ref, u_2_AC, u_2_safe, pe_projected, delta_ij, slacks}.
    """
    N = state.r.shape[0]

    # === 1. Targets and reference command ===
    t_now = t_targets_fn(state.t)                               # (N,) complex
    u_2_ref = _compute_u_2_ref(state.r_ref, state.v_a, t_now, edges)
    u_2_AC = state.theta_hat * u_2_ref                           # (N,) real

    # === 2. Communication-delayed broadcast view (axiom (A4) v17) ===
    # Each agent i sees its own state current; neighbours' (r_j, v_a,j, theta_j,
    # u_safe_j) are the most-recent past broadcast.
    r_bcast, v_bcast, theta_bcast, u_safe_bcast = _delayed_view(state, comm_delay)

    def per_agent_view(i):
        """Agent i's view: its own state current, neighbours' delayed."""
        r_view = r_bcast.copy()
        v_view = v_bcast.copy()
        th_view = theta_bcast.copy()
        us_view = u_safe_bcast.copy()
        r_view[i] = state.r[i]
        v_view[i] = state.v_a[i]
        th_view[i] = state.theta_hat[i]
        us_view[i] = state.last_u_safe[i]
        return r_view, v_view, th_view, us_view

    # === 3. Hysteretic active-set update (Krasnosel'skii-Pokrovskii play operator) ===
    # Done per outer step (rate-independent; commutes with RK4 sub-stepping).
    # Within the RK4 sub-step _eval calls, we DO NOT modify pair_active — it's
    # frozen for the duration of one outer step. The outer loop (`run`) updates
    # it once per step using the post-step state.

    pair_active = state.pair_active

    # === 4. CBF tightening per paper §3.1.2 (R1+R2+R3 residual aggregation) ===
    delta_ij = {}
    for (i, j) in edges:
        a_ii = dyn.hocbf_jacobian_self(r_bcast[i], r_bcast[j], v_bcast[i])
        a_ij = dyn.hocbf_jacobian_other(r_bcast[i], r_bcast[j], v_bcast[j])
        # Symmetric: take the larger of the two pair members' tightenings.
        delta_i = dyn.cbf_tightening_delta(state.P[i], state.P[j], a_ii, a_ij,
                                            state.theta_hat[i], state.theta_hat[j],
                                            tau_d=comm_delay)
        a_jj = dyn.hocbf_jacobian_self(r_bcast[j], r_bcast[i], v_bcast[j])
        a_ji = dyn.hocbf_jacobian_other(r_bcast[j], r_bcast[i], v_bcast[i])
        delta_j = dyn.cbf_tightening_delta(state.P[j], state.P[i], a_jj, a_ji,
                                            state.theta_hat[j], state.theta_hat[i],
                                            tau_d=comm_delay)
        delta_ij[frozenset({i, j})] = max(delta_i, delta_j)

    # === 5. PE injection with binary freedom-cone projection (paper §3.2 v17) ===
    # F_i in {0, R}: PE admitted only when no pair is active.
    pe_projected = np.zeros(N)
    for i in range(N):
        any_active = any(pair_active.get(frozenset({i, j}), False)
                         for j in dyn.neighbours(i, edges))
        if A_e > 0.0 and not any_active:
            pe_projected[i] = dyn.excitation_signal(state.t, omegas[i], phases[i], A_e)

    # === 6. Per-agent QP solve (Moreau prox) ===
    u_2_safe = np.zeros(N)
    slacks_all = []
    for i in range(N):
        r_view, v_view, th_view, us_view = per_agent_view(i)
        if use_safety_filter:
            u_i_safe, slacks_i, _ = qpr.solve_qp(
                i, r_view, v_view, th_view, us_view, pe_projected[i],
                pair_active, edges, delta_ij, solver_cache,
            )
            u_2_safe[i] = u_i_safe
            slacks_all.append(slacks_i)
        else:
            # No safety filter: u_AC + PE clipped to saturation
            u_2_safe[i] = float(np.clip(u_2_AC[i] + pe_projected[i],
                                         -pp.PSI_DOT_MAX, pp.PSI_DOT_MAX))
            slacks_all.append(np.zeros(0))

    # === 7. Plant + reference dynamics (paper §2.1 + §2.2) ===
    # Plant: dot r_i = v_a,i,    dot v_a,i = i * lambda_i * u_2_safe * v_a,i
    dr = state.v_a.copy()
    # Slice pp.LAMBDA_TRUE to the actual number of agents N (allows runs with
    # fewer agents than the §8.3 N=4 cross-swap default — e.g., the §8.1 N=2
    # head-on demo).
    lambda_arr = pp.LAMBDA_TRUE[:N]
    dv_a = 1j * lambda_arr * u_2_safe * state.v_a

    # Reference Dubins:
    # dot r_ref = v_ref,    dot v_ref = i * u_2_ref * v_ref
    # The reference Dubins agent has NO LOE on it (it's an idealised reference);
    # its turn rate is u_2_ref (same as plant's commanded turn rate before LOE).
    dr_ref = state.v_ref.copy()
    dv_ref = 1j * u_2_ref * state.v_ref

    # === 8. Adaptive law and KB filter (paper §2.4 + §2.5) ===
    dtheta = dyn.adaptive_law_rate(state.theta_hat, state.r, state.r_ref,
                                    state.v_a, state.v_ref, u_2_ref)
    dP = dyn.kalman_bucy_riccati(state.P, state.v_a, u_2_ref)

    info = {
        "u_2_ref": u_2_ref,
        "u_2_AC": u_2_AC,
        "u_2_safe": u_2_safe,
        "pe_projected": pe_projected,
        "delta_ij": delta_ij,
        "slacks": slacks_all,
    }
    deriv = {
        "dr": dr, "dv_a": dv_a,
        "dr_ref": dr_ref, "dv_ref": dv_ref,
        "dtheta": dtheta, "dP": dP,
    }
    return deriv, info


def _shifted(s_base: State, ds: dict, dt: float) -> State:
    """Build a shifted state for the next RK4 sub-step (state + dt * deriv)."""
    return State(
        t=s_base.t + dt,
        r=s_base.r + dt * ds["dr"],
        v_a=s_base.v_a + dt * ds["dv_a"],
        r_ref=s_base.r_ref + dt * ds["dr_ref"],
        v_ref=s_base.v_ref + dt * ds["dv_ref"],
        theta_hat=np.clip(s_base.theta_hat + dt * ds["dtheta"],
                           pp.THETA_MIN, pp.THETA_MAX),
        P=np.maximum(s_base.P + dt * ds["dP"], 0.0),
        last_u_safe=s_base.last_u_safe,        # frozen for this sub-step
        pair_active=s_base.pair_active,        # frozen for this outer step
        broadcast_history=s_base.broadcast_history,
    )


def _rk4_step(state: State,
              t_targets_fn: Callable[[float], np.ndarray],
              edges: tuple,
              A_e: float,
              omegas: np.ndarray,
              phases: np.ndarray,
              solver_cache: dict,
              use_safety_filter: bool = True,
              comm_delay: float = 0.0) -> tuple:
    """One RK4 step over h_outer."""
    h = pp.H_OUTER
    args = (t_targets_fn, edges, A_e, omegas, phases, solver_cache,
            use_safety_filter, comm_delay)

    d1, info_1 = _eval(state, *args)
    d2, _ = _eval(_shifted(state, d1, h / 2), *args)
    d3, _ = _eval(_shifted(state, d2, h / 2), *args)
    d4, _ = _eval(_shifted(state, d3, h), *args)

    # RK4 weighted average
    new_state = State(
        t=state.t + h,
        r=state.r + h / 6 * (d1["dr"] + 2 * d2["dr"] + 2 * d3["dr"] + d4["dr"]),
        v_a=_renormalise_velocity(
            state.v_a + h / 6 * (d1["dv_a"] + 2 * d2["dv_a"]
                                  + 2 * d3["dv_a"] + d4["dv_a"])
        ),
        r_ref=state.r_ref + h / 6 * (d1["dr_ref"] + 2 * d2["dr_ref"]
                                       + 2 * d3["dr_ref"] + d4["dr_ref"]),
        v_ref=_renormalise_velocity(
            state.v_ref + h / 6 * (d1["dv_ref"] + 2 * d2["dv_ref"]
                                    + 2 * d3["dv_ref"] + d4["dv_ref"])
        ),
        theta_hat=np.clip(
            state.theta_hat + h / 6 * (d1["dtheta"] + 2 * d2["dtheta"]
                                         + 2 * d3["dtheta"] + d4["dtheta"]),
            pp.THETA_MIN, pp.THETA_MAX,
        ),
        P=np.maximum(
            state.P + h / 6 * (d1["dP"] + 2 * d2["dP"] + 2 * d3["dP"] + d4["dP"]),
            0.0,
        ),
        # Update broadcast: use the K_1 (current state) u_2_safe — the most-recent
        # value at time t. Future RK4 sub-steps (next outer step) see this as t^-.
        last_u_safe=info_1["u_2_safe"].copy(),
        pair_active=state.pair_active,
        broadcast_history=state.broadcast_history,
    )
    return new_state, info_1


def run(r0: np.ndarray, v_a0: np.ndarray,
        r_ref0: np.ndarray, v_ref0: np.ndarray,
        edges: tuple,
        t_targets_fn: Callable[[float], np.ndarray],
        A_e: float,
        T_final: float,
        log_every: int = 1,
        use_safety_filter: bool = True,
        comm_delay: float = 0.0) -> dict:
    """Run a v17 complex-Dubins simulation from initial conditions.

    Parameters
    ----------
    r0, v_a0     : (N,) complex initial plant state. |v_a0[i]| should equal V_0.
    r_ref0       : (N,) complex initial reference position. Typically r_ref0 = r0.
    v_ref0       : (N,) complex initial reference velocity. Typically v_ref0 = v_a0.
    edges        : tuple of (i, j) pairs in the communication graph.
    t_targets_fn : callable t -> (N,) complex target positions for the formation.
    A_e          : PE injection amplitude (rad/s); 0 disables PE.
    T_final      : simulation horizon (s).
    log_every    : record every k-th outer step (default: every step).
    use_safety_filter : if False, bypass the QP and apply u_AC + PE only (clipped).
    comm_delay   : broadcast latency in seconds; 0 = continuous broadcast.

    Returns
    -------
    dict with keys: t, r, v_a, r_ref, v_ref, theta_hat, P, u_2_safe, u_2_ref,
                    h_pairs, active_count, pe_projected, bar_rho_i, edges,
                    phases, wall_time_s, n_steps.

    PE phases are drawn under seed pp.PE_SEED [paper §8.3].
    """
    N = r0.shape[0]
    rng = np.random.default_rng(pp.PE_SEED)
    phases = rng.uniform(0.0, 2.0 * np.pi, size=(N, 2))
    omegas = pp.pe_omegas(N)                       # (N, 2) staggered freqs

    # Initial state
    state = State(
        t=0.0,
        r=r0.copy().astype(complex),
        v_a=_renormalise_velocity(v_a0.copy().astype(complex)),
        r_ref=r_ref0.copy().astype(complex),
        v_ref=_renormalise_velocity(v_ref0.copy().astype(complex)),
        # Initial parameter estimate at midpoint of [theta_min, theta_max]
        theta_hat=0.5 * (pp.THETA_MIN + pp.THETA_MAX) * np.ones(N),
        # P_i(0) = (theta_max - theta_min)^2  [paper §2.5]
        P=(pp.THETA_MAX - pp.THETA_MIN) ** 2 * np.ones(N),
        last_u_safe=np.zeros(N),
        pair_active={frozenset({i, j}): False for (i, j) in edges},
        broadcast_history=[] if comm_delay > 0 else None,
    )

    n_steps = int(np.ceil(T_final / pp.H_OUTER))
    solver_cache: dict = {}

    log_t: list = []
    log_r: list = []
    log_v_a: list = []
    log_r_ref: list = []
    log_v_ref: list = []
    log_theta: list = []
    log_P: list = []
    log_u_safe: list = []
    log_u_ref: list = []
    log_h: list = []
    log_active_count: list = []
    log_pe: list = []

    # Running scalar Fisher info for §5.2 bar_rho_i:
    # bar_rho_i = E_mu[V_0^2 (u_2^ref)^2 / (1 + V_0^2 (u_2^ref)^2)
    #                  * 1{N_i^on = empty}]
    rho_running = np.zeros(N)
    rho_count = 0

    t_start = time.time()

    # Pre-size broadcast history buffer
    max_buf = (int(np.ceil(comm_delay / pp.H_OUTER)) + 4) if comm_delay > 0 else 0

    for step in range(n_steps):
        # Snapshot for comm-delay buffer (BEFORE stepping)
        if comm_delay > 0:
            state.broadcast_history.append(
                (state.t, state.r.copy(), state.v_a.copy(),
                 state.theta_hat.copy(), state.last_u_safe.copy())
            )
            if len(state.broadcast_history) > max_buf:
                state.broadcast_history = state.broadcast_history[-max_buf:]

        # RK4 step
        state, info = _rk4_step(state, t_targets_fn, edges, A_e, omegas, phases,
                                 solver_cache, use_safety_filter, comm_delay)

        # Hysteresis update once per outer step (rate-independent K-P operator)
        state.pair_active = dyn.update_hysteresis(
            state.r, state.v_a, state.theta_hat, info["u_2_safe"],
            state.pair_active, edges,
        )

        # Logging
        if step % log_every == 0:
            log_t.append(state.t)
            log_r.append(state.r.copy())
            log_v_a.append(state.v_a.copy())
            log_r_ref.append(state.r_ref.copy())
            log_v_ref.append(state.v_ref.copy())
            log_theta.append(state.theta_hat.copy())
            log_P.append(state.P.copy())
            log_u_safe.append(info["u_2_safe"].copy())
            log_u_ref.append(info["u_2_ref"].copy())
            h_pairs = np.array([dyn.cbf_h(state.r[i], state.r[j])
                                 for (i, j) in edges])
            log_h.append(h_pairs)
            log_active_count.append(
                sum(int(v) for v in state.pair_active.values())
            )
            log_pe.append(info["pe_projected"].copy())

            # Update running bar_rho_i
            rho_count += 1
            for i in range(N):
                any_active = any(state.pair_active.get(frozenset({i, j}), False)
                                  for j in dyn.neighbours(i, edges))
                if not any_active:
                    u2_ref_i = info["u_2_ref"][i]
                    num = pp.V_0 ** 2 * u2_ref_i ** 2
                    rho_running[i] += num / (1.0 + num)

    elapsed = time.time() - t_start
    bar_rho_i = rho_running / max(rho_count, 1)

    return {
        "wall_time_s": elapsed,
        "n_steps": n_steps,
        "t": np.array(log_t),
        "r": np.array(log_r),
        "v_a": np.array(log_v_a),
        "r_ref": np.array(log_r_ref),
        "v_ref": np.array(log_v_ref),
        "theta_hat": np.array(log_theta),
        "P": np.array(log_P),
        "u_2_safe": np.array(log_u_safe),
        "u_2_ref": np.array(log_u_ref),
        "h": np.array(log_h),
        "pe_projected": np.array(log_pe),
        "active_count": np.array(log_active_count),
        "bar_rho_i": bar_rho_i,
        "edges": edges,
        "phases": phases,
    }
