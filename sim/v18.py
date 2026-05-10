"""v18 plant: complex double-integrator with bounded acceleration + scalar LOE.

Council Pass 52 unanimous (math-god + OG + controls): drop the constant-speed
Dubins assumption. New plant:

    dot r_i = v_i,    dot v_i = lambda_i u_i

where r_i, v_i, u_i in C, u_i is the complex acceleration command,
|u_i| <= u_max (saturation), and lambda_i in [lambda_min, 1] is the scalar
LOE on the acceleration channel.

This is a Pontryagin (1962) bounded-acceleration double integrator on R^2,
NOT a Dubins vehicle. Naming honesty: drop "Dubins" from v18 manuscript title.

Closes Pass 43-49 failure modes structurally:
- Pass 43 highway / Pass 47 head-on obstacle: HOCBF input coefficient is
  2*lambda_i*(r_i - r_obs), a full complex vector — never zero unless
  r_i = r_obs (deep inside unsafe set). No relative-degree drop.
- Pass 45 multi-radius rotation: no constant-speed kinematic mismatch.
- Pass 49 static rendezvous: v_i = 0 is a valid equilibrium; vehicles can
  decelerate to a stop at target vertices.

Self-contained — does not import sim.dynamics, sim.integrator, sim.qp_resolvent
to keep v17 code path independent.
"""

from __future__ import annotations

import numpy as np
import scipy.sparse as sparse
import osqp


# ---------------------------------------------------------------------------
# v18 plant constants (council Pass 52)
# ---------------------------------------------------------------------------
U_MAX = 5.0           # acceleration saturation |u_i| <= u_max
                      # (per-component bound: |Re(u_i)|, |Im(u_i)| <= u_max)
R_SAFE = 0.4
ALPHA_1 = 5.0
ALPHA_2 = 5.0
EPS_HYST = 0.05 * R_SAFE ** 2
SLACK_PENALTY = 1e4
H_OUTER = 5e-3        # 5 ms outer step
LAMBDA_TRUE = np.array([0.6, 0.9, 0.7, 0.8])   # 4 agents heterogeneous LOE
THETA_MIN = 1.0
THETA_MAX = 2.0
GAMMA = 0.15          # Pomet-Praly adaptive gain (council Pass 57)
A_E_DEFAULT = 0.5     # PE amplitude (acceleration units)


# ---------------------------------------------------------------------------
# v18 CBF helpers (complex double-integrator)
# ---------------------------------------------------------------------------

def cbf_h(r_i: complex, r_j: complex, R_safety: float = None) -> float:
    """h_ij = |r_i - r_j|^2 - R^2 (R = R_safety or R_SAFE by default)."""
    R = R_safety if R_safety is not None else R_SAFE
    return float(np.abs(r_i - r_j) ** 2) - R ** 2


def hocbf_b0(r_i: complex, r_j: complex,
             v_i: complex, v_j: complex, h_val: float) -> float:
    """b0 (LOE-independent residual) of HOCBF for pair (i, j).

    Plant: dot v = lambda * u (double-integrator). The HOCBF requires
        psi_2 = ddot h + (alpha_1 + alpha_2) dot h + alpha_1*alpha_2*h >= 0
    where:
        h = |r_i-r_j|^2 - R^2
        dot h = 2 Re((r_i-r_j) conj(v_i-v_j))
        ddot h = 2|v_i-v_j|^2 + 2 Re((r_i-r_j) conj(lambda_i u_i - lambda_j u_j))

    The b0 (no-control) part:
        b0_ij = 2|v_i-v_j|^2 + 2(alpha_1+alpha_2)*Re((r_i-r_j)*conj(v_i-v_j))
                + alpha_1*alpha_2*h
    """
    return (2.0 * np.abs(v_i - v_j) ** 2
            + 2.0 * (ALPHA_1 + ALPHA_2) * np.real((r_i - r_j) * np.conj(v_i - v_j))
            + ALPHA_1 * ALPHA_2 * h_val)


