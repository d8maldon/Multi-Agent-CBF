"""
Multi-agent formation control with adaptive control + CBF safety filters,
following Solano-Castellanos, Fisher, Annaswamy (arXiv 2403.15674, MECC 2025).

Architecture per agent i:

  Plant:          dx_i/dt  =  Λ_i  u_i             (Λ_i unknown, sign known)
  Reference:      dz_i/dt  =  u_i_ref              (driven by formation law)
  Adaptive law:   d θ̂_i/dt =  −γ  u_i_ref^T (x_i − z_i)
  Adaptive ctrl:  u_i      =  θ̂_i  u_i_ref         (θ̂_i ≈ 1 / Λ_i)
  Safety filter:  u_i^safe =  argmin_u  ‖u − u_i‖²
                              subject to  ZCBF inter-agent constraints

Reference formation law (distributed, neighbours only):

  u_i_ref  =  −K_target (z_i − t_i)
              −K_form  Σ_{j ∈ N_i}  [ (z_i − z_j)  −  (t_i − t_j) ]

Inter-agent CBF (pairwise, with i < j):

  h_ij(x)   =  ‖x_i − x_j‖²  −  r_safe²        (≥ 0 means safe)
  d h_ij/dt =  2 (x_i − x_j)^T (ẋ_i − ẋ_j)
  Constraint:  d h_ij/dt  +  α h_ij  ≥  0

The safety filter operates in nominal-plant coordinates (assumes ẋ ≈ u after
adaptation has converged); a more conservative variant would operate on the
reference trajectory z directly, as the paper does.

Run:  python multi_agent_cbf.py
"""

from __future__ import annotations

from pathlib import Path

import cvxpy as cp
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE / "output"
OUT.mkdir(exist_ok=True)

plt.rcParams.update(
    {
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "axes.edgecolor": "#444444",
        "axes.labelcolor": "#1f1f1f",
        "xtick.color": "#1f1f1f",
        "ytick.color": "#1f1f1f",
        "axes.titleweight": "bold",
        "font.size": 10,
    }
)

AGENT_COLORS = ["#0891b2", "#d97706", "#16a34a", "#7c3aed"]


# ----------------------------- Simulation core -----------------------


