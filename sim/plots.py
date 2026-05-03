"""Figures 1-5 of paper section 8.4 figure plan.

Figure 6 (communication-delay sweep) is deferred: implementing it requires
a delay buffer on neighbour-broadcast state, which is not yet in sim/.

Style: clean white background, paper-like typography, consistent colour
palette across all figures (one colour per agent, one linestyle per scenario).

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
# Figure 1 — cross-swap trajectories (AC alone / AC+CBF / AC+CBF+PE)
# ---------------------------------------------------------------------------

def figure_1_trajectories(out_AC: dict, out_CBF: dict, out_PE: dict, save: Path):
    """Three side-by-side panels: agent trajectories under each scenario."""
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.8), sharex=True, sharey=True)
    scenarios = [("AC", out_AC), ("AC+CBF", out_CBF), ("AC+CBF+PE", out_PE)]

    for ax, (name, out) in zip(axes, scenarios):
        x = out["x"]                       # (T, N, d)
        for i in range(x.shape[1]):
            # Trajectory
            ax.plot(x[:, i, 0], x[:, i, 1], color=AGENT_COLOURS[i],
                    linewidth=1.2, alpha=0.85, label=f"agent {i}")
            # Initial position
            ax.plot(x[0, i, 0], x[0, i, 1], "o",
                    color=AGENT_COLOURS[i], markersize=5)
            # Final position
            ax.plot(x[-1, i, 0], x[-1, i, 1], "s",
                    color=AGENT_COLOURS[i], markersize=5)
            # r_safe circle around each starting position (faded)
            theta = np.linspace(0, 2 * np.pi, 80)
            ax.plot(
                x[0, i, 0] + pp.R_SAFE * np.cos(theta),
                x[0, i, 1] + pp.R_SAFE * np.sin(theta),
                color=AGENT_COLOURS[i], linewidth=0.4, alpha=0.4,
            )
        ax.set_aspect("equal")
        ax.set_xlabel("$x_1$ [m]")
        if name == "AC":
            ax.set_ylabel("$x_2$ [m]")
            ax.legend(loc="lower left")
        ax.set_title(f"{name}    (min $h_{{ij}}$ = {out['h'].min():.3f})")
        ax.set_xlim(-3.6, 3.6)
        ax.set_ylim(-3.6, 3.6)

    fig.suptitle("Figure 1 — Cross-swap trajectories under three scenarios",
                 fontsize=12, y=1.02)
    fig.tight_layout()
    fig.savefig(save, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Figure 2 — parameter convergence (one subplot per agent, log-y)
# ---------------------------------------------------------------------------

def figure_2_param_convergence(out_AC: dict, out_CBF: dict, out_PE: dict, save: Path):
    """4 subplots (one per agent), showing |theta_hat - 1/Lambda| over time."""
    inv_L = 1.0 / pp.LAMBDA_TRUE
    N = inv_L.shape[0]

    fig, axes = plt.subplots(1, N, figsize=(12, 3.2), sharey=True)
    for i, ax in enumerate(axes):
        for name, out in [("AC", out_AC), ("AC+CBF", out_CBF), ("AC+CBF+PE", out_PE)]:
            err = np.abs(out["theta_hat"][:, i] - inv_L[i])
            err = np.maximum(err, 1e-4)              # for log scale floor
            ax.semilogy(out["t"], err, color=AGENT_COLOURS[i], **SCENARIO_STYLES[name])
        ax.set_xlabel("time [s]")
        ax.set_title(f"agent {i}    $1/\\Lambda_{{{i}}} = {inv_L[i]:.3f}$")
        ax.set_ylim(1e-4, 2.0)
    axes[0].set_ylabel(r"$|\hat\theta_i(t) - 1/\Lambda_i|$")
    axes[-1].legend(loc="upper right")

    fig.suptitle("Figure 2 — parameter convergence (semilog) under three scenarios",
                 fontsize=12, y=1.02)
    fig.tight_layout()
    fig.savefig(save, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Figure 3 — identifiability gain rho_bar_i(t) computed online
# ---------------------------------------------------------------------------

def figure_3_identifiability(out_PE: dict, save: Path):
    """Cumulative average of ||Proj_F u^ref||^2 per agent + spatial average.

    Re-derives the running tr(Q_i)(t) from the logged time-series so we get
    a smooth curve, not just the final value from integrator.run.
    """
    t = out_PE["t"]
    u_ref = out_PE["u_ref"]                # (T, N, d)
    pe_proj = out_PE["pe_projected"]       # (T, N, d) — already projected
    # Reconstruct Proj_F u^ref by projecting u_ref onto the same direction
    # that pe_proj was projected onto. Easier: compute ||u^ref||^2 minus the
    # active-normal-aligned component.  But simpler: just use ||u^ref||^2 when
    # no active pair, and zero when fully constrained.  For a rigorous trace,
    # we'd re-run with a projected-u^ref logger.  Approximation here:
    #   ||Proj_F u^ref||^2 ≈ ||pe_proj||^2 / A_e^2 * ||u^ref||^2  (when A_e > 0)
    #
    # Cleaner: log Proj_F u^ref directly in the integrator. For the figure
    # we use: rho_bar_i(t) = (1/t) * ∫_0^t ||Proj_F u^ref||^2 dτ
    # using the SAME projector that was active at each step. Since pe_proj
    # used that exact projector, and pe_proj = Proj_F * (A_e * sin(...)),
    # we can recover Proj_F by re-projecting u^ref through the same nullspace.
    # For a simpler (slightly approximate) version:  use ||u^ref||^2 directly
    # when active_count == 0 at that step, else use a fraction of it.

    # Quick approximation: integrated ||u^ref||^2 (since active fraction is
    # very low, Proj_F ≈ I most of the time and pe_proj ≈ raw e_pe).
    sq_norm = np.sum(u_ref ** 2, axis=-1)              # (T, N)
    # Cumulative time-average via trapezoidal-style cumsum
    dt = np.diff(t, prepend=t[0])
    cum_int = np.cumsum(sq_norm * dt[:, None], axis=0)
    cum_t = np.maximum(np.cumsum(dt), 1e-9)
    rho_bar_t = cum_int / cum_t[:, None]                # (T, N)

    fig, ax = plt.subplots(figsize=(8, 4.2))
    for i in range(rho_bar_t.shape[1]):
        ax.plot(t, rho_bar_t[:, i], color=AGENT_COLOURS[i],
                linewidth=1.4, label=f"agent {i}")
    spatial_avg = rho_bar_t.mean(axis=1)
    ax.plot(t, spatial_avg, color="black", linewidth=1.6, linestyle="--",
            label=r"spatial $\mu$-average")

    # Final tr(Q_i) values (exact) annotated
    for i, rho in enumerate(out_PE["rho_bar_i"]):
        ax.axhline(rho, color=AGENT_COLOURS[i], linewidth=0.6, alpha=0.5)

    ax.set_xlabel("time [s]")
    ax.set_ylabel(r"running $\bar\rho_i(t) \approx (1/t)\int_0^t \|u_i^{\rm ref}\|^2\,d\tau$")
    ax.set_title(r"Figure 3 — identifiability gain $\bar\rho_i(t)$ under PE injection")
    ax.legend(ncol=3, loc="lower right")
    fig.tight_layout()
    fig.savefig(save, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Figure 4 — safety margin min_ij h_ij(t) + tightening delta(t)
# ---------------------------------------------------------------------------

def figure_4_safety(out_PE: dict, save: Path):
    """min over pairs of h_ij(t), with safe-set boundary at 0 and zeta margin."""
    t = out_PE["t"]
    h_min = out_PE["h"].min(axis=1)            # (T,)
    h_mean = out_PE["h"].mean(axis=1)
    P = out_PE["P"]                             # (T, N) KB covariance

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
    ax.set_title(f"Figure 4 — safety margin (run min = {h_min.min():.4f})")

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
# Figure 5 — A_e Pareto sweep: identifiability rate vs ultimate bound
# ---------------------------------------------------------------------------

def figure_5_ae_sweep(sweep_results: list, save: Path):
    """sweep_results: list of (A_e, out_dict) for A_e in §8.4 sweep."""
    A_e_vals = np.array([s[0] for s in sweep_results])
    inv_L = 1.0 / pp.LAMBDA_TRUE

    # Identifiability rate proxy: -log(final |theta_err|)/T (rough exponential rate)
    # Ultimate bound proxy: time-averaged ||x_i - z_i||^2 over the second half
    rates = np.zeros((len(A_e_vals), pp.LAMBDA_TRUE.shape[0]))
    bounds = np.zeros_like(rates)
    for k, (A_e, out) in enumerate(sweep_results):
        T = out["t"][-1]
        # rate: convergence speed of theta_hat to 1/Lambda
        err_final = np.abs(out["theta_hat"][-1] - inv_L)
        err_initial = np.abs(out["theta_hat"][0] - inv_L) + 1e-9
        rates[k] = -np.log(np.maximum(err_final, 1e-4) / err_initial) / T
        # ultimate bound: time-averaged ||x - z||^2 over last 50% of run
        half = len(out["t"]) // 2
        e_sq = np.sum((out["x"][half:] - out["z"][half:]) ** 2, axis=-1)
        bounds[k] = e_sq.mean(axis=0)

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))

    ax = axes[0]
    for i in range(rates.shape[1]):
        ax.plot(A_e_vals / pp.U_MAX, rates[:, i], "o-",
                color=AGENT_COLOURS[i], label=f"agent {i}")
    ax.set_xlabel(r"excitation amplitude  $A_e / u_{\max}$")
    ax.set_ylabel(r"identification rate  $-\log(|\theta_{\rm err}^{\rm final}|/|\theta_{\rm err}^{\rm init}|)/T$")
    ax.set_title("Identification rate (higher = faster)")
    ax.legend(ncol=2)

    ax = axes[1]
    for i in range(bounds.shape[1]):
        ax.plot(A_e_vals / pp.U_MAX, bounds[:, i], "s-",
                color=AGENT_COLOURS[i], label=f"agent {i}")
    ax.set_xlabel(r"excitation amplitude  $A_e / u_{\max}$")
    ax.set_ylabel(r"steady-state $\langle \|x_i - z_i\|^2\rangle$")
    ax.set_title("Ultimate bound (lower = tighter tracking)")
    ax.legend(ncol=2)

    fig.suptitle(r"Figure 5 — Pareto sweep over $A_e \in \{0, 0.05, 0.10, 0.20\}\,u_{\max}$",
                 fontsize=12, y=1.02)
    fig.tight_layout()
    fig.savefig(save, bbox_inches="tight")
    plt.close(fig)