def hocbf_jacobian_pair(r_i: complex, r_j: complex) -> complex:
    """Coefficient of (lambda_i u_i - lambda_j u_j) in psi_2 for pair (i, j).

    Specifically psi_2 = b0 + 2*Re((r_i-r_j)*conj(lambda_i u_i - lambda_j u_j)).
    The coefficient is the COMPLEX VECTOR 2*(r_i - r_j) — no relative-degree
    drop at any heading (council Pass 52 key property).

    Returns the complex coefficient z_{ij} = 2*(r_i - r_j) so the constraint
    contribution is: Re(z_{ij} * conj(lambda_i u_i - lambda_j u_j)).
    """
    return 2.0 * (r_i - r_j)


# v18 obstacle helpers (same form as inter-agent with v_obs = 0, lambda_obs = 0)

def cbf_h_obstacle(r_i: complex, r_obs: complex, r_obs_radius: float) -> float:
    return float(np.abs(r_i - r_obs) ** 2) - (R_SAFE + r_obs_radius) ** 2


def hocbf_b0_obstacle(r_i: complex, r_obs: complex, v_i: complex, h_val: float) -> float:
    """b0 for static obstacle (v_obs = 0)."""
    return (2.0 * np.abs(v_i) ** 2
            + 2.0 * (ALPHA_1 + ALPHA_2) * np.real((r_i - r_obs) * np.conj(v_i))
            + ALPHA_1 * ALPHA_2 * h_val)


def hocbf_jacobian_obstacle(r_i: complex, r_obs: complex) -> complex:
    """Coefficient of lambda_i u_i in psi_2 for static obstacle. Returns
    z_obs = 2*(r_i - r_obs)."""
    return 2.0 * (r_i - r_obs)


# ---------------------------------------------------------------------------
# v18 reference dynamics: PD on (position, velocity) -> acceleration command
# ---------------------------------------------------------------------------

def reference_acceleration(r: np.ndarray, v: np.ndarray, t_targets: np.ndarray,
                            t_targets_dot: np.ndarray = None,
                            obstacles: tuple = (),
                            K_p: float = 4.0, K_d: float = 4.0,
                            K_obs: float = 16.0,
                            K_rot: float = None,
                            v_terminal_fb: np.ndarray = None) -> np.ndarray:
    """Compute u_ref[i] = -K_p*(r_i - target_i) - K_d*v_i + obstacle field.

    Standard PD on position with velocity damping. With damping, vehicles
    DECELERATE as they approach the target — they can stop at v = 0.

    Obstacle field (Pass 61 council): a Khatib 1986 radial repulsion combined
    with a Khansari-Zadeh & Billard 2012 / Singletary-Ames 2020 *circulation
    component* (rotational potential field). The radial term alone creates
    a known PD+HOCBF deadlock at the bubble boundary (Reis-Aguiar-Silvestre
    2021 IEEE TAC: "CBF-QPs introduce undesirable asymptotically stable
    equilibria"). The rotational term adds tangential bias so the closed
    loop has no zero-velocity equilibria on the bubble boundary.

    Field per agent i, per obstacle k:
        F_radial = K_obs · overlap² · n_hat        (Khatib outward repulsion)
        F_circ   = K_rot · overlap² · (i·n_hat)·s  (CCW tangential bias,
                                                    s = ±1 chosen to align
                                                    with goal-direction)
    where n_hat = (r_i - r_obs)/|r_i - r_obs| and overlap = (r_inf - d)/r_inf.

    Default K_rot = K_obs (45° resultant): equal radial + tangential. Set to
    None to default to K_obs; set to 0.0 to disable circulation (legacy mode).
    """
    if K_rot is None:
        K_rot = K_obs
    N = r.shape[0]
    u_ref = np.zeros(N, dtype=complex)
    for i in range(N):
        u_ref[i] = -K_p * (r[i] - t_targets[i]) - K_d * v[i]
        if t_targets_dot is not None:
            u_ref[i] += K_d * t_targets_dot[i]
        # Optional terminal-heading velocity feedforward: a state-dependent
        # desired velocity that steers v toward d_hat_terminal as the agent
        # enters a gaussian shell around its target. Decays to 0 at the
        # target so static rendezvous is preserved while the LAST commanded
        # direction equals the prescribed terminal heading.
        if v_terminal_fb is not None:
            u_ref[i] += K_d * v_terminal_fb[i]
    # Saturate PD term FIRST, leaving headroom for obstacle field. This avoids
    # the per-component clipping washing out the (smaller) circulation signal
    # when the saturated PD already fills the budget — diagnosed Pass 61.
    # Pass 62 fix: cap PD direction to u_PD_cap so circulation is preserved.
    u_PD_cap = U_MAX * 0.5
    for i in range(N):
        pd_mag = float(np.abs(u_ref[i]))
        if pd_mag > u_PD_cap:
            u_ref[i] = u_ref[i] * (u_PD_cap / pd_mag)

    if obstacles:
        for i in range(N):
            # PD goal direction (used to disambiguate CCW vs CW circulation)
            goal_dir = t_targets[i] - r[i]
            for (r_obs, r_obs_radius) in obstacles:
                d_vec = r[i] - r_obs
                d = float(np.abs(d_vec))
                r_inf = 2.5 * (r_obs_radius + R_SAFE)
                if d < r_inf and d > 1e-6:
                    overlap = max(r_inf - d, 0.0) / r_inf
                    n_hat = d_vec / d              # outward unit vector
                    # Radial repulsion (Khatib 1986)
                    u_ref[i] += K_obs * overlap ** 2 * n_hat
                    # Circulation: pick CCW or CW so that the tangential
                    # component aligns with the vehicle's goal direction
                    # (avoids reversing direction of motion).
                    t_hat_ccw = 1j * n_hat         # 90° CCW from n_hat
                    sign = +1.0 if (goal_dir.conjugate() * t_hat_ccw).real > 0 else -1.0
                    u_ref[i] += K_rot * overlap ** 2 * (sign * t_hat_ccw)
    # Final saturation: radial (norm-ball) preserves direction
    for i in range(N):
        m = float(np.abs(u_ref[i]))
        if m > U_MAX:
            u_ref[i] = u_ref[i] * (U_MAX / m)
    return u_ref