class MultiAgentSim:
    def __init__(
        self,
        n_agents: int = 4,
        dt: float = 0.05,
        K_target: float = 0.5,
        K_form: float = 0.3,
        gamma_adapt: float = 0.15,
        alpha_cbf: float = 10.0,
        r_safe: float = 0.40,
        u_max: float = 1.0,
    ):
        self.N = n_agents
        self.dt = dt
        self.K_target = K_target
        self.K_form = K_form
        self.gamma = gamma_adapt
        self.alpha = alpha_cbf
        self.r_safe = r_safe
        self.u_max = u_max
        # Default fully-connected neighbour graph
        self.neighbours = {i: [j for j in range(n_agents) if j != i] for i in range(n_agents)}

    def reference_command(self, z, t_targets):
        """Distributed formation reference: per-agent velocity that drives
        each agent's reference state z_i toward its slot t_i while keeping
        the formation cohesive across neighbours."""
        u_ref = np.zeros_like(z)
        for i in range(self.N):
            u_ref[i] = -self.K_target * (z[i] - t_targets[i])
            for j in self.neighbours[i]:
                u_ref[i] -= self.K_form * ((z[i] - z[j]) - (t_targets[i] - t_targets[j]))
        return u_ref

    def safety_filter(self, x, u_nom):
        """Per-agent QP that finds u_safe minimising ‖u - u_nom‖² subject to
        every pairwise ZCBF constraint with the agent's neighbours.
        Returns the saturated, safety-filtered command for every agent."""
        u_safe = np.zeros_like(u_nom)
        for i in range(self.N):
            u = cp.Variable(2)
            constraints = []
            for j in self.neighbours[i]:
                d = x[i] - x[j]
                h = float(d @ d - self.r_safe ** 2)
                # Half the assumption: agent j moves with its nominal command;
                # the agent computes its own safe u taking j's plan as given.
                # Symmetry comes from each agent doing the same in parallel.
                d_dot_uj = 2 * d @ u_nom[j]
                # h_dot = 2 d^T (u - u_j) ; constraint 2 d^T u  ≥ 2 d^T u_j - α h
                constraints.append(2 * d @ u - d_dot_uj + self.alpha * h >= 0)
            constraints.append(cp.norm_inf(u) <= self.u_max)
            prob = cp.Problem(cp.Minimize(cp.sum_squares(u - u_nom[i])), constraints)
            try:
                prob.solve(solver=cp.OSQP, verbose=False)
                if u.value is None or prob.status not in ("optimal", "optimal_inaccurate"):
                    u_safe[i] = u_nom[i]
                else:
                    u_safe[i] = np.clip(u.value, -self.u_max, self.u_max)
            except Exception:
                u_safe[i] = u_nom[i]
        return u_safe

    def simulate(
        self,
        x0,
        t_targets,
        Lambda,
        T: float = 18.0,
        use_adaptive: bool = True,
        use_cbf: bool = True,
        theta_init: float = 1.0,
    ):
        steps = int(T / self.dt)
        # State arrays: x = plant state, z = reference state, theta_hat = adaptive estimate
        x = x0.copy()
        z = x0.copy()
        theta_hat = theta_init * np.ones(self.N)  # scalar per agent

        # Logs
        log_x = np.zeros((steps + 1, self.N, 2))
        log_z = np.zeros((steps + 1, self.N, 2))
        log_theta = np.zeros((steps + 1, self.N))
        log_min_sep = np.zeros(steps + 1)
        log_track_err = np.zeros((steps + 1, self.N))
        log_x[0] = x
        log_z[0] = z
        log_theta[0] = theta_hat

        def min_separation(state):
            d = np.inf
            for i in range(self.N):
                for j in range(i + 1, self.N):
                    d = min(d, np.linalg.norm(state[i] - state[j]))
            return d

        log_min_sep[0] = min_separation(x)

        for k in range(steps):
            u_ref = self.reference_command(z, t_targets)

            # Saturate the reference command itself so that the reference
            # trajectory z stays inside the plant's reachable speed envelope.
            # Without this, z outruns x in every step, which makes the
            # adaptive law's tracking-error sign degenerate.
            ref_norms = np.linalg.norm(u_ref, axis=1, keepdims=True)
            scale = np.where(ref_norms > self.u_max, self.u_max / np.maximum(ref_norms, 1e-9), 1.0)
            u_ref = u_ref * scale

            # Adaptive control: u_i = θ̂_i  u_i_ref. Allow the actuator to
            # exceed u_max by 50 % to give the controller headroom for
            # under-gained plants (Λ < 1 → θ̂ > 1).
            if use_adaptive:
                u_nom = (theta_hat[:, None]) * u_ref
            else:
                u_nom = u_ref.copy()
            u_nom = np.clip(u_nom, -1.5 * self.u_max, 1.5 * self.u_max)

            # CBF safety filter
            if use_cbf:
                u_applied = self.safety_filter(x, u_nom)
            else:
                u_applied = u_nom

            # True plant dynamics (with unknown gain Lambda)
            x_dot = Lambda[:, None] * u_applied  # element-wise scaling per agent
            x = x + x_dot * self.dt

            # Reference dynamics
            z = z + u_ref * self.dt

            # Normalised adaptive law to keep updates bounded when the
            # reference command is large; the gain effectively becomes
            # γ / (1 + ‖u_ref‖²), a standard MRAC robustness trick.
            if use_adaptive:
                e = x - z
                for i in range(self.N):
                    norm_sq = 1.0 + float(np.dot(u_ref[i], u_ref[i]))
                    theta_hat[i] -= (self.gamma / norm_sq) * np.dot(u_ref[i], e[i]) * self.dt
                theta_hat = np.clip(theta_hat, 0.1, 4.0)

            log_x[k + 1] = x
            log_z[k + 1] = z
            log_theta[k + 1] = theta_hat
            log_min_sep[k + 1] = min_separation(x)
            for i in range(self.N):
                log_track_err[k + 1, i] = np.linalg.norm(x[i] - t_targets[i])

        return {
            "x": log_x,
            "z": log_z,
            "theta": log_theta,
            "min_sep": log_min_sep,
            "track_err": log_track_err,
            "Lambda": Lambda.copy(),
            "t_targets": t_targets.copy(),
            "x0": x0.copy(),
            "T": T,
            "dt": self.dt,
        }


# ------------------------- Diagnostic plots -------------------------


