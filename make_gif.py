"""Render an animated GIF of a v17 simulation (visualization for talks/web).

Not a paper figure — purely for showing how the agents move in real time.

Usage:
    python make_gif.py                          # rotating-ring rosette (default)
    python make_gif.py --scenario obstacles     # 4-vehicle obstacle avoidance
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np

from sim import paper_params as pp
from sim import integrator
from sim import plots as sim_plots


HERE = Path(__file__).resolve().parent
OUT = HERE / "output" / "gifs"
OUT.mkdir(parents=True, exist_ok=True)

AGENT_COLOURS = sim_plots.AGENT_COLOURS


def render_gif(out: dict, save_path: Path, title: str,
               obstacles: list = None,
               xlim: tuple = (-3.6, 3.6), ylim: tuple = (-3.6, 3.6),
               fps: int = 20):
    """Render an animated GIF from a sim output dict.

    out: integrator.run output (must have 't', 'r', 'v_a', 'h')
    obstacles: optional list of (centre_complex, radius) tuples for static
               obstacles to draw as filled circles.
    """
    t = out["t"]
    r = out["r"]                            # (T, N) complex
    h_ij = out["h"]                         # (T, n_pairs)
    h_min_t = h_ij.min(axis=1)
    N = r.shape[1]
    T = len(t)

    # Down-sample to ~ fps * duration frames
    duration = float(t[-1])
    n_frames = int(fps * duration)
    if n_frames > T:
        n_frames = T
    frame_indices = np.linspace(0, T - 1, n_frames).astype(int)

    fig, (ax_traj, ax_h) = plt.subplots(
        2, 1, figsize=(8, 7),
        gridspec_kw={"height_ratios": [4, 1]},
    )

    # Trajectory panel setup
    ax_traj.set_xlim(*xlim)
    ax_traj.set_ylim(*ylim)
    ax_traj.set_aspect("equal")
    ax_traj.set_xlabel(r"$\Re(r_i)$ [m]")
    ax_traj.set_ylabel(r"$\Im(r_i)$ [m]")
    ax_traj.set_title(title, fontsize=11)
    ax_traj.grid(True, alpha=0.3)

    # Static obstacles (drawn once)
    if obstacles is not None:
        for (centre, rad) in obstacles:
            circ = plt.Circle((centre.real, centre.imag), rad,
                              color="#888888", alpha=0.6, zorder=1,
                              linewidth=1.5, edgecolor="black")
            ax_traj.add_patch(circ)

    # Trail lines (one per agent), updated in animation
    trails = []
    bodies = []
    safety_circles = []
    for i in range(N):
        line, = ax_traj.plot([], [], color=AGENT_COLOURS[i % len(AGENT_COLOURS)],
                             linewidth=1.6, alpha=0.7, zorder=2,
                             label=f"agent {i}")
        trails.append(line)
        body, = ax_traj.plot([], [], "o",
                             color=AGENT_COLOURS[i % len(AGENT_COLOURS)],
                             markersize=8, zorder=4)
        bodies.append(body)
        # r_safe bubble
        circ, = ax_traj.plot([], [],
                             color=AGENT_COLOURS[i % len(AGENT_COLOURS)],
                             linewidth=0.6, alpha=0.4, zorder=3)
        safety_circles.append(circ)
    ax_traj.legend(loc="upper right", fontsize=7, ncol=2)

    # h_min(t) panel setup
    ax_h.set_xlim(0, duration)
    h_y_min = min(h_min_t.min() * 1.3 - 0.02, -0.1)
    h_y_max = 0.4
    ax_h.set_ylim(h_y_min, h_y_max)
    ax_h.set_xlabel("time [s]", fontsize=9)
    ax_h.set_ylabel(r"$\min_{ij}\,h_{ij}(t)$ [m$^2$]", fontsize=9)
    ax_h.axhline(0.0, color="black", linewidth=0.8)
    ax_h.axhline(pp.ZETA, color="grey", linewidth=0.5, linestyle="--", alpha=0.6)
    ax_h.grid(True, alpha=0.3)

    h_line, = ax_h.plot([], [], color="#444", linewidth=1.0, alpha=0.5)
    h_dot, = ax_h.plot([], [], "o", color="#d62728", markersize=6)
    h_safe_fill = ax_h.fill_between([0], [0], [0], color="#2ca02c",
                                     alpha=0.35, label="safe")
    h_unsafe_fill = ax_h.fill_between([0], [0], [0], color="#d62728",
                                       alpha=0.5, label="UNSAFE")

    theta = np.linspace(0, 2 * np.pi, 60)
    cos_th = np.cos(theta)
    sin_th = np.sin(theta)

    def init():
        for tr in trails:
            tr.set_data([], [])
        for b in bodies:
            b.set_data([], [])
        for c in safety_circles:
            c.set_data([], [])
        h_line.set_data([], [])
        h_dot.set_data([], [])
        return trails + bodies + safety_circles + [h_line, h_dot]

    def animate(frame_idx):
        idx = frame_indices[frame_idx]
        t_now = t[idx]
        for i in range(N):
            # Trail: history up to current index
            xs = r[:idx + 1, i].real
            ys = r[:idx + 1, i].imag
            trails[i].set_data(xs, ys)
            # Current body marker
            bodies[i].set_data([r[idx, i].real], [r[idx, i].imag])
            # Safety bubble
            safety_circles[i].set_data(
                r[idx, i].real + pp.R_SAFE * cos_th,
                r[idx, i].imag + pp.R_SAFE * sin_th,
            )
        # h_min panel
        h_line.set_data(t[:idx + 1], h_min_t[:idx + 1])
        h_dot.set_data([t_now], [h_min_t[idx]])

        # Refresh fill (must remove and re-add since fill_between can't update)
        nonlocal h_safe_fill, h_unsafe_fill
        for coll in [h_safe_fill, h_unsafe_fill]:
            coll.remove()
        sub_t = t[:idx + 1]
        sub_h = h_min_t[:idx + 1]
        h_safe_fill = ax_h.fill_between(
            sub_t, sub_h, 0.0, where=(sub_h >= 0), color="#2ca02c", alpha=0.35,
            interpolate=True,
        )
        h_unsafe_fill = ax_h.fill_between(
            sub_t, sub_h, 0.0, where=(sub_h < 0), color="#d62728", alpha=0.5,
            interpolate=True,
        )
        return trails + bodies + safety_circles + [h_line, h_dot,
                                                    h_safe_fill, h_unsafe_fill]

    anim = animation.FuncAnimation(
        fig, animate, init_func=init,
        frames=n_frames, interval=1000 / fps, blit=False,
    )

    print(f"Rendering {n_frames} frames at {fps} fps ({duration:.1f}s) -> {save_path}")
    t0 = time.time()
    anim.save(save_path, writer=animation.PillowWriter(fps=fps), dpi=80)
    print(f"  saved in {time.time() - t0:.1f}s")
    plt.close(fig)


def make_ring8_gif():
    """GIF of the v17.3 N=8 rotating-ring rosette (AC+CBF+PE headline)."""
    print("[ring8 gif] running sim...")
    saved_H, saved_M = pp.H_OUTER, pp.SLACK_PENALTY
    pp.H_OUTER = pp.H_OUTER_RING8
    pp.SLACK_PENALTY = pp.SLACK_PENALTY_RING8
    try:
        out = integrator.run(
            r0=pp.RING8_R0.copy(), v_a0=pp.ring8_v0(),
            r_ref0=pp.RING8_R0.copy(), v_ref0=pp.ring8_v0(),
            edges=pp.RING8_EDGES,
            t_targets_fn=pp.ring8_targets_oscillating,
            A_e=0.10 * pp.PSI_DOT_MAX,
            T_final=16.0, log_every=2,
            use_safety_filter=True,
        )
    finally:
        pp.H_OUTER, pp.SLACK_PENALTY = saved_H, saved_M
    print(f"  h_min = {out['h'].min():.3f}")
    render_gif(
        out, OUT / "ring8_rotation.gif",
        title="v17.3 N=8 rotating-ring rosette (AC+CBF+PE)",
        xlim=(-3.6, 3.6), ylim=(-3.6, 3.6), fps=15,
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", default="ring8",
                        choices=["ring8", "obstacles"])
    args = parser.parse_args()

    if args.scenario == "ring8":
        make_ring8_gif()
    elif args.scenario == "obstacles":
        # Defer to v17.7 obstacle implementation
        from sim import paper_params as pp2
        if not hasattr(pp2, "OBSTACLE_R0"):
            print("Obstacle scenario not yet implemented.")
            sys.exit(1)
        from make_gif_obstacles import make_obstacle_gif
        make_obstacle_gif()


if __name__ == "__main__":
    main()