# ---------------------------------------------------------------------------
# v18 QP-resolvent
# ---------------------------------------------------------------------------

def solve_qp_v18(i: int, r: np.ndarray, v: np.ndarray, theta_hat: np.ndarray,
                 u_AC: np.ndarray, pe_projected_i: complex,
                 pair_active: dict, edges: tuple, delta_ij: dict,
                 solver_cache: dict, obstacles: tuple = ()) -> tuple:
    """v18 QP-resolvent with 2D acceleration control.

    Decision variable: x = (u_re, u_im, s_1, ..., s_K) where K = number of
    active constraints (pairs + obstacles). Slacks s_k >= 0 absorb deficits.

    Cost: 0.5 (u - target)^2 + M * sum s_k^2
    Constraints:
        - Pairwise HOCBF: Re(z_ij * conj(theta_i u_i - cross_term)) + s_k >= delta - b0
        - Obstacle HOCBF: Re(z_obs * conj(theta_i u_i)) + s_k >= -b0_obs
        - Saturation: |u_re|, |u_im| <= U_MAX
        - Slacks: s_k >= 0
    """
    target_re = float(u_AC[i].real + pe_projected_i.real)
    target_im = float(u_AC[i].imag + pe_projected_i.imag)

    active_pairs = [j for j in _neighbours(i, edges)
                    if pair_active.get(frozenset({i, j}), False)]
    K_pair = len(active_pairs)
    K_obs = len(obstacles)
    K_total = K_pair + K_obs
    n = 2 + K_total   # 2 (u_re, u_im) + slacks

    # Hessian: P = diag(2, 2, 2M, 2M, ..., 2M)
    P_diag = np.concatenate([[2.0, 2.0], 2.0 * SLACK_PENALTY * np.ones(K_total)])
    P_mat = sparse.diags(P_diag).tocsc()
    # Linear cost: from (u - target)^2 = u^2 - 2*target*u + const
    q_vec = np.concatenate([[-2.0 * target_re, -2.0 * target_im],
                             np.zeros(K_total)])

    rows = []
    l_vec = []
    u_vec = []

    # Pairwise HOCBF (one per active pair)
    for k_idx, j in enumerate(active_pairs):
        h_val = cbf_h(r[i], r[j])
        b0 = hocbf_b0(r[i], r[j], v[i], v[j], h_val)
        z_ij = hocbf_jacobian_pair(r[i], r[j])

        # Constraint: Re(z_ij * conj(theta_i u_i)) - Re(z_ij * conj(theta_j u_j_AC))
        #             + theta_i*b0 + s_k >= delta_ij
        # (i.e., theta absorbs into the inequality on the LHS)
        # Re(z * conj(u)) = Re(z)*Re(u) + Im(z)*Im(u)
        coef_re = float(np.real(z_ij)) * float(theta_hat[i])
        coef_im = float(np.imag(z_ij)) * float(theta_hat[i])
        # Cross-term: neighbour j's known u_AC contribution
        # Re(z_ij * conj(theta_j u_j_AC)) where u_j_AC is the broadcast value
        cross_term = (float(theta_hat[j]) *
                       (float(np.real(z_ij)) * float(u_AC[j].real)
                        + float(np.imag(z_ij)) * float(u_AC[j].imag)))
        rhs_const = (delta_ij.get(frozenset({i, j}), 0.0)
                     + cross_term
                     - float(theta_hat[i]) * b0)

        row = np.zeros(n)
        row[0] = coef_re
        row[1] = coef_im
        row[2 + k_idx] = 1.0    # +slack
        rows.append(row)
        l_vec.append(rhs_const)
        u_vec.append(np.inf)

    # Obstacle HOCBF (one per obstacle, no cross-term, no theta_j)
    for o_idx, (r_obs, r_obs_radius) in enumerate(obstacles):
        h_obs = cbf_h_obstacle(r[i], r_obs, r_obs_radius)
        b0_obs = hocbf_b0_obstacle(r[i], r_obs, v[i], h_obs)
        z_obs = hocbf_jacobian_obstacle(r[i], r_obs)
        coef_re = float(np.real(z_obs)) * float(theta_hat[i])
        coef_im = float(np.imag(z_obs)) * float(theta_hat[i])
        rhs_const = -float(theta_hat[i]) * b0_obs

        row = np.zeros(n)
        row[0] = coef_re
        row[1] = coef_im
        row[2 + K_pair + o_idx] = 1.0
        rows.append(row)
        l_vec.append(rhs_const)
        u_vec.append(np.inf)

    # Slack >= 0
    for k_idx in range(K_total):
        row = np.zeros(n)
        row[2 + k_idx] = 1.0
        rows.append(row)
        l_vec.append(0.0)
        u_vec.append(np.inf)

    # Saturation: |u_re|, |u_im| <= U_MAX
    row_re = np.zeros(n); row_re[0] = 1.0
    row_im = np.zeros(n); row_im[1] = 1.0
    rows.extend([row_re, row_im])
    l_vec.extend([-U_MAX, -U_MAX])
    u_vec.extend([U_MAX, U_MAX])

    A_mat = sparse.csc_matrix(np.array(rows))
    l_arr = np.array(l_vec)
    u_arr = np.array(u_vec)

    cache_key = (i, tuple(active_pairs), K_obs)
    cached = solver_cache.get(cache_key)
    if cached is None:
        prob = osqp.OSQP()
        prob.setup(P_mat, q_vec, A_mat, l_arr, u_arr,
                   eps_abs=1e-7, eps_rel=1e-7,
                   max_iter=20000, verbose=False, polishing=False,
                   warm_starting=True)
        solver_cache[cache_key] = prob
    else:
        prob = cached
        prob.update(q=q_vec, l=l_arr, u=u_arr)

    res = prob.solve()
    if res.info.status_val not in (1, 2):
        # Fallback: clipped target
        u_safe_fallback = (np.clip(target_re, -U_MAX, U_MAX)
                            + 1j * np.clip(target_im, -U_MAX, U_MAX))
        return u_safe_fallback, np.zeros(K_total), f"FALLBACK ({res.info.status})"

    u_re = float(res.x[0])
    u_im = float(res.x[1])
    return u_re + 1j * u_im, res.x[2:].copy(), res.info.status


