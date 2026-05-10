"""v18 diamond rendezvous demo (council Pass 52 binding example).

4 vehicles start at outer-square corners, must reach a STATIC diamond
formation around a central obstacle. With the v18 double-integrator
kinematics, vehicles can decelerate to v=0 at their assigned vertices —
so a static rendezvous IS achievable (unlike the constant-speed Dubins
of v17 which was Poincaré-Bendixson-blocked at static targets).
"""

from __future__ import annotations

import time
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.patches import Polygon
import numpy as np

from sim import v18


def _vehicle_body_xy(r_center: complex, heading: complex,
                      length: float = 0.45, width: float = 0.28):
    """Return (xs, ys) arrays for a chevron-shaped vehicle body pointed in
    the heading direction. Acts like a small aircraft icon:
        - Tip (nose) at center + length * heading_hat
        - Back-left/right at center - 0.5*length*heading_hat ± 0.5*width*(i*heading_hat)
    Heading must be a non-zero complex; if zero, defaults to +x.
    """
    h = heading
    hmag = float(np.abs(h))
    if hmag < 1e-6:
        h_hat = 1.0 + 0.0j
    else:
        h_hat = h / hmag
    perp = 1j * h_hat   # 90° CCW perpendicular
    nose = r_center + length * h_hat
    back_l = r_center - 0.5 * length * h_hat + 0.5 * width * perp
    tail = r_center - 0.65 * length * h_hat
    back_r = r_center - 0.5 * length * h_hat - 0.5 * width * perp
    pts = np.array([
        [nose.real, nose.imag],
        [back_l.real, back_l.imag],
        [tail.real, tail.imag],
        [back_r.real, back_r.imag],
    ])
    return pts


HERE = Path(__file__).resolve().parent
OUT_FIG = HERE / "output" / "v18"
OUT_GIF = HERE / "output" / "gifs"
OUT_FIG.mkdir(parents=True, exist_ok=True)
OUT_GIF.mkdir(parents=True, exist_ok=True)


# 4 vehicles at outer-square corners; targets at diamond vertices
DIAMOND_R0 = np.array([
    -5.0 - 5.0j,
    +5.0 - 5.0j,
    +5.0 + 5.0j,
    -5.0 + 5.0j,
], dtype=complex)
DIAMOND_TARGETS = np.array([
    0.0 + 3.0j,    # v0: SW (-5,-5) -> N vertex
    -3.0 + 0.0j,   # v1: SE (+5,-5) -> W vertex
    0.0 - 3.0j,    # v2: NE (+5,+5) -> S vertex
    +3.0 + 0.0j,   # v3: NW (-5,+5) -> E vertex
], dtype=complex)
# Terminal heading directions (CW pinwheel at the final formation):
#   v0 at N points toward E (rightmost)   -> SE direction
#   v1 at W points toward N (topmost)     -> NE direction
#   v2 at S points toward W (leftmost)    -> NW direction
#   v3 at E points toward S (bottommost)  -> SW direction
# Each row is the unit complex vector for the final velocity direction.
TERMINAL_HEADINGS = np.array([
    (1.0 - 1.0j) / np.sqrt(2.0),   # v0: SE
    (1.0 + 1.0j) / np.sqrt(2.0),   # v1: NE
    (-1.0 + 1.0j) / np.sqrt(2.0),  # v2: NW
    (-1.0 - 1.0j) / np.sqrt(2.0),  # v3: SW
], dtype=complex)
DIAMOND_EDGES = ((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3))   # K_4
OBSTACLES = (
    # Council Pass 53/54/55 Fix-A: central obstacle r_obs=0.5
    (0.0 + 0.0j, 0.5),
    # Council Pass 60-62: 4 corner obstacles at corners of [-3,3]^2.
    # Pure-radial Khatib at this geometry deadlocks the closed loop at
    # the bubble boundary (Reis-Aguiar-Silvestre 2021 IEEE TAC: "CBF-QPs
    # introduce undesirable asymptotically stable equilibria"). Pass 62
    # fix: circulation-embedded reference (Khansari-Zadeh & Billard 2012
    # modulation; Singletary-Klingebiel-Bourne-Browning-Ames 2020) adds
    # tangential bias near each obstacle, breaking the deadlock.
    (-3.0 - 3.0j, 0.5),
    ( 3.0 - 3.0j, 0.5),
    ( 3.0 + 3.0j, 0.5),
    (-3.0 + 3.0j, 0.5),
)


