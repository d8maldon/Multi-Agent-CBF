"""v17.7 4-vehicle obstacle-avoidance demo (Pass 47 council APPROVED).

Generates:
- output/v17/figure_obstacle_demo.pdf  (3-panel: AC, AC+CBF, AC+CBF+PE with
  trajectory + h_min(t) inset)
- output/gifs/obstacle_demo.gif        (animation of AC+CBF+PE)
"""

from __future__ import annotations

import time
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np

from sim import paper_params as pp
from sim import integrator
from sim import dynamics as dyn
from sim import plots as sim_plots


HERE = Path(__file__).resolve().parent
OUT_FIG = HERE / "output" / "v17"
OUT_GIF = HERE / "output" / "gifs"
OUT_FIG.mkdir(parents=True, exist_ok=True)
OUT_GIF.mkdir(parents=True, exist_ok=True)


def obstacle_run(A_e: float, T_final: float, log_every: int,
                  use_safety_filter: bool = True) -> dict:
    """One v17.7 obstacle-avoidance run."""
    return integrator.run(
        r0=pp.OBSTACLE_R0.copy(), v_a0=pp.obstacle_v0(),
        r_ref0=pp.OBSTACLE_R0.copy(), v_ref0=pp.obstacle_v0(),
        edges=pp.OBSTACLE_EDGES,
        t_targets_fn=pp.obstacle_targets_static,
        A_e=A_e,
        T_final=T_final,
        log_every=log_every,
        use_safety_filter=use_safety_filter,
        obstacles=pp.OBSTACLE_LIST,
    )


def _compute_h_obstacle(out: dict) -> np.ndarray:
    """Compute h_obstacle[t, i, k] for each (time, vehicle, obstacle) over the
    full trajectory. Returns the per-time min over (i, k)."""
    r = out["r"]                   # (T, N) complex
    T, N = r.shape
    K = len(pp.OBSTACLE_LIST)
    h_obs = np.zeros((T, N, K))
    for k_idx, (r_obs, r_obs_radius) in enumerate(pp.OBSTACLE_LIST):
        for i in range(N):
            h_obs[:, i, k_idx] = np.abs(r[:, i] - r_obs) ** 2 - (pp.R_SAFE + r_obs_radius) ** 2
    return h_obs    # (T, N, K)


def _draw_obstacles(ax, alpha=0.6):
    """Draw the static obstacle circles on a trajectory ax."""
    for (centre, rad) in pp.OBSTACLE_LIST:
        circ = plt.Circle((centre.real, centre.imag), rad,
                          color="#888888", alpha=alpha, zorder=1,
                          linewidth=1.5, edgecolor="black")
        ax.add_patch(circ)


def make_obstacle_figure(out_AC, out_CBF, out_PE, save_path: Path):
    """3-panel obstacle figure with h_min(t) inset."""
    fig, axes_grid = plt.subplots(2, 3, figsize=(12, 6),
                                   gridspec_kw={"height_ratios": [3, 1]})
    axes_traj = axes_grid[0]
    axes_h = axes_grid[1]
    scenarios = [("AC", out_AC), ("AC+CBF", out_CBF), ("AC+CBF+PE", out_PE)]

    for col, (ax, ax_h, (name, out)) in enumerate(zip(axes_traj, axes_h, scenarios)):
        r = out["r"]
        v_a = out["v_a"]
        N = r.shape[1]

        # Trajectory panel
        _draw_obstacles(ax)
        for i in range(N):
            xs = r[:, i].real
            ys = r[:, i].imag
            ax.plot(xs, ys, color=sim_plots.AGENT_COLOURS[i],
                    linewidth=1.6, alpha=0.85,
                    label=f"vehicle {i}", zorder=3)
            ax.plot([xs[0]], [ys[0]], "o",
                    color=sim_plots.AGENT_COLOURS[i],
                    markersize=8, zorder=4, alpha=0.6)
            ax.plot([xs[-1]], [ys[-1]], "^",
                    color=sim_plots.AGENT_COLOURS[i],
                    markersize=10, zorder=4)
            theta = np.linspace(0, 2 * np.pi, 60)
            ax.plot(xs[0] + pp.R_SAFE * np.cos(theta),
                    ys[0] + pp.R_SAFE * np.sin(theta),
                    color=sim_plots.AGENT_COLOURS[i],
                    linewidth=0.4, alpha=0.4, zorder=2)
        # Target markers
        for i, t_target in enumerate(pp.OBSTACLE_TARGETS):
            ax.plot(t_target.real, t_target.imag, "*",
                    color=sim_plots.AGENT_COLOURS[i],
                    markersize=14, zorder=4, alpha=0.5,
                    markeredgecolor="black", markeredgewidth=0.7)

        ax.set_aspect("equal")
        ax.set_xlim(-5.5, 5.5)
        ax.set_ylim(-5.5, 5.5)
        if col == 0:
            ax.set_ylabel(r"$\Im(r_i)$ [m]")
            ax.legend(loc="lower right", fontsize=7, ncol=2)
        ax.grid(True, alpha=0.3)

        # min h_ij and min h_obs combined
        h_pair = out["h"].min(axis=1)
        h_obs_arr = _compute_h_obstacle(out)
        h_obs_min = h_obs_arr.min(axis=(1, 2))
        h_combined = np.minimum(h_pair, h_obs_min)
        h_min_total = float(h_combined.min())
        ax.set_title(f"{name}    (min $h$ = {h_min_total:.3f})", fontsize=10)

        # h_min(t) inset panel
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
        y_min = min(h_combined.min() * 1.3 - 0.05, -0.2)
        ax_h.set_ylim(y_min, 0.8)
        ax_h.tick_params(axis='both', labelsize=7)
        ax_h.grid(True, alpha=0.3)

    fig.suptitle("v17.7 — 4-vehicle cross-swap with 3 static circular obstacles "
                  r"($K_4$ comm + obstacle CBF; Ames-Xu-Grizzle 2014)",
                  fontsize=11, y=0.99)
    fig.tight_layout()
    fig.savefig(save_path, bbox_inches="tight")
    plt.close(fig)