def _neighbours(i: int, edges: tuple) -> list:
    return [j if i == ie else ie for (ie, j) in edges if i in (ie, j)]


# ---------------------------------------------------------------------------
# v18 hysteresis update (similar form to v17 but with new HOCBF coefficient)
# ---------------------------------------------------------------------------

def update_hysteresis(r: np.ndarray, v: np.ndarray, theta_hat: np.ndarray,
                      u_AC: np.ndarray, pair_active_in: dict,
                      edges: tuple) -> dict:
    """Hysteretic active-set: engage when c_ij <= eps, disengage when
    c_ij >= 2*eps."""
    new_active = dict(pair_active_in)
    for (i, j) in edges:
        h_val = cbf_h(r[i], r[j])
        b0 = hocbf_b0(r[i], r[j], v[i], v[j], h_val)
        z_ij = hocbf_jacobian_pair(r[i], r[j])
        c_re = float(np.real(z_ij)) * float(theta_hat[i])
        c_im = float(np.imag(z_ij)) * float(theta_hat[i])
        # c at u = u_AC[i] (no slack, ignoring cross-term for hysteresis check)
        c_ij = (c_re * float(u_AC[i].real) + c_im * float(u_AC[i].imag)
                + float(theta_hat[i]) * b0)
        key = frozenset({i, j})
        if new_active.get(key, False):
            if c_ij >= 2 * EPS_HYST:
                new_active[key] = False
        else:
            if c_ij <= EPS_HYST:
                new_active[key] = True
    return new_active


