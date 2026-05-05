"""Figures for paper §8.4 figure plan, v17 (council-vetted Passes 19-30).

v17 specifics:
- State is complex (r, v_a) in C^2 per agent. Plot x = r.real, y = r.imag.
- Agents rendered as oriented triangles with heading psi = arg(v_a).
- Control u_2 is scalar real (not vector).
- Identifiability gain bar_rho_i is scalar (not matrix Q_i with trace).
- Saturation is psi_dot_max (rad/s), not u_max.
- New: figure 7 head-on Filippov sliding-mode demonstration (paper §8.1).

Each function takes already-computed simulation outputs (dicts from
integrator.run) and writes a PDF to the given path.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from . import paper_params as pp


# ---------------------------------------------------------------------------
# Style
# ---------------------------------------------------------------------------

plt.rcParams.update({
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "axes.edgecolor": "#222222",
    "axes.labelcolor": "#1f1f1f",
    "xtick.color": "#1f1f1f",
    "ytick.color": "#1f1f1f",
    "axes.grid": True,
    "grid.color": "#dddddd",
    "grid.linewidth": 0.6,
    "font.size": 10,
    "axes.titlesize": 11,
    "axes.labelsize": 10,
    "legend.frameon": False,
    "legend.fontsize": 9,
})

AGENT_COLOURS = ["#d62728", "#1f77b4", "#2ca02c", "#9467bd"]   # 4 agents
SCENARIO_STYLES = {
    "AC": {"linestyle": ":", "linewidth": 1.4, "label": "AC alone"},
    "AC+CBF": {"linestyle": "--", "linewidth": 1.4, "label": "AC + CBF"},
    "AC+CBF+PE": {"linestyle": "-", "linewidth": 1.6, "label": "AC + CBF + PE"},
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _draw_oriented_triangle(ax, x, y, heading_rad, color, scale=0.25, alpha=1.0):
    """Draw an oriented triangle at (x, y) pointing in direction heading_rad.

    The triangle is sized `scale` along its long axis and rendered in the agent
    colour. Used for the v17 cross-swap trajectory figure to show heading psi_i.
    """
    cos_h, sin_h = np.cos(heading_rad), np.sin(heading_rad)
    # Triangle local vertices: nose (long axis), back-left, back-right
    nose = np.array([scale, 0.0])
    bl = np.array([-scale * 0.4, scale * 0.4])
    br = np.array([-scale * 0.4, -scale * 0.4])
    R = np.array([[cos_h, -sin_h], [sin_h, cos_h]])
    n = R @ nose; bl = R @ bl; br = R @ br
    triangle = plt.Polygon([
        (x + n[0], y + n[1]),
        (x + bl[0], y + bl[1]),
        (x + br[0], y + br[1]),
    ], color=color, alpha=alpha, edgecolor="black", linewidth=0.4)
    ax.add_patch(triangle)


# ---------------------------------------------------------------------------
# Figure 1 — cross-swap trajectories (oriented Dubins agents on curved paths)
# ---------------------------------------------------------------------------

def figure_1_trajectories(out_AC: dict, out_CBF: dict, out_PE: dict, save: Path):
    """Three side-by-side panels showing curved Dubins trajectories under each
    scenario. Agents rendered as oriented triangles (using arg(v_a)) at start
    and end positions; trajectory lines show the curved Dubins path.
    """
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.8), sharex=True, sharey=True)
    scenarios = [("AC", out_AC), ("AC+CBF", out_CBF), ("AC+CBF+PE", out_PE)]

    for ax, (name, out) in zip(axes, scenarios):
        r = out["r"]               # (T, N) complex
        v_a = out["v_a"]           # (T, N) complex
        N = r.shape[1]
        for i in range(N):
            xs = r[:, i].real
            ys = r[:, i].imag
            # Trajectory (curved Dubins path)
            ax.plot(xs, ys, color=AGENT_COLOURS[i],
                    linewidth=1.2, alpha=0.85, label=f"agent {i}")
            # Oriented triangle at start and end
            _draw_oriented_triangle(ax, xs[0], ys[0], np.angle(v_a[0, i]),
                                     color=AGENT_COLOURS[i], alpha=0.4)
            _draw_oriented_triangle(ax, xs[-1], ys[-1], np.angle(v_a[-1, i]),
                                     color=AGENT_COLOURS[i], alpha=0.95)
            # r_safe circle at start position (faded; collision-avoidance bubble)
            theta = np.linspace(0, 2 * np.pi, 80)
            ax.plot(
                xs[0] + pp.R_SAFE * np.cos(theta),
                ys[0] + pp.R_SAFE * np.sin(theta),
                color=AGENT_COLOURS[i], linewidth=0.4, alpha=0.4,
            )
        ax.set_aspect("equal")
        ax.set_xlabel(r"$\Re(r_i)$ [m]")
        if name == "AC":
            ax.set_ylabel(r"$\Im(r_i)$ [m]")
            ax.legend(loc="lower left", fontsize=7)
        h_min = float(out['h'].min())
        ax.set_title(f"{name}    (min $h_{{ij}}$ = {h_min:.2f})")
        ax.set_xlim(-3.6, 3.6)
        ax.set_ylim(-3.6, 3.6)

    fig.suptitle("Figure 1 — v17 cross-swap Dubins trajectories under three scenarios",
                 fontsize=12, y=1.02)
    fig.tight_layout()
    fig.savefig(save, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Figure 2 — parameter convergence (one subplot per agent, log-y)
# ---------------------------------------------------------------------------

def figure_2_param_convergence(out_AC: dict, out_CBF: dict, out_PE: dict, save: Path):
    """4 subplots (one per agent), showing |theta_hat - 1/lambda| over time."""
    inv_L = 1.0 / pp.LAMBDA_TRUE
    N = inv_L.shape[0]

    fig, axes = plt.subplots(1, N, figsize=(12, 3.2), sharey=True)
    for i, ax in enumerate(axes):
        for name, out in [("AC", out_AC), ("AC+CBF", out_CBF), ("AC+CBF+PE", out_PE)]:
            err = np.abs(out["theta_hat"][:, i] - inv_L[i])
            err = np.maximum(err, 1e-4)
            ax.semilogy(out["t"], err, color=AGENT_COLOURS[i], **SCENARIO_STYLES[name])
        ax.set_xlabel("time [s]")
        ax.set_title(f"agent {i}    $1/\\lambda_{{{i}}} = {inv_L[i]:.3f}$")
        ax.set_ylim(1e-4, 2.0)
    axes[0].set_ylabel(r"$|\hat\theta_i(t) - 1/\lambda_i|$")
    axes[-1].legend(loc="upper right")

    fig.suptitle("Figure 2 — v17 parameter convergence (semilog) under three scenarios",
                 fontsize=12, y=1.02)
    fig.tight_layout()
    fig.savefig(save, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Figure 3 — identifiability gain bar_rho_i(t) computed online (v17 scalar)
# ---------------------------------------------------------------------------

def figure_3_identifiability(out_PE: dict, save: Path):
    """Cumulative running average of |Pi_F phi|^2 / m^2 per agent + spatial
    average. Per paper §5.2:
        bar_rho_i(t) = (1/t) integral_0^t [V_0^2 (u_2^ref)^2 / (1 + V_0^2 (u_2^ref)^2)
                                              * 1{N_i^on = empty}] dtau
    """
    t = out_PE["t"]
    u_2_ref = out_PE["u_2_ref"]                  # (T, N) real
    active_count = out_PE["active_count"]        # (T,) int
    # Per-step integrand: only when no pair active; the integrator already
    # treats binary cone {0, R}, so use the global no-pair-active flag.
    no_active = (active_count == 0)              # (T,) bool
    integrand = (pp.V_0 ** 2 * u_2_ref ** 2) / (1.0 + pp.V_0 ** 2 * u_2_ref ** 2)
    integrand_masked = integrand * no_active[:, None]
    dt = np.diff(t, prepend=t[0])
    cum_int = np.cumsum(integrand_masked * dt[:, None], axis=0)
    cum_t = np.maximum(np.cumsum(dt), 1e-9)
    rho_bar_t = cum_int / cum_t[:, None]         # (T, N)

    fig, ax = plt.subplots(figsize=(8, 4.2))
    for i in range(rho_bar_t.shape[1]):
        ax.plot(t, rho_bar_t[:, i], color=AGENT_COLOURS[i],
                linewidth=1.4, label=f"agent {i}")
    spatial_avg = rho_bar_t.mean(axis=1)
    ax.plot(t, spatial_avg, color="black", linewidth=1.6, linestyle="--",
            label=r"spatial $\mu$-average")

    # Final bar_rho_i values from integrator
    for i, rho in enumerate(out_PE["bar_rho_i"]):
        ax.axhline(rho, color=AGENT_COLOURS[i], linewidth=0.6, alpha=0.5)

    ax.set_xlabel("time [s]")
    ax.set_ylabel(r"running $\bar\rho_i(t)$ (scalar Fisher info)")
    ax.set_title(r"Figure 3 — v17 scalar identifiability gain $\bar\rho_i(t) \in [0, 1)$")
    ax.set_ylim(0, 1)
    ax.legend(ncol=3, loc="lower right")
    fig.tight_layout()
    fig.savefig(save, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Figure 4 — safety margin min_ij h_ij(t) + KB covariance decay
# ---------------------------------------------------------------------------

def figure_4_safety(out_PE: dict, save: Path):
    """Two-panel: top is min h_ij(t) safety margin, bottom is P_i(t) decay."""
    t = out_PE["t"]
    h_min = out_PE["h"].min(axis=1)
    h_mean = out_PE["h"].mean(axis=1)
    P = out_PE["P"]

    fig, axes = plt.subplots(2, 1, figsize=(8, 5), sharex=True)

    ax = axes[0]
    ax.plot(t, h_min, color="#d62728", linewidth=1.6, label=r"$\min_{ij}\,h_{ij}(t)$")
    ax.plot(t, h_mean, color="#1f77b4", linewidth=1.0, alpha=0.6,
            label=r"$\mathrm{mean}_{ij}\,h_{ij}(t)$")
    ax.axhline(0.0, color="black", linewidth=0.7, label="safe-set boundary")
    ax.axhline(pp.ZETA, color="grey", linewidth=0.7, linestyle="--",
               label=fr"$\zeta = 0.5\, r_{{\rm safe}}^2 = {pp.ZETA:.3f}$")
    ax.set_ylabel(r"$h_{ij}(t)$  $[\rm m^2]$")
    ax.legend(loc="upper right", ncol=2)
    ax.set_title(f"Figure 4 — v17 safety margin (run min = {h_min.min():.4f})")

    ax = axes[1]
    for i in range(P.shape[1]):
        ax.plot(t, P[:, i], color=AGENT_COLOURS[i], linewidth=1.2,
                label=f"agent {i}")
    ax.set_xlabel("time [s]")
    ax.set_ylabel(r"KB covariance $P_i(t)$")
    ax.set_yscale("log")
    ax.legend(ncol=4, loc="upper right")

    fig.tight_layout()
    fig.savefig(save, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Figure 5 — A_e Pareto sweep
# ---------------------------------------------------------------------------

def figure_5_ae_sweep(sweep_results: list, save: Path):
    """sweep_results: list of (A_e, out_dict) for A_e in §8.4 sweep.

    v17: ultimate-bound proxy is mean |r - r_ref|^2 (complex tracking error).
    """
    A_e_vals = np.array([s[0] for s in sweep_results])
    inv_L = 1.0 / pp.LAMBDA_TRUE

    rates = np.zeros((len(A_e_vals), pp.LAMBDA_TRUE.shape[0]))
    bounds = np.zeros_like(rates)
    for k, (A_e, out) in enumerate(sweep_results):
        T = out["t"][-1]
        err_final = np.abs(out["theta_hat"][-1] - inv_L)
        err_initial = np.abs(out["theta_hat"][0] - inv_L) + 1e-9
        rates[k] = -np.log(np.maximum(err_final, 1e-4) / err_initial) / T
        # ultimate bound: time-averaged |r - r_ref|^2 over last 50% of run
        half = len(out["t"]) // 2
        e_sq = np.abs(out["r"][half:] - out["r_ref"][half:]) ** 2  # (T, N)
        bounds[k] = e_sq.mean(axis=0)

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))

    ax = axes[0]
    for i in range(rates.shape[1]):
        ax.plot(A_e_vals / pp.PSI_DOT_MAX, rates[:, i], "o-",
                color=AGENT_COLOURS[i], label=f"agent {i}")
    ax.set_xlabel(r"excitation amplitude  $A_e / \dot\psi_{\max}$")
    ax.set_ylabel(r"identification rate $-\log(|\theta_{\rm err}^{\rm final}|/|\theta_{\rm err}^{\rm init}|)/T$")
    ax.set_title("Identification rate (higher = faster)")
    ax.legend(ncol=2)

    ax = axes[1]
    for i in range(bounds.shape[1]):
        ax.plot(A_e_vals / pp.PSI_DOT_MAX, bounds[:, i], "s-",
                color=AGENT_COLOURS[i], label=f"agent {i}")
    ax.set_xlabel(r"excitation amplitude  $A_e / \dot\psi_{\max}$")
    ax.set_ylabel(r"steady-state $\langle |r_i - r_{{\rm ref},i}|^2\rangle$")
    ax.set_title("Ultimate bound (lower = tighter tracking)")
    ax.legend(ncol=2)

    fig.suptitle(r"Figure 5 — v17 Pareto sweep over $A_e \in \{0, 0.05, 0.10, 0.20\}\,\dot\psi_{\max}$",
                 fontsize=12, y=1.02)
    fig.tight_layout()
    fig.savefig(save, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Figure 6 — communication-delay robustness sweep (v17)
# ---------------------------------------------------------------------------

def figure_6_comm_delay(delay_results: list, save: Path):
    """delay_results: list of (tau_ms, out_dict). v17 cross-coupling via v_a,j
    has higher relative degree than v16; the comm-delay tolerance may differ.
    """
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))

    ax = axes[0]
    cmap = plt.cm.viridis
    for k, (tau_ms, out) in enumerate(delay_results):
        c = cmap(k / max(len(delay_results) - 1, 1))
        h_min_t = out["h"].min(axis=1)
        ax.plot(out["t"], h_min_t, color=c, linewidth=1.4,
                label=fr"$\tau = {tau_ms}$ ms")
    ax.axhline(0.0, color="black", linewidth=0.8, label="safe-set boundary")
    ax.axhline(pp.ZETA, color="grey", linewidth=0.6, linestyle="--",
               label=fr"$\zeta = {pp.ZETA:.3f}$")
    ax.set_xlabel("time [s]")
    ax.set_ylabel(r"$\min_{ij}\,h_{ij}(t)$  $[\rm m^2]$")
    ax.set_title(r"v17 safety margin vs comm delay $\tau$")
    ax.legend(ncol=2, loc="lower right", fontsize=8)

    ax = axes[1]
    taus = np.array([d[0] for d in delay_results])
    hmins = np.array([d[1]["h"].min() for d in delay_results])
    colours = ["#2ca02c" if h >= pp.ZETA else "#ff9800" if h >= 0 else "#d62728"
               for h in hmins]
    ax.bar(np.arange(len(taus)), hmins, color=colours, edgecolor="black", linewidth=0.5)
    for k, (tau, h) in enumerate(zip(taus, hmins)):
        ax.text(k, max(h, 0) + 0.005, f"{h:+.3f}", ha="center", fontsize=9)
    ax.axhline(0.0, color="black", linewidth=0.8)
    ax.axhline(pp.ZETA, color="grey", linewidth=0.6, linestyle="--",
               label=fr"$\zeta = {pp.ZETA:.3f}$ margin target")
    ax.set_xticks(np.arange(len(taus)))
    ax.set_xticklabels([f"{int(t)}" for t in taus])
    ax.set_xlabel(r"comm-delay $\tau$ [ms]")
    ax.set_ylabel(r"run-min  $\min_t \min_{ij} h_{ij}$  $[\rm m^2]$")
    ax.set_title("v17 empirical robustness margin against (A4) relaxation")
    ax.legend(loc="upper right")

    fig.suptitle(r"Figure 6 — v17 comm-delay sweep $\tau \in \{0, 5, 20, 50, 100\}$ ms",
                 fontsize=12, y=1.02)
    fig.tight_layout()
    fig.savefig(save, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Figure 7 — N=2 head-on Filippov sliding-mode demonstration (v17 §8.1)
# ---------------------------------------------------------------------------

def figure_7_headon_filippov(out_no_pe: dict, out_with_pe: dict, save: Path):
    """v17-specific figure: N=2 agents on head-on closing trajectory.

    Two side-by-side panels:
      - Left: A_e = 0 (no PE). Agents stay on the relative-degree-drop locus,
        |a_ii| stays near 0, slack absorbs the constraint. Identifiability is
        zero.
      - Right: A_e > 0 (PE injection). PE breaks the head-on alignment;
        |a_ii| ramps up; safety filter regains turn-rate authority;
        identifiability re-engages.

    Below each panel: |a_ii(t)| trace + bar_rho_i running average.
    """
    fig, axes = plt.subplots(2, 2, figsize=(11, 6),
                              gridspec_kw={"height_ratios": [3, 1]})

    for col, (name, out) in enumerate([
        (r"$A_e = 0$ (head-on locus, Filippov sliding)", out_no_pe),
        (r"$A_e > 0$ (PE breaks locus, identifiability re-engages)", out_with_pe),
    ]):
        # Top: trajectory plot with oriented triangles
        ax = axes[0, col]
        r = out["r"]
        v_a = out["v_a"]
        N = r.shape[1]
        for i in range(N):
            xs = r[:, i].real
            ys = r[:, i].imag
            ax.plot(xs, ys, color=AGENT_COLOURS[i], linewidth=1.4, alpha=0.85,
                    label=f"agent {i}")
            _draw_oriented_triangle(ax, xs[0], ys[0], np.angle(v_a[0, i]),
                                     color=AGENT_COLOURS[i], alpha=0.35, scale=0.15)
            _draw_oriented_triangle(ax, xs[-1], ys[-1], np.angle(v_a[-1, i]),
                                     color=AGENT_COLOURS[i], alpha=0.95, scale=0.15)
        ax.set_aspect("equal")
        ax.set_xlabel(r"$\Re(r_i)$ [m]")
        if col == 0:
            ax.set_ylabel(r"$\Im(r_i)$ [m]")
        ax.set_title(name)

        # Compute |a_ii| over time for the (0, 1) pair
        a_ii_traj = np.array([
            2.0 * np.imag((r[t, 0] - r[t, 1]) * np.conj(v_a[t, 0]))
            for t in range(len(out["t"]))
        ])

        # Bottom: |a_ii(t)| trace
        ax = axes[1, col]
        ax.plot(out["t"], np.abs(a_ii_traj), color="#d62728", linewidth=1.4,
                label=r"$|a_{11}(t)|$")
        ax.axhline(1.6, color="black", linewidth=0.7, linestyle=":",
                    label=r"$\eta_a^{\rm practical} \approx 1.6$ (recoverability)")
        ax.set_xlabel("time [s]")
        if col == 0:
            ax.set_ylabel(r"$|a_{11}(t)|$")
        ax.set_yscale("log")
        ax.set_ylim(1e-4, 10)
        ax.legend(loc="lower right", fontsize=8)

    fig.suptitle(
        "Figure 7 — v17 §8.1 N=2 head-on Filippov demonstration\n"
        "(left: relative-degree drop with slack absorbing; right: PE breaks the locus)",
        fontsize=12, y=1.02
    )
    fig.tight_layout()
    fig.savefig(save, bbox_inches="tight")
    plt.close(fig)
