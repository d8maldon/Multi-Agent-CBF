"""Outer-loop RK4 integrator at h_outer = 5 ms [§3.3 + §8.3 timing].

The closed loop is the Moreau sweeping process [§3.2 line 118; Moreau 1977];
in continuous time we discretise via fixed-step RK4 using the inner QP solve
at each derivative evaluation.

Per [§3.3]:
    - Outer step h = 5 ms
    - Inner OSQP tolerance 1e-7
    - Numerical-scheme error: ||x_n - x(t_n)|| ≤ C1 h + C2 tol/h  [Brezis 1973 Cor 4.2]

Records every observable that the §8.4 figure plan needs, plus the running
joint-second-moment Q_i [§5 def line 219] for verifying the §8.2 number.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable

import numpy as np

from . import paper_params as pp
from . import dynamics as dyn
from . import qp_resolvent as qpr


@dataclass
class State:
    t: float
    x: np.ndarray            # (N, d) plant
    z: np.ndarray            # (N, d) reference model
    theta_hat: np.ndarray    # (N,)   parameter estimate
    P: np.ndarray            # (N,)   KB covariance
    pair_active: dict        # {frozenset({i,j}): bool}
    # Communication-delay buffer: history of recent x and theta_hat for each agent.
    # Indexed as broadcast_buffer[(t - delay) // h_outer] gives the delayed state.
    # We keep it as a list of (t, x, theta_hat) tuples on the same H_OUTER cadence;
    # when delay = 0 this is just the current state.
    broadcast_history: list = None


def _delayed_state(state: State, comm_delay: float) -> tuple:
    """Return (x_delayed, theta_delayed) corresponding to t - comm_delay.

    For comm_delay = 0, returns current state. Otherwise returns the
    historical broadcast snapshot at the appropriate index, or the
    initial broadcast if the delay exceeds available history.
    """
    if comm_delay <= 0.0 or not state.broadcast_history:
        return state.x, state.theta_hat
    target_t = state.t - comm_delay
    # Walk backwards through history to find the closest snapshot
    for (t_hist, x_hist, theta_hist) in reversed(state.broadcast_history):
        if t_hist <= target_t:
            return x_hist, theta_hist
    # Fallback: oldest snapshot we have
    t0, x0, th0 = state.broadcast_history[0]
    return x0, th0


def _eval(state: State, t_targets_fn: Callable[[float], np.ndarray],
          edges: tuple, A_e: float, omegas: np.ndarray, phases: np.ndarray,
          d: int, solver_cache: dict, use_safety_filter: bool = True,
          comm_delay: float = 0.0) -> tuple:
    """Compute u^safe and all derivatives at a state. Returns (deriv, info)."""
    N = state.x.shape[0]
    t_now = t_targets_fn(state.t)
    u_ref = dyn.reference_velocity(state.z, t_now, edges)
    u_AC = state.theta_hat[:, None] * u_ref

    # Communication-delayed broadcast: agent i sees x_j and theta_j as of (t - delay).
    # Agent i's OWN state (x_i, theta_i, u_AC_i) remains current.
    if comm_delay > 0.0:
        x_bcast, theta_bcast = _delayed_state(state, comm_delay)
        u_AC_bcast = theta_bcast[:, None] * dyn.reference_velocity(state.z, t_now, edges)
        # Agent i sees its own state current; neighbours delayed.
        # We splice: per-agent broadcast-view tensors built when needed.
    else:
        x_bcast, theta_bcast = state.x, state.theta_hat
        u_AC_bcast = u_AC

    def per_agent_view(i):
        """Each agent i sees (its own current state) + (delayed neighbours)."""
        x_view = x_bcast.copy()
        theta_view = theta_bcast.copy()
        u_AC_view = u_AC_bcast.copy()
        x_view[i] = state.x[i]
        theta_view[i] = state.theta_hat[i]
        u_AC_view[i] = u_AC[i]
        return x_view, theta_view, u_AC_view

    # Hysteretic active set [§3.1 line 92] — uses agent 0's view by default for
    # the global pair_active dict. Each pair (i, j) is symmetric in the c_ij
    # condition; with delays both agents see the same delayed-neighbour state.
    state.pair_active = dyn.update_hysteresis(
        x_bcast, theta_bcast, u_AC_bcast, state.pair_active, edges
    )

    # CBF tightening from KB filter [§2.1 line 84 + Lemma 5.2]
    delta_ij = {}
    for (i, j) in edges:
        D_max_est = float(np.linalg.norm(x_bcast[i] - x_bcast[j])) + 1e-3
        delta = max(dyn.cbf_tightening_delta(state.P[i], D_max_est, d),
                    dyn.cbf_tightening_delta(state.P[j], D_max_est, d))
        delta_ij[frozenset({i, j})] = delta

    # Per-agent: freedom-cone projection of PE injection [§3.2 line 102-104]
    u_safe = np.zeros((N, d))
    pe_proj = np.zeros((N, d))
    for i in range(N):
        x_view_i, theta_view_i, u_AC_view_i = per_agent_view(i)
        active_pairs = [j for j in dyn.neighbours(i, edges)
                        if state.pair_active.get(frozenset({i, j}), False)]
        normals = [x_view_i[i] - x_view_i[j] for j in active_pairs]
        normals_unit = [n / max(np.linalg.norm(n), 1e-12) for n in normals]
        F_proj = dyn.freedom_cone_projector(normals_unit, d)
        if A_e > 0:
            e_pe = dyn.excitation_signal(state.t, omegas[i], phases[i], A_e)
            pe_proj[i] = F_proj @ e_pe

        if use_safety_filter:
            u_i_safe, slacks_i, _ = qpr.solve_qp(
                i, x_view_i, theta_view_i, u_AC_view_i, pe_proj[i],
                state.pair_active, edges, delta_ij, solver_cache,
            )
            u_safe[i] = u_i_safe
        else:
            u_safe[i] = np.clip(u_AC[i] + pe_proj[i], -pp.U_MAX, pp.U_MAX)

    # Plant: dx/dt = Lambda u_safe   [§2 eq line 59]
    dx = pp.LAMBDA_TRUE[:, None] * u_safe
    # Reference: dz/dt = u^ref       [§2 eq line 65]
    dz = u_ref
    # Adaptive law and KB                [§2 eqs lines 64, 70]
    dtheta = dyn.adaptive_law_rate(state.theta_hat, state.x, state.z, u_ref)
    dP = dyn.kalman_bucy_riccati(state.P, u_ref)

    info = {"u_ref": u_ref, "u_AC": u_AC, "u_safe": u_safe,
            "pe_projected": pe_proj, "delta_ij": delta_ij}
    return {"dx": dx, "dz": dz, "dtheta": dtheta, "dP": dP}, info


def _rk4_step(state: State, t_targets_fn, edges: tuple, A_e: float,
              omegas: np.ndarray, phases: np.ndarray, d: int,
              solver_cache: dict, use_safety_filter: bool = True,
              comm_delay: float = 0.0) -> tuple:
    """One RK4 step over h_outer."""
    h = pp.H_OUTER
    usf = use_safety_filter

    def shifted(s_base: State, ds: dict, dt: float) -> State:
        return State(
            t=s_base.t + dt,
            x=s_base.x + dt * ds["dx"],
            z=s_base.z + dt * ds["dz"],
            theta_hat=np.clip(s_base.theta_hat + dt * ds["dtheta"],
                              pp.THETA_MIN, pp.THETA_MAX),
            P=np.maximum(s_base.P + dt * ds["dP"], 0.0),
            pair_active=s_base.pair_active,
            broadcast_history=s_base.broadcast_history,
        )

    d1, info_1 = _eval(state, t_targets_fn, edges, A_e, omegas, phases, d, solver_cache, usf, comm_delay)
    d2, _ = _eval(shifted(state, d1, h / 2), t_targets_fn, edges, A_e, omegas, phases, d, solver_cache, usf, comm_delay)
    d3, _ = _eval(shifted(state, d2, h / 2), t_targets_fn, edges, A_e, omegas, phases, d, solver_cache, usf, comm_delay)
    d4, _ = _eval(shifted(state, d3, h),     t_targets_fn, edges, A_e, omegas, phases, d, solver_cache, usf, comm_delay)

    new_state = State(
        t=state.t + h,
        x=state.x + h / 6 * (d1["dx"] + 2 * d2["dx"] + 2 * d3["dx"] + d4["dx"]),
        z=state.z + h / 6 * (d1["dz"] + 2 * d2["dz"] + 2 * d3["dz"] + d4["dz"]),
        theta_hat=np.clip(
            state.theta_hat + h / 6 * (d1["dtheta"] + 2 * d2["dtheta"]
                                       + 2 * d3["dtheta"] + d4["dtheta"]),
            pp.THETA_MIN, pp.THETA_MAX,
        ),
        P=np.maximum(
            state.P + h / 6 * (d1["dP"] + 2 * d2["dP"] + 2 * d3["dP"] + d4["dP"]),
            0.0,
        ),
        pair_active=state.pair_active,
        broadcast_history=state.broadcast_history,
    )
    return new_state, info_1


def run(x0: np.ndarray, z0: np.ndarray, edges: tuple,
        t_targets_fn: Callable[[float], np.ndarray],
        A_e: float, T_final: float, log_every: int = 1,
        use_safety_filter: bool = True, comm_delay: float = 0.0) -> dict:
    """Run a full simulation from initial conditions.

    PE phases are drawn under seed pp.PE_SEED [§8.3].
    """
    N, d = x0.shape
    rng = np.random.default_rng(pp.PE_SEED)
    phases = rng.uniform(0.0, 2.0 * np.pi, size=(N, 2))
    omegas = pp.pe_omegas(N)              # (N, 2) per-agent staggered frequencies

    state = State(
        t=0.0,
        x=x0.copy(),
        z=z0.copy(),
        # Initial estimate at midpoint of [theta_min, theta_max]
        theta_hat=0.5 * (pp.THETA_MIN + pp.THETA_MAX) * np.ones(N),
        # P_i(0) = (theta_max - theta_min)^2  [§2 line 74]
        P=(pp.THETA_MAX - pp.THETA_MIN) ** 2 * np.ones(N),
        pair_active={frozenset({i, j}): False for (i, j) in edges},
        broadcast_history=[],
    )

    n_steps = int(np.ceil(T_final / pp.H_OUTER))
    solver_cache = {}

    log_t, log_x, log_z, log_theta, log_P = [], [], [], [], []
    log_u_safe, log_u_ref = [], []
    log_h, log_active_count, log_pe = [], [], []
    Q_running = [np.zeros((d, d)) for _ in range(N)]
    Q_count = 0

    t_start = time.time()
    # Pre-size broadcast history buffer for max needed depth + small slack
    max_buf = int(np.ceil(comm_delay / pp.H_OUTER)) + 4 if comm_delay > 0 else 0

    for step in range(n_steps):
        # Append current snapshot BEFORE stepping forward (so the buffer
        # contains x at the current time t_now)
        if comm_delay > 0:
            state.broadcast_history.append((state.t, state.x.copy(), state.theta_hat.copy()))
            # Trim buffer to required depth
            if len(state.broadcast_history) > max_buf:
                state.broadcast_history = state.broadcast_history[-max_buf:]

        state, info = _rk4_step(state, t_targets_fn, edges, A_e, omegas, phases,
                                d, solver_cache, use_safety_filter, comm_delay)

        if step % log_every == 0:
            log_t.append(state.t)
            log_x.append(state.x.copy())
            log_z.append(state.z.copy())
            log_theta.append(state.theta_hat.copy())
            log_P.append(state.P.copy())
            log_u_safe.append(info["u_safe"].copy())
            log_u_ref.append(info["u_ref"].copy())
            h_pairs = np.array([dyn.cbf_h(state.x[i], state.x[j]) for (i, j) in edges])
            log_h.append(h_pairs)
            log_active_count.append(sum(int(v) for v in state.pair_active.values()))
            log_pe.append(info["pe_projected"].copy())

            # Update running Q_i: Pu Pu^T  using the same projector that was
            # actually active at this step.
            Q_count += 1
            for i in range(N):
                active_pairs = [j for j in dyn.neighbours(i, edges)
                                if state.pair_active.get(frozenset({i, j}), False)]
                normals = [state.x[i] - state.x[j] for j in active_pairs]
                normals_unit = [n / max(np.linalg.norm(n), 1e-12) for n in normals]
                F_proj = dyn.freedom_cone_projector(normals_unit, d)
                Pu = F_proj @ info["u_ref"][i]
                Q_running[i] += np.outer(Pu, Pu)

    elapsed = time.time() - t_start
    Q_avg = [Q / max(Q_count, 1) for Q in Q_running]

    return {
        "wall_time_s": elapsed,
        "n_steps": n_steps,
        "t": np.array(log_t),
        "x": np.array(log_x),
        "z": np.array(log_z),
        "theta_hat": np.array(log_theta),
        "P": np.array(log_P),
        "u_safe": np.array(log_u_safe),
        "u_ref": np.array(log_u_ref),
        "h": np.array(log_h),
        "pe_projected": np.array(log_pe),
        "active_count": np.array(log_active_count),
        "Q_i": Q_avg,
        "rho_bar_i": np.array([np.trace(Q) for Q in Q_avg]),
        "edges": edges,
        "phases": phases,
    }