def diamond_targets_static(t: float) -> np.ndarray:
    """STATIC diamond targets — feasible at v18 because vehicles can decelerate."""
    return DIAMOND_TARGETS.copy()


def diamond_targets_with_terminal_approach(t: float) -> np.ndarray:
    """Smooth two-phase moving-target trajectory for the diamond demo,
    achieving CW pinwheel terminal heading via curved approach.

    Phase 1 (0 < t < T_p1): smoothstep from r_start_i to
                            r_pre_i = r_target_i - L_aim * d_hat_terminal_i.
    Phase 2 (T_p1 < t < T_p2): smoothstep from r_pre_i to r_target_i
                                (motion along +d_hat). The smoothstep
                                profile s(τ) = 3τ²-2τ³ has ds/dτ = 0 at
                                both endpoints, so target velocity is zero
                                at the start and end of each phase. This
                                eliminates overshoot: vehicle's velocity
                                gracefully ramps up to a peak along d_hat
                                in the middle of Phase 2, then ramps back
                                to zero by t = T_p2. Last meaningful
                                direction = +d_hat → chevron faces d_hat
                                at arrival, naturally.
    Phase 3 (t > T_p2): stationary at r_target_i.
    """
    T_p1 = 5.0
    T_p2 = 11.0          # 6s Phase 2 → peak target vel ≈ L_aim*1.5/6 = 0.4 m/s
    L_aim = 1.6
    r_pre = DIAMOND_TARGETS - L_aim * TERMINAL_HEADINGS
    if t <= 0.0:
        return DIAMOND_R0.copy()
    if t < T_p1:
        tau = t / T_p1
        s = tau * tau * (3.0 - 2.0 * tau)   # smoothstep
        return (1.0 - s) * DIAMOND_R0 + s * r_pre
    if t < T_p2:
        tau = (t - T_p1) / (T_p2 - T_p1)
        s = tau * tau * (3.0 - 2.0 * tau)
        return (1.0 - s) * r_pre + s * DIAMOND_TARGETS
    return DIAMOND_TARGETS.copy()


def diamond_target_offset_fn(r_now: np.ndarray, t_now: float) -> np.ndarray:
    """Carrot-on-stick state-dependent target offset for the diamond demo.

    Returns a per-vehicle complex position offset such that the AC reference
    aims at (r_target_i + offset_i) instead of r_target_i. The offset is
    designed so vehicles approach along the prescribed d_hat_terminal_i
    direction (a CW pinwheel around the diamond), producing a SMOOTH
    CURVED path with no curl/loop at the target.

    Specifically:
        offset_i(r) = -L_aim * d_hat_terminal_i * f(d_i)
    where d_i = |r_i - r_target_i| and f is a smooth bump that:
        - is ~1 when vehicle is in an intermediate annulus (d ∈ [d_near, d_far])
        - is 0 when vehicle is at target (d → 0)
        - is 0 when vehicle is very far (d → ∞)

    Mechanism: when vehicle is far, aim point is shifted BEHIND the target
    along -d_hat. Vehicle drives toward this offset point. As vehicle gets
    closer to its target, the offset shrinks → aim transitions to the actual
    target. The last leg of the path is along +d_hat direction.

    Vehicle arrives at r_target with velocity tangent to d_hat (smooth
    approach), no curl. After arrival, PD pulls v → 0 along the d_hat
    direction. Chevron stays oriented along d_hat. Physically honest.
    """
    L_aim = 2.5     # m, peak offset magnitude
    d_peak = 2.5    # m, distance from target where offset peaks
    sigma = 1.5     # m, bump width
    offset = np.zeros_like(TERMINAL_HEADINGS)
    for i in range(len(DIAMOND_TARGETS)):
        d = float(np.abs(r_now[i] - DIAMOND_TARGETS[i]))
        # Smooth bump: peaks at d_peak, zero at d=0 and d>>d_peak+sigma
        f = float(np.exp(-((d - d_peak) ** 2) / (2.0 * sigma * sigma)))
        # Smoothly decay to zero at d=0 so static rendezvous is preserved
        f *= float(1.0 - np.exp(-d * d / 0.5))   # 0 at d=0, ≈1 at d>0.7
        offset[i] = -L_aim * TERMINAL_HEADINGS[i] * f
    return offset