# ---------------------------------------------------------------------------
# v18 Pomet-Praly adaptive law (council Pass 57)
# ---------------------------------------------------------------------------

def adaptive_law_rate_v18(theta_hat: np.ndarray, v: np.ndarray, v_ref: np.ndarray,
                           u_ref: np.ndarray, gamma: float = None) -> np.ndarray:
    """Pomet-Praly normalised swapped-signal adaptive law for v18 plant
    (dot v = lambda u). The regressor is u_ref directly (acceleration channel
    LOE), distinct from v17's i*v_a*u_2_ref turn-rate regressor.

        d theta_hat_i / dt = Proj_[theta_min, theta_max](
            -(gamma / m_i^2) * Re(conj(u_ref_i) * tilde_v_i)
        )
        m_i^2 = 1 + |u_ref_i|^2
        tilde_v_i = v_i - v_ref_i

    Smooth-projection convention: rate clipped to zero when at boundary and
    sign of raw rate would push outside [theta_min, theta_max].
    """
    g = GAMMA if gamma is None else gamma
    N = theta_hat.shape[0]
    rates = np.zeros(N)
    tilde_v = v - v_ref
    for i in range(N):
        m_sq = 1.0 + float(np.abs(u_ref[i]) ** 2)
        raw = -(g / m_sq) * float(np.real(np.conj(u_ref[i]) * tilde_v[i]))
        if theta_hat[i] <= THETA_MIN and raw < 0:
            rates[i] = 0.0
        elif theta_hat[i] >= THETA_MAX and raw > 0:
            rates[i] = 0.0
        else:
            rates[i] = raw
    return rates


# ---------------------------------------------------------------------------
# v18 PE injection (staggered sinusoidal dither, council Pass 57)
# ---------------------------------------------------------------------------