def plot_trajectories(sim, title, save):
    fig, ax = plt.subplots(figsize=(8, 7))
    x = sim["x"]
    t_targets = sim["t_targets"]
    x0 = sim["x0"]

    # Trajectories
    for i in range(x.shape[1]):
        ax.plot(x[:, i, 0], x[:, i, 1], color=AGENT_COLORS[i], linewidth=1.6, alpha=0.7,
                label=f"agent {i+1}")
    # Initial
    for i in range(x.shape[1]):
        ax.scatter(*x0[i], color=AGENT_COLORS[i], s=140, alpha=0.55,
                   edgecolor="black", linewidth=0.6, zorder=5)
    # Final
    for i in range(x.shape[1]):
        ax.scatter(*x[-1, i], color=AGENT_COLORS[i], s=140, marker="D",
                   edgecolor="black", linewidth=0.6, zorder=6)
    # Target slots
    for i in range(x.shape[1]):
        ax.scatter(*t_targets[i], color=AGENT_COLORS[i], s=190, marker="X",
                   edgecolor="black", linewidth=0.6, alpha=0.9, zorder=7)

    ax.set_xlim(-4.5, 4.5)
    ax.set_ylim(-4.5, 4.5)
    ax.set_aspect("equal")
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.grid(alpha=0.3)
    ax.legend(loc="upper left", fontsize=9)
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(save, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_comparison(sims, labels, title, save):
    fig, axes = plt.subplots(1, len(sims), figsize=(6.5 * len(sims), 6.5))
    for ax, sim, lab in zip(axes, sims, labels):
        x = sim["x"]
        t_targets = sim["t_targets"]
        x0 = sim["x0"]
        for i in range(x.shape[1]):
            ax.plot(x[:, i, 0], x[:, i, 1], color=AGENT_COLORS[i], linewidth=1.4, alpha=0.7)
            ax.scatter(*x0[i], color=AGENT_COLORS[i], s=130, alpha=0.55,
                       edgecolor="black", linewidth=0.5, zorder=5)
            ax.scatter(*x[-1, i], color=AGENT_COLORS[i], s=130, marker="D",
                       edgecolor="black", linewidth=0.5, zorder=6)
            ax.scatter(*t_targets[i], color=AGENT_COLORS[i], s=170, marker="X",
                       edgecolor="black", linewidth=0.5, alpha=0.85, zorder=7)
        ax.set_xlim(-4.5, 4.5)
        ax.set_ylim(-4.5, 4.5)
        ax.set_aspect("equal")
        ax.grid(alpha=0.3)
        # Final tracking error
        final_err = np.mean([np.linalg.norm(x[-1, i] - t_targets[i]) for i in range(x.shape[1])])
        min_sep = sim["min_sep"].min()
        ax.set_title(f"{lab}\nmean final ‖x − t‖ = {final_err:.3f}    min sep = {min_sep:.3f}")
    fig.suptitle(title, fontsize=12, fontweight="bold")
    fig.tight_layout()
    fig.savefig(save, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_parameter_convergence(sim, save):
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    t = np.arange(sim["theta"].shape[0]) * sim["dt"]
    for i in range(sim["theta"].shape[1]):
        axes[0].plot(t, sim["theta"][:, i], color=AGENT_COLORS[i], linewidth=1.6,
                     label=f"agent {i+1}: θ̂ → {1/sim['Lambda'][i]:.2f}")
        axes[0].axhline(1 / sim["Lambda"][i], color=AGENT_COLORS[i], linestyle=":", alpha=0.6)
    axes[0].set_xlabel("time (s)")
    axes[0].set_ylabel("θ̂_i")
    axes[0].set_title("Adaptive parameter estimates  (dotted = true 1/Λ_i)")
    axes[0].grid(alpha=0.3)
    axes[0].legend(loc="upper right", fontsize=9)

    for i in range(sim["track_err"].shape[1]):
        axes[1].plot(t, sim["track_err"][:, i], color=AGENT_COLORS[i], linewidth=1.6,
                     label=f"agent {i+1}")
    axes[1].set_xlabel("time (s)")
    axes[1].set_ylabel("‖x_i − t_i‖")
    axes[1].set_title("Per-agent target-tracking error")
    axes[1].grid(alpha=0.3)
    axes[1].legend(loc="upper right", fontsize=9)

    fig.suptitle("Adaptation diagnostics", fontsize=12, fontweight="bold")
    fig.tight_layout()
    fig.savefig(save, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_safety(sims, labels, save, r_safe=0.40):
    fig, ax = plt.subplots(figsize=(11, 5))
    for sim, lab in zip(sims, labels):
        t = np.arange(sim["min_sep"].shape[0]) * sim["dt"]
        ax.plot(t, sim["min_sep"], linewidth=1.8, label=lab)
    ax.axhline(r_safe, color="#dc2626", linestyle="--", linewidth=1.5,
               label=f"safety threshold r_safe = {r_safe}")
    ax.set_xlabel("time (s)")
    ax.set_ylabel("min pairwise inter-agent distance")
    ax.set_title("Inter-agent separation over time, four conditions")
    ax.legend(loc="upper right", fontsize=9)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(save, dpi=150, bbox_inches="tight")
    plt.close(fig)


# ------------------------------- Main -------------------------------


def main():
    rng = np.random.default_rng(42)
    sim_engine = MultiAgentSim(n_agents=4)

    # Initial positions: spread around origin
    x0 = np.array([[-3.0, -3.0], [3.0, -3.0], [3.0, 3.0], [-3.0, 3.0]])

    # Target formation: rotated square (cross-swap from start positions:
    # each agent goes to the slot diagonally opposite, which forces collision
    # risk through the centre and exercises the CBF filter)
    t_targets = -x0.copy()

    # True unknown gains
    Lambda_true = np.array([0.6, 1.4, 0.9, 1.6])
    print(f"True Lambda per agent: {Lambda_true}")
    print(f"Target  1/Lambda:     {1/Lambda_true}")

    print("\nScenario 1: Nominal (Lambda=1, no AC, no CBF)")
    sim_nom = sim_engine.simulate(x0, t_targets, np.ones(4),
                                  use_adaptive=False, use_cbf=False)
    print(f"  min sep = {sim_nom['min_sep'].min():.3f}")

    print("\nScenario 2: Uncertain plant, NO adaptive control, NO CBF")
    sim_unc = sim_engine.simulate(x0, t_targets, Lambda_true,
                                  use_adaptive=False, use_cbf=False)
    print(f"  min sep = {sim_unc['min_sep'].min():.3f}, mean tracking err = "
          f"{sim_unc['track_err'][-1].mean():.3f}")

    print("\nScenario 3: Uncertain plant, adaptive control ON, CBF OFF")
    sim_ac = sim_engine.simulate(x0, t_targets, Lambda_true,
                                 use_adaptive=True, use_cbf=False)
    print(f"  min sep = {sim_ac['min_sep'].min():.3f}, mean tracking err = "
          f"{sim_ac['track_err'][-1].mean():.3f}")
    print(f"  final theta_hat = {sim_ac['theta'][-1]}")
    print(f"  target  = {1/Lambda_true}")

    print("\nScenario 4: Uncertain plant + adaptive control + CBF safety filter")
    sim_full = sim_engine.simulate(x0, t_targets, Lambda_true,
                                   use_adaptive=True, use_cbf=True)
    print(f"  min sep = {sim_full['min_sep'].min():.3f}, mean tracking err = "
          f"{sim_full['track_err'][-1].mean():.3f}")
    print(f"  final theta_hat = {sim_full['theta'][-1]}")

    # ----- Figures -----

    # 4-panel comparison
    plot_comparison(
        [sim_nom, sim_unc, sim_ac, sim_full],
        ["1. Nominal (Λ=1)",
         "2. Uncertain, no AC, no CBF",
         "3. Uncertain + AC, no CBF",
         "4. Uncertain + AC + CBF"],
        "Cross-swap formation: four conditions",
        OUT / "01_four_conditions.png",
    )

    # Single-condition trajectory: AC + CBF (the headline)
    plot_trajectories(sim_full, "Adaptive control + CBF safety filter on cross-swap",
                      OUT / "02_full_system.png")

    # Adaptation diagnostics on AC + CBF run
    plot_parameter_convergence(sim_full, OUT / "03_adaptation.png")

    # Safety: min separation over time, all four conditions
    plot_safety([sim_nom, sim_unc, sim_ac, sim_full],
                ["1. Nominal", "2. Uncertain, no AC/CBF", "3. + AC", "4. + AC + CBF"],
                OUT / "04_safety.png")

    print(f"\nFigures saved to {OUT}")


if __name__ == "__main__":
    main()