def _draw_terminal_headings(ax, length: float = 1.0, alpha: float = 0.85):
    """Draw the prescribed terminal-heading arrows at each diamond target.
    These show the CW pinwheel pattern: v0(N)→E, v1(W)→N, v2(S)→W, v3(E)→S.
    Static annotation independent of the trajectory's instantaneous velocity.
    """
    for i, (t_tgt, d_hat) in enumerate(zip(DIAMOND_TARGETS, TERMINAL_HEADINGS)):
        x0, y0 = float(t_tgt.real), float(t_tgt.imag)
        dx = length * float(np.real(d_hat))
        dy = length * float(np.imag(d_hat))
        ax.annotate("", xy=(x0 + dx, y0 + dy), xytext=(x0, y0),
                    arrowprops=dict(arrowstyle="-|>", color=AGENT_COLOURS[i],
                                    lw=2.5, alpha=alpha,
                                    mutation_scale=22,
                                    linestyle="-"),
                    zorder=7)


AGENT_COLOURS = ["#d62728", "#1f77b4", "#2ca02c", "#9467bd"]


def diamond_run(T_final: float = 14.0,
                use_safety_filter: bool = True,
                K_obs: float = 8.0,
                with_terminal_heading: bool = True) -> dict:
    """Run a v18 diamond rendezvous: 4 vehicles, 5 obstacles.

    with_terminal_heading=True uses the two-phase time-varying target
    trajectory so each vehicle approaches its diamond vertex tangent to
    the prescribed d_hat_terminal direction (CW pinwheel). The path is
    smooth (no curls); final orientation = approach direction = d_hat.
    """
    # Honest approach: vehicles use a straight PD to static target.
    # Chevron orientation = v_hat at all times. No magic terminal-heading
    # dynamics (which produced curls/overshoot — physically dishonest).
    return v18.run(
        r0=DIAMOND_R0.copy(),
        v0=np.zeros(4, dtype=complex),
        edges=DIAMOND_EDGES,
        t_targets_fn=diamond_targets_static,
        T_final=T_final,
        K_p=4.0, K_d=4.0, K_obs=K_obs,
        obstacles=OBSTACLES,
        use_safety_filter=use_safety_filter,
        log_every=2,
    )


def diamond_run_adaptive(T_final: float = 60.0,
                          T_PE_start: float = 6.0,
                          T_PE: float = 58.0,
                          A_e: float = 2.0,
                          gamma: float = 5.0,
                          K_obs: float = 8.0) -> dict:
    """Adaptive run: rendezvous-then-PE-then-cooldown protocol (Pass 57).

    [0, T_PE_start]      : rendezvous transient, no PE, no adaptation.
    [T_PE_start, T_PE]   : cruise phase with PE injection + Pomet-Praly
                            adaptive law on theta_hat. (W+) Wald recurrent
                            excitation guarantees cumulative Fisher info
                            grows linearly.
    [T_PE, T_final]      : PE-off cooldown, theta_hat frozen, agents return
                            to exact static rendezvous.
    """
    return v18.run(
        r0=DIAMOND_R0.copy(),
        v0=np.zeros(4, dtype=complex),
        edges=DIAMOND_EDGES,
        t_targets_fn=diamond_targets_static,
        T_final=T_final,
        K_p=4.0, K_d=4.0, K_obs=K_obs,
        obstacles=OBSTACLES,
        use_safety_filter=True,
        adaptive=True,
        A_e=A_e,
        T_PE_start=T_PE_start,
        T_PE=T_PE,
        gamma=gamma,
        log_every=10,
    )