def make_obstacle_gif(save_path: Path, fps: int = 15, T_final: float = 14.0):
    """Animated GIF of AC+CBF+PE on the obstacle scenario."""
    print("[obstacle gif] running sim...")
    out = obstacle_run(0.10 * pp.PSI_DOT_MAX, T_final=T_final, log_every=2)
    print(f"  pairwise min h = {out['h'].min():.3f}")
    h_obs_arr = _compute_h_obstacle(out)
    h_obs_min = h_obs_arr.min()
    print(f"  obstacle min h = {h_obs_min:.3f}")

    t = out["t"]
    r = out["r"]
    h_pair = out["h"].min(axis=1)
    h_obs_min_t = h_obs_arr.min(axis=(1, 2))
    h_combined = np.minimum(h_pair, h_obs_min_t)
    N = r.shape[1]
    T = len(t)

    duration = float(t[-1])
    n_frames = int(fps * duration)
    if n_frames > T:
        n_frames = T
    frame_indices = np.linspace(0, T - 1, n_frames).astype(int)

    fig, (ax, ax_h) = plt.subplots(2, 1, figsize=(8, 8),
                                     gridspec_kw={"height_ratios": [4, 1]})

    _draw_obstacles(ax)
    ax.set_xlim(-5.5, 5.5)
    ax.set_ylim(-5.5, 5.5)
    ax.set_aspect("equal")
    ax.set_xlabel(r"$\Re(r_i)$ [m]")
    ax.set_ylabel(r"$\Im(r_i)$ [m]")
    ax.set_title("v17.7 4-vehicle obstacle avoidance (AC+CBF+PE)", fontsize=11)
    ax.grid(True, alpha=0.3)

    # Target stars (drawn once)
    for i, t_target in enumerate(pp.OBSTACLE_TARGETS):
        ax.plot(t_target.real, t_target.imag, "*",
                color=sim_plots.AGENT_COLOURS[i], markersize=15,
                alpha=0.5, markeredgecolor="black", markeredgewidth=0.8,
                zorder=4)

    trails = []
    bodies = []
    safety_circles = []
    for i in range(N):
        line, = ax.plot([], [], color=sim_plots.AGENT_COLOURS[i],
                        linewidth=1.6, alpha=0.7, zorder=3,
                        label=f"vehicle {i}")
        trails.append(line)
        body, = ax.plot([], [], "o",
                         color=sim_plots.AGENT_COLOURS[i],
                         markersize=10, zorder=5)
        bodies.append(body)
        circ, = ax.plot([], [],
                         color=sim_plots.AGENT_COLOURS[i],
                         linewidth=0.6, alpha=0.4, zorder=4)
        safety_circles.append(circ)
    ax.legend(loc="upper right", fontsize=8, ncol=2)

    ax_h.set_xlim(0, duration)
    h_y_min = min(h_combined.min() * 1.3 - 0.05, -0.2)
    ax_h.set_ylim(h_y_min, 0.6)
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
            bodies[i].set_data([r[idx, i].real], [r[idx, i].imag])
            safety_circles[i].set_data(
                r[idx, i].real + pp.R_SAFE * cos_th,
                r[idx, i].imag + pp.R_SAFE * sin_th,
            )
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
    T_final = 14.0   # enough for vehicles to reach their targets

    print("Running 3 obstacle-avoidance scenarios (T_final=14s)...")
    print("[1/3] AC alone (no filter, no PE)")
    out_AC = obstacle_run(0.0, T_final, log_every=2, use_safety_filter=False)
    h_obs_AC = _compute_h_obstacle(out_AC).min()
    print(f"  pairwise min h = {out_AC['h'].min():.3f}, obstacle min h = {h_obs_AC:.3f}")

    print("[2/3] AC + CBF (filter on, no PE)")
    out_CBF = obstacle_run(0.0, T_final, log_every=2, use_safety_filter=True)
    h_obs_CBF = _compute_h_obstacle(out_CBF).min()
    print(f"  pairwise min h = {out_CBF['h'].min():.3f}, obstacle min h = {h_obs_CBF:.3f}")

    print("[3/3] AC + CBF + PE (filter + PE)")
    out_PE = obstacle_run(0.10 * pp.PSI_DOT_MAX, T_final, log_every=2,
                            use_safety_filter=True)
    h_obs_PE = _compute_h_obstacle(out_PE).min()
    print(f"  pairwise min h = {out_PE['h'].min():.3f}, obstacle min h = {h_obs_PE:.3f}")

    print("\nGenerating obstacle figure...")
    make_obstacle_figure(out_AC, out_CBF, out_PE,
                          OUT_FIG / "figure_obstacle_demo.pdf")
    print(f"  written to {OUT_FIG / 'figure_obstacle_demo.pdf'}")

    print("\nGenerating obstacle GIF...")
    make_obstacle_gif(OUT_GIF / "obstacle_demo.gif", fps=15, T_final=T_final)


if __name__ == "__main__":
    main()