def make_pe_injector(N: int, A_e: float = A_E_DEFAULT,
                     T_PE_start: float = 0.0,
                     T_PE: float = float("inf"),
                     seed: int = 42) -> callable:
    """Per-agent staggered PE: xi_i^PE(t) = A_e * sum_k sin(omega_i^k t + phi_i^k).

    Two frequencies per agent. omega_i^k = 2*pi*(0.7 + 0.2*i + 0.1*(k-1)) Hz
    (irrationally-related across agents, ensures Wald (W+) recurrent excitation).
    Cruise-PE-cooldown: PE active on [T_PE_start, T_PE], identically zero
    elsewhere. The early phase t < T_PE_start is the rendezvous-without-PE
    transient (so the LOE-driven adaptation operates near the equilibrium).
    """
    rng = np.random.default_rng(seed)
    omegas = np.zeros((N, 2))
    phases = np.zeros((N, 2))
    for i in range(N):
        for k in range(2):
            omegas[i, k] = 2.0 * np.pi * (0.7 + 0.2 * i + 0.1 * k)
            phases[i, k] = float(rng.uniform(0, 2 * np.pi))

    def xi(t: float) -> np.ndarray:
        if t < T_PE_start or t >= T_PE:
            return np.zeros(N, dtype=complex)
        out = np.zeros(N, dtype=complex)
        for i in range(N):
            re = A_e * float(np.sin(omegas[i, 0] * t + phases[i, 0]))
            im = A_e * float(np.sin(omegas[i, 1] * t + phases[i, 1]))
            out[i] = re + 1j * im
        return out

    return xi


# ---------------------------------------------------------------------------
# v18 integrator (RK4 on r, v with no |v|=V_0 normalisation)
# ---------------------------------------------------------------------------