def _draw_obstacles(ax, alpha=0.6):
    for (centre, rad) in OBSTACLES:
        circ = plt.Circle((centre.real, centre.imag), rad,
                          color="#888888", alpha=alpha, zorder=1,
                          linewidth=1.5, edgecolor="black")
        ax.add_patch(circ)


def _draw_diamond_targets(ax):
    pts = DIAMOND_TARGETS
    xs = list(pts.real) + [pts[0].real]
    ys = list(pts.imag) + [pts[0].imag]
    ax.plot(xs, ys, color="#aaa", linewidth=0.8, linestyle="--", alpha=0.6, zorder=2)
    for i, t_target in enumerate(pts):
        ax.plot(t_target.real, t_target.imag, "*",
                color=AGENT_COLOURS[i], markersize=14,
                alpha=0.55, markeredgecolor="black", markeredgewidth=0.7,
                zorder=4)


def make_figure(out_AC, out_CBF, save_path: Path):
    fig, axes_grid = plt.subplots(2, 2, figsize=(10, 7),
                                    gridspec_kw={"height_ratios": [3, 1]})
    axes_traj = axes_grid[0]
    axes_h = axes_grid[1]
    scenarios = [("AC alone (no filter)", out_AC), ("AC + CBF (filter on)", out_CBF)]

    for col, (ax, ax_h, (name, out)) in enumerate(zip(axes_traj, axes_h, scenarios)):
        r = out["r"]
        v = out["v"]
        N = r.shape[1]

        _draw_obstacles(ax)
        _draw_diamond_targets(ax)

        for i in range(N):
            xs = r[:, i].real
            ys = r[:, i].imag
            ax.plot(xs, ys, color=AGENT_COLOURS[i],
                    linewidth=1.6, alpha=0.85,
                    label=f"vehicle {i}", zorder=3)
            # Start: vehicle body oriented toward target (initial cross-swap heading)
            start_heading = DIAMOND_TARGETS[i] - DIAMOND_R0[i]
            start_xy = _vehicle_body_xy(complex(xs[0], ys[0]), start_heading,
                                         length=0.4, width=0.25)
            ax.add_patch(Polygon(start_xy, closed=True,
                                  facecolor=AGENT_COLOURS[i], edgecolor="black",
                                  linewidth=0.6, alpha=0.55, zorder=4))
            # End: vehicle body oriented in the LAST meaningful velocity
            # direction (honest — no magic terminal heading). We scan back
            # from the last frame to find the most recent significant |v|.
            end_heading = None
            v_arr = out["v"]
            for k in range(len(xs) - 1, -1, -1):
                vk = v_arr[k, i]
                if float(np.abs(vk)) > 1e-3:
                    end_heading = vk
                    break
            if end_heading is None:
                end_heading = DIAMOND_TARGETS[i] - DIAMOND_R0[i]
            end_xy = _vehicle_body_xy(complex(xs[-1], ys[-1]),
                                       end_heading,
                                       length=0.55, width=0.32)
            ax.add_patch(Polygon(end_xy, closed=True,
                                  facecolor=AGENT_COLOURS[i], edgecolor="black",
                                  linewidth=0.8, alpha=0.95, zorder=5))
            # Heading-vector arrows along trajectory: sampled every K steps,
            # normalized velocity direction (hat v_i = v_i / |v_i|), arrow
            # length scaled for visibility.
            n_arrows = 12   # arrows per trajectory
            stride = max(1, len(xs) // (n_arrows + 1))
            arrow_len = 0.6  # m, fixed visible length regardless of |v_i|
            for k in range(stride, len(xs) - stride, stride):
                vk = v[k, i]
                vmag = float(np.abs(vk))
                if vmag < 1e-3:
                    continue   # skip when essentially at rest
                dx = arrow_len * float(np.real(vk)) / vmag
                dy = arrow_len * float(np.imag(vk)) / vmag
                ax.annotate("", xy=(xs[k] + dx, ys[k] + dy),
                            xytext=(xs[k], ys[k]),
                            arrowprops=dict(arrowstyle="->",
                                            color=AGENT_COLOURS[i],
                                            lw=1.2, alpha=0.85,
                                            mutation_scale=12),
                            zorder=4)

        ax.set_aspect("equal")
        ax.set_xlim(-6.5, 6.5)
        ax.set_ylim(-6.5, 6.5)
        if col == 0:
            ax.set_ylabel(r"$\Im(r_i)$ [m]")
            ax.legend(loc="lower left", fontsize=7, ncol=2)
        ax.grid(True, alpha=0.3)

        h_pair = out["h"].min(axis=1)
        h_obs = out["h_obs"].min(axis=1) if out["h_obs"].size > 0 else h_pair
        h_combined = np.minimum(h_pair, h_obs)
        h_min_total = float(h_combined.min())
        # Final velocity magnitudes (should be near 0 in CBF case for rendezvous)
        v_final = np.abs(v[-1])
        v_final_max = float(v_final.max())
        ax.set_title(f"{name}    (min $h$ = {h_min_total:.3f}, "
                      f"max $|v_{{\\rm final}}|$ = {v_final_max:.2f})", fontsize=10)

        t = out["t"]
        ax_h.plot(t, h_combined, color="#444", linewidth=1.0, alpha=0.5)
        unsafe = h_combined < 0.0
        safe = ~unsafe
        if unsafe.any():
            ax_h.fill_between(t, h_combined, 0.0, where=unsafe,
                              color="#d62728", alpha=0.5, interpolate=True)
        if safe.any():
            ax_h.fill_between(t, h_combined, 0.0, where=safe,
                              color="#2ca02c", alpha=0.4, interpolate=True)
        ax_h.axhline(0.0, color="black", linewidth=0.8)
        ax_h.set_xlabel("time [s]", fontsize=8)
        if col == 0:
            ax_h.set_ylabel(r"$\min h(t)$  $[\rm m^2]$", fontsize=8)
        y_min = min(h_combined.min() * 1.3 - 0.05, -0.3)
        ax_h.set_ylim(y_min, 1.0)
        ax_h.grid(True, alpha=0.3)
        ax_h.tick_params(labelsize=7)

    fig.suptitle("v18 — 4-vehicle static diamond rendezvous "
                  "(complex double-integrator, $\\dot v = \\lambda u$)",
                  fontsize=11, y=0.995)
    fig.tight_layout()
    fig.savefig(save_path, bbox_inches="tight")
    plt.close(fig)


def make_identification_figure(out_adapt, save_path: Path,
                                T_PE_start: float, T_PE: float):
    """Figure showing parameter identification: theta_hat(t) per agent + the
    log-error |theta_hat - 1/lambda|. Validates Theorem 1(3) under (W+) PE."""
    t = out_adapt["t"]
    th = out_adapt["theta_hat"]
    lam = out_adapt["lambda_true"]
    true_inv = 1.0 / lam
    N = th.shape[1]
    err = np.abs(th - true_inv[None, :])

    fig, (ax_th, ax_err) = plt.subplots(2, 1, figsize=(8, 5.5), sharex=True)
    for i in range(N):
        ax_th.plot(t, th[:, i], color=AGENT_COLOURS[i],
                   linewidth=1.4, alpha=0.9,
                   label=fr"vehicle {i} ($\lambda={lam[i]:.2f}$)")
        ax_th.axhline(true_inv[i], color=AGENT_COLOURS[i],
                       linestyle="--", linewidth=0.8, alpha=0.5)
        ax_err.semilogy(t, np.maximum(err[:, i], 1e-6),
                          color=AGENT_COLOURS[i], linewidth=1.4, alpha=0.9)

    for ax in (ax_th, ax_err):
        ax.axvspan(T_PE_start, T_PE, color="#fff0e0",
                    alpha=0.7, zorder=0, label="_nolegend_")
        ax.grid(True, alpha=0.3)

    ax_th.set_ylabel(r"$\hat{\theta}_i(t)$")
    ax_th.legend(loc="lower right", fontsize=8, ncol=2)
    ax_th.set_title(r"Parameter identification under (W+) PE: "
                     r"$\hat{\theta}_i(t) \to 1/\lambda_i$ "
                     r"(dashed lines = true $1/\lambda_i$)", fontsize=10)
    ax_err.set_ylabel(r"$|\hat{\theta}_i - 1/\lambda_i|$")
    ax_err.set_xlabel("time [s]")
    ax_err.set_ylim(1e-5, 1.0)

    # Annotate phases
    ax_th.text((0 + T_PE_start) / 2, ax_th.get_ylim()[1] * 0.95,
                "rendezvous\ntransient", ha="center", va="top", fontsize=8,
                bbox=dict(facecolor="white", alpha=0.7, edgecolor="#888",
                          boxstyle="round,pad=0.2"))
    ax_th.text((T_PE_start + T_PE) / 2, ax_th.get_ylim()[1] * 0.95,
                "cruise + PE\n(W+ active)", ha="center", va="top", fontsize=8,
                bbox=dict(facecolor="#fff0e0", alpha=0.85, edgecolor="#888",
                          boxstyle="round,pad=0.2"))
    if T_PE < t[-1]:
        ax_th.text((T_PE + t[-1]) / 2, ax_th.get_ylim()[1] * 0.95,
                    "PE-off\ncooldown", ha="center", va="top", fontsize=8,
                    bbox=dict(facecolor="white", alpha=0.7, edgecolor="#888",
                              boxstyle="round,pad=0.2"))

    fig.tight_layout()
    fig.savefig(save_path, bbox_inches="tight")
    plt.close(fig)


def make_gif(save_path: Path, fps: int = 15, T_final: float = 14.0):
    print("[v18 diamond gif] running sim...")
    out = diamond_run(T_final=T_final, use_safety_filter=True)
    print(f"  pairwise min h = {out['h'].min():.3f}")
    if out["h_obs"].size > 0:
        print(f"  obstacle min h = {out['h_obs'].min():.3f}")
    v_final_max = float(np.abs(out["v"][-1]).max())
    print(f"  final |v|_max = {v_final_max:.3f} (should be near 0 for rendezvous)")

    t = out["t"]
    r = out["r"]
    v = out["v"]
    h_pair = out["h"].min(axis=1)
    h_obs = out["h_obs"].min(axis=1) if out["h_obs"].size > 0 else h_pair
    h_combined = np.minimum(h_pair, h_obs)
    N = r.shape[1]
    T = len(t)

    duration = float(t[-1])
    n_frames = int(fps * duration)
    if n_frames > T:
        n_frames = T
    frame_indices = np.linspace(0, T - 1, n_frames).astype(int)

    fig, (ax, ax_h) = plt.subplots(2, 1, figsize=(8, 9),
                                     gridspec_kw={"height_ratios": [4, 1]})

    _draw_obstacles(ax)
    _draw_diamond_targets(ax)
    ax.set_xlim(-6.5, 6.5)
    ax.set_ylim(-6.5, 6.5)
    ax.set_aspect("equal")
    ax.set_xlabel(r"$\Re(r_i)$ [m]")
    ax.set_ylabel(r"$\Im(r_i)$ [m]")
    ax.set_title("v18 diamond rendezvous (AC+CBF, double-integrator)", fontsize=11)
    ax.grid(True, alpha=0.3)

    trails = []
    bodies = []           # chevron Polygon patches
    safety_circles = []
    # Persistent "last meaningful heading" per vehicle. Initialized to the
    # initial goal direction (toward target). Updated each frame while |v|>0;
    # used as fallback when the vehicle is at rest (so the chevron freezes
    # rather than snapping arbitrarily).
    last_heading = []
    for i in range(N):
        h0 = DIAMOND_TARGETS[i] - DIAMOND_R0[i]
        last_heading.append(h0 / np.abs(h0))
    last_heading = np.array(last_heading, dtype=complex)
    for i in range(N):
        line, = ax.plot([], [], color=AGENT_COLOURS[i],
                        linewidth=1.6, alpha=0.7, zorder=3,
                        label=f"vehicle {i}")
        trails.append(line)
        # Oriented vehicle body as a chevron Polygon patch
        # (initial heading: toward target along the cross-swap)
        initial_heading = DIAMOND_TARGETS[i] - DIAMOND_R0[i]
        body_xy = _vehicle_body_xy(DIAMOND_R0[i], initial_heading)
        body_patch = Polygon(body_xy, closed=True,
                              facecolor=AGENT_COLOURS[i],
                              edgecolor="black", linewidth=0.9,
                              alpha=0.95, zorder=5)
        ax.add_patch(body_patch)
        bodies.append(body_patch)
        circ, = ax.plot([], [], color=AGENT_COLOURS[i],
                         linewidth=0.6, alpha=0.4, zorder=4)
        safety_circles.append(circ)
    ax.legend(loc="upper right", fontsize=8, ncol=2)

    ax_h.set_xlim(0, duration)
    ax_h.set_ylim(min(h_combined.min() * 1.3 - 0.05, -0.3), 1.0)
    ax_h.set_xlabel("time [s]", fontsize=9)
    ax_h.set_ylabel(r"$\min h(t)$ [m$^2$]", fontsize=9)
    ax_h.axhline(0.0, color="black", linewidth=0.8)
    ax_h.grid(True, alpha=0.3)
    h_dot, = ax_h.plot([], [], "o", color="#d62728", markersize=6)
    h_safe_fill = ax_h.fill_between([0], [0], [0], color="#2ca02c", alpha=0.35)
    h_unsafe_fill = ax_h.fill_between([0], [0], [0], color="#d62728", alpha=0.5)

    theta_circ = np.linspace(0, 2 * np.pi, 60)
    cos_th = np.cos(theta_circ)
    sin_th = np.sin(theta_circ)

    def animate(frame_idx):
        idx = frame_indices[frame_idx]
        t_now = t[idx]
        for i in range(N):
            xs = r[:idx + 1, i].real
            ys = r[:idx + 1, i].imag
            trails[i].set_data(xs, ys)
            safety_circles[i].set_data(
                r[idx, i].real + v18.R_SAFE * cos_th,
                r[idx, i].imag + v18.R_SAFE * sin_th,
            )
            # Chevron heading = v_hat (instantaneous velocity direction).
            # When |v| is very small, freeze in the LAST meaningful heading
            # observed (stored across frames). No magic snap — physically
            # honest for the double-integrator plant.
            vk = v[idx, i]
            vmag = float(np.abs(vk))
            if vmag > 1e-3:
                heading_dir = vk
                last_heading[i] = vk / vmag   # remember for the at-rest case
            else:
                heading_dir = last_heading[i]
            body_xy = _vehicle_body_xy(r[idx, i], heading_dir)
            bodies[i].set_xy(body_xy)
        h_dot.set_data([t_now], [h_combined[idx]])
        nonlocal h_safe_fill, h_unsafe_fill
        for coll in [h_safe_fill, h_unsafe_fill]:
            coll.remove()
        sub_t = t[:idx + 1]
        sub_h = h_combined[:idx + 1]
        h_safe_fill = ax_h.fill_between(
            sub_t, sub_h, 0.0, where=(sub_h >= 0), color="#2ca02c",
            alpha=0.35, interpolate=True,
        )
        h_unsafe_fill = ax_h.fill_between(
            sub_t, sub_h, 0.0, where=(sub_h < 0), color="#d62728",
            alpha=0.5, interpolate=True,
        )
        return trails + bodies + safety_circles + [h_dot, h_safe_fill, h_unsafe_fill]

    anim = animation.FuncAnimation(
        fig, animate, frames=n_frames, interval=1000 / fps, blit=False,
    )
    print(f"Rendering {n_frames} frames at {fps} fps -> {save_path}")
    t0 = time.time()
    anim.save(save_path, writer=animation.PillowWriter(fps=fps), dpi=80)
    print(f"  saved in {time.time() - t0:.1f}s")
    plt.close(fig)


def main():
    T_final = 14.0
    print("v18 diamond rendezvous demo (Pass 52 council unanimous)")
    print(f"Plant: dot r = v, dot v = lambda u (double-integrator), |u| <= {v18.U_MAX}")
    print()

    print("[1/2] AC alone (no filter)")
    out_AC = diamond_run(T_final=T_final, use_safety_filter=False)
    print(f"  pairwise min h = {out_AC['h'].min():.3f}")
    if out_AC["h_obs"].size > 0:
        print(f"  obstacle min h = {out_AC['h_obs'].min():.3f}")
    print(f"  final |v|_max  = {float(np.abs(out_AC['v'][-1]).max()):.3f}")

    print("[2/2] AC + CBF (filter on)")
    out_CBF = diamond_run(T_final=T_final, use_safety_filter=True)
    print(f"  pairwise min h = {out_CBF['h'].min():.3f}")
    if out_CBF["h_obs"].size > 0:
        print(f"  obstacle min h = {out_CBF['h_obs'].min():.3f}")
    print(f"  final |v|_max  = {float(np.abs(out_CBF['v'][-1]).max()):.3f}")

    print("\nGenerating figure...")
    make_figure(out_AC, out_CBF, OUT_FIG / "figure_diamond_v18.pdf")
    print(f"  written to {OUT_FIG / 'figure_diamond_v18.pdf'}")

    print("\n[3/3] Adaptive run (Pomet-Praly + PE on cruise window) ...")
    T_adapt = 60.0
    T_PE_start = 6.0
    T_PE = 58.0
    out_adapt = diamond_run_adaptive(
        T_final=T_adapt, T_PE_start=T_PE_start, T_PE=T_PE,
        A_e=2.0, gamma=5.0,
    )
    th_final = out_adapt["theta_hat"][-1]
    lam = out_adapt["lambda_true"]
    err_final = np.abs(th_final - 1.0 / lam)
    print(f"  true 1/lambda = {np.round(1.0/lam, 3)}")
    print(f"  theta_hat(T_f) = {np.round(th_final, 3)}")
    print(f"  identification error = {np.round(err_final, 4)}")
    print(f"  pairwise h_min = {out_adapt['h'].min():.3f}")
    print(f"  obstacle h_min = {out_adapt['h_obs'].min():.3f}")
    make_identification_figure(out_adapt,
                                OUT_FIG / "figure_diamond_identification.pdf",
                                T_PE_start, T_PE)
    print(f"  written to {OUT_FIG / 'figure_diamond_identification.pdf'}")

    print("\nGenerating GIF...")
    # Pass 63 Boyd: 30 fps for smoother cross-swap motion
    make_gif(OUT_GIF / "diamond_v18.gif", fps=30, T_final=T_final)


if __name__ == "__main__":
    main()