def run(r0: np.ndarray, v0: np.ndarray,
        edges: tuple,
        t_targets_fn,
        T_final: float,
        K_p: float = 4.0, K_d: float = 4.0, K_obs: float = 16.0,
        obstacles: tuple = (),
        use_safety_filter: bool = True,
        adaptive: bool = False,
        A_e: float = 0.0,
        T_PE_start: float = 0.0,
        T_PE: float = float("inf"),
        gamma: float = None,
        v_terminal_fn=None,
        target_offset_fn=None,
        log_every: int = 1) -> dict:
    """Run a v18 simulation from initial conditions.

    State: (r, v) in C^N x C^N. Plant: dot r = v, dot v = lambda * u.
    Reference: PD on (r, v) toward target. Safety filter modifies u via QP.

    Optional council Pass 57 extensions:
        adaptive=True : evolve theta_hat via Pomet-Praly + integrate (r_ref,
                        v_ref) reference model with lambda=1.
        A_e>0          : PE injection xi^PE(t) added to u_ref; sustained on
                        [0, T_PE], identically zero after (dither-then-cruise).
    """
    N = r0.shape[0]
    r = r0.copy().astype(complex)
    v = v0.copy().astype(complex)
    # Reference model: same target dynamics with lambda = 1 (no LOE).
    # Initial conditions match the plant; tilde_v starts at zero.
    r_ref = r0.copy().astype(complex) if adaptive else None
    v_ref = v0.copy().astype(complex) if adaptive else None
    theta_hat = 0.5 * (THETA_MIN + THETA_MAX) * np.ones(N)
    pair_active = {frozenset({i, j}): False for (i, j) in edges}
    solver_cache: dict = {}

    pe_inject = (make_pe_injector(N, A_e=A_e, T_PE_start=T_PE_start, T_PE=T_PE)
                 if A_e > 0 else None)

    h_outer = H_OUTER
    n_steps = int(np.ceil(T_final / h_outer))

    log_t: list = []
    log_r: list = []
    log_v: list = []
    log_u_safe: list = []
    log_u_AC: list = []
    log_h: list = []
    log_h_obs: list = []
    log_active: list = []
    log_theta: list = []
    log_r_ref: list = []
    log_v_ref: list = []
    log_u_ref: list = []
    log_pe: list = []

    lambda_arr = LAMBDA_TRUE[:N]

    def compute_u_ref_at(state_r, state_v, t_now):
        """PD reference + (optional) PE injection at the given (r, v) state.

        IMPORTANT: this is computed at the CALLER's state (plant or reference
        model). The reference model has its own closed-loop PD so it remains
        bounded and provides a well-defined target trajectory for tilde_v.

        State-dependent target offset (target_offset_fn): shifts the PD aim
        point as a function of state, so the path can curve to approach
        each target tangent to a prescribed direction (e.g., the CW pinwheel
        terminal heading on the diamond demo). The offset → 0 as r → target,
        so static rendezvous is preserved.
        """
        t_targets = t_targets_fn(t_now)
        eps = 1e-3
        t_dot = (t_targets_fn(t_now + eps) - t_targets_fn(t_now - eps)) / (2.0 * eps)
        if target_offset_fn is not None:
            offset = target_offset_fn(state_r, t_now)
            t_targets = t_targets + offset
        v_term_fb = None
        if v_terminal_fn is not None:
            v_term_fb = v_terminal_fn(state_r, t_now)
        u_ref = reference_acceleration(state_r, state_v, t_targets,
                                        t_targets_dot=t_dot,
                                        obstacles=obstacles,
                                        K_p=K_p, K_d=K_d, K_obs=K_obs,
                                        v_terminal_fb=v_term_fb)
        if pe_inject is not None:
            u_ref = u_ref + pe_inject(t_now)
            u_ref_re = np.clip(u_ref.real, -U_MAX, U_MAX)
            u_ref_im = np.clip(u_ref.imag, -U_MAX, U_MAX)
            u_ref = u_ref_re + 1j * u_ref_im
        return u_ref

    def deriv(state_r, state_v, state_r_ref, state_v_ref,
              state_theta, t_now):
        # Plant control: u_ref evaluated at PLANT state, AC scales by theta_hat.
        u_ref_plant = compute_u_ref_at(state_r, state_v, t_now)
        u_AC = state_theta * u_ref_plant
        u_safe = np.zeros(N, dtype=complex)
        if use_safety_filter:
            for ag in range(N):
                u_i_safe, _, _ = solve_qp_v18(
                    ag, state_r, state_v, state_theta, u_AC, 0.0+0j,
                    pair_active, edges, {}, solver_cache, obstacles=obstacles,
                )
                u_safe[ag] = u_i_safe
        else:
            u_safe_re = np.clip(u_AC.real, -U_MAX, U_MAX)
            u_safe_im = np.clip(u_AC.imag, -U_MAX, U_MAX)
            u_safe = u_safe_re + 1j * u_safe_im
        dr = state_v.copy()
        dv = lambda_arr * u_safe
        if state_r_ref is not None:
            # Reference model: closed-loop PD on REFERENCE state with lambda=1
            # and identical PE injection. Both plant and reference model share
            # the PD law structure; tilde_v = v - v_ref measures pure LOE error.
            u_ref_M = compute_u_ref_at(state_r_ref, state_v_ref, t_now)
            dr_ref = state_v_ref.copy()
            dv_ref = u_ref_M
            # Adaptive law gated to PE-active window: avoids transient nonlinear
            # regime where PD-driven plant/reference state mismatch can produce
            # wrong-sign correlation. During [T_PE_start, T_PE] the system is
            # near equilibrium and PE drives the regressor cleanly.
            if T_PE_start <= t_now < T_PE:
                d_theta = adaptive_law_rate_v18(state_theta, state_v,
                                                  state_v_ref, u_ref_M,
                                                  gamma=gamma)
            else:
                d_theta = np.zeros(N)
        else:
            dr_ref = None
            dv_ref = None
            d_theta = np.zeros(N)
        return dr, dv, dr_ref, dv_ref, d_theta, u_safe, u_AC, u_ref_plant

    pe_started = False
    for step_idx in range(n_steps):
        t_now = step_idx * h_outer

        # Sync reference model to plant at start of PE window (so tilde_v
        # starts at zero in the cruise phase and the adaptive law sees pure
        # PE-driven LOE response without transient contamination).
        if adaptive and (not pe_started) and t_now >= T_PE_start:
            r_ref = r.copy()
            v_ref = v.copy()
            pe_started = True

        # Hysteresis update (once per outer step)
        u_ref_now = compute_u_ref_at(r, v, t_now)
        u_AC_now = theta_hat * u_ref_now
        pair_active = update_hysteresis(r, v, theta_hat, u_AC_now, pair_active, edges)

        # RK4 over (r, v) and optionally (r_ref, v_ref, theta_hat)
        d1_r, d1_v, d1_rref, d1_vref, d1_th, u_safe_step, u_AC_step, u_ref_step = \
            deriv(r, v, r_ref, v_ref, theta_hat, t_now)
        if adaptive:
            d2_r, d2_v, d2_rref, d2_vref, d2_th, *_ = deriv(
                r + h_outer/2 * d1_r, v + h_outer/2 * d1_v,
                r_ref + h_outer/2 * d1_rref, v_ref + h_outer/2 * d1_vref,
                theta_hat + h_outer/2 * d1_th, t_now + h_outer/2)
            d3_r, d3_v, d3_rref, d3_vref, d3_th, *_ = deriv(
                r + h_outer/2 * d2_r, v + h_outer/2 * d2_v,
                r_ref + h_outer/2 * d2_rref, v_ref + h_outer/2 * d2_vref,
                theta_hat + h_outer/2 * d2_th, t_now + h_outer/2)
            d4_r, d4_v, d4_rref, d4_vref, d4_th, *_ = deriv(
                r + h_outer * d3_r, v + h_outer * d3_v,
                r_ref + h_outer * d3_rref, v_ref + h_outer * d3_vref,
                theta_hat + h_outer * d3_th, t_now + h_outer)
            r_ref = r_ref + h_outer/6 * (d1_rref + 2*d2_rref + 2*d3_rref + d4_rref)
            v_ref = v_ref + h_outer/6 * (d1_vref + 2*d2_vref + 2*d3_vref + d4_vref)
            theta_hat = theta_hat + h_outer/6 * (d1_th + 2*d2_th + 2*d3_th + d4_th)
            theta_hat = np.clip(theta_hat, THETA_MIN, THETA_MAX)
        else:
            d2_r, d2_v, *_ = deriv(r + h_outer/2 * d1_r, v + h_outer/2 * d1_v,
                                    None, None, theta_hat, t_now + h_outer/2)
            d3_r, d3_v, *_ = deriv(r + h_outer/2 * d2_r, v + h_outer/2 * d2_v,
                                    None, None, theta_hat, t_now + h_outer/2)
            d4_r, d4_v, *_ = deriv(r + h_outer * d3_r, v + h_outer * d3_v,
                                    None, None, theta_hat, t_now + h_outer)
        r = r + h_outer/6 * (d1_r + 2*d2_r + 2*d3_r + d4_r)
        v = v + h_outer/6 * (d1_v + 2*d2_v + 2*d3_v + d4_v)

        if step_idx % log_every == 0:
            log_t.append(t_now)
            log_r.append(r.copy())
            log_v.append(v.copy())
            log_u_safe.append(u_safe_step.copy())
            log_u_AC.append(u_AC_step.copy())
            log_u_ref.append(u_ref_step.copy())
            if pe_inject is not None:
                log_pe.append(pe_inject(t_now))
            h_pair = np.array([cbf_h(r[ie], r[je]) for (ie, je) in edges])
            log_h.append(h_pair)
            if obstacles:
                h_obs_list = []
                for ag in range(N):
                    for (r_obs, r_obs_rad) in obstacles:
                        h_obs_list.append(cbf_h_obstacle(r[ag], r_obs, r_obs_rad))
                log_h_obs.append(np.array(h_obs_list))
            log_active.append(sum(int(v_) for v_ in pair_active.values()))
            log_theta.append(theta_hat.copy())
            if adaptive:
                log_r_ref.append(r_ref.copy())
                log_v_ref.append(v_ref.copy())

    out = {
        "t": np.array(log_t),
        "r": np.array(log_r),
        "v": np.array(log_v),
        "u_safe": np.array(log_u_safe),
        "u_AC": np.array(log_u_AC),
        "u_ref": np.array(log_u_ref),
        "h": np.array(log_h),
        "h_obs": np.array(log_h_obs) if log_h_obs else np.zeros((len(log_t), 0)),
        "active_count": np.array(log_active),
        "theta_hat": np.array(log_theta),
        "edges": edges,
        "obstacles": obstacles,
        "lambda_true": lambda_arr.copy(),
    }
    if adaptive:
        out["r_ref"] = np.array(log_r_ref)
        out["v_ref"] = np.array(log_v_ref)
    if log_pe:
        out["pe"] = np.array(log_pe)
    return out
