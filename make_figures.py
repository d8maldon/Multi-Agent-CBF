"""Generate v16 paper section 8.4 figures 1-5 for the cross-swap scenario.

Runs:
  - 3 scenarios for figs 1, 2 (AC alone, AC+CBF, AC+CBF+PE)
  - 4 A_e values for fig 5 (0, 0.05, 0.10, 0.20 * u_max)
Total: 7 sims, each ~10-20s wall time on a desktop CPU.

Outputs to:  output/v16/figure_{1..5}.pdf

Note: figure 6 (communication-delay sweep) is deferred — the sim does not
yet model neighbour-broadcast latency. Will require a delay buffer on
state.x[j] inputs to the QP.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

from sim import paper_params as pp
from sim import integrator
from sim import plots


HERE = Path(__file__).resolve().parent
OUT = HERE / "output" / "v16"
OUT.mkdir(parents=True, exist_ok=True)


# Cross-swap scenario, fixed across all runs in this driver
def crossswap_run(A_e: float, T_final: float, log_every: int,
                  use_safety_filter: bool = True,
                  comm_delay: float = 0.0) -> dict:
    """One section 8.2 cross-swap run with given excitation amplitude + delay."""
    return integrator.run(
        x0=pp.CROSSSWAP_X0,
        z0=pp.CROSSSWAP_X0.copy(),
        edges=pp.CROSSSWAP_EDGES,
        t_targets_fn=pp.crossswap_targets_oscillating,
        A_e=A_e,
        T_final=T_final,
        log_every=log_every,
        use_safety_filter=use_safety_filter,
        comm_delay=comm_delay,
    )


def _summary(name, out):
    err = np.linalg.norm(out['theta_hat'][-1] - 1.0 / pp.LAMBDA_TRUE)
    return (f"     [{name}] wall {out['wall_time_s']:.1f}s, min h = "
            f"{out['h'].min():.3f}, theta-err = {err:.3f}")


def main(quick: bool = False):
    if quick:
        T_final, log_every = 4.0, 8
    else:
        T_final, log_every = 16.0, 8        # 4 full swap cycles for fig 2 convergence
    print(f"Cross-swap (v16): T_final = {T_final} s, log_every = {log_every}.")
    print()

    t0 = time.time()

    # --- 3 scenarios for figures 1 + 2 ---
    print("[1/3] AC alone  (no safety filter, no PE)")
    out_AC = crossswap_run(0.0, T_final, log_every, use_safety_filter=False)
    print(_summary("AC", out_AC))

    print("[2/3] AC + CBF  (safety filter on, no PE)")
    out_CBF = crossswap_run(0.0, T_final, log_every, use_safety_filter=True)
    print(_summary("AC+CBF", out_CBF))

    print("[3/3] AC + CBF + PE  (paper headline scenario, A_e = 0.10 u_max)")
    out_PE = crossswap_run(0.10 * pp.U_MAX, T_final, log_every, use_safety_filter=True)
    print(_summary("AC+CBF+PE", out_PE))

    # --- A_e Pareto sweep for figure 5 (re-use out_CBF for A_e = 0) ---
    print("[A_e sweep] for figure 5:")
    sweep = []
    for A_e_frac in [0.0, 0.05, 0.10, 0.20]:
        A_e = A_e_frac * pp.U_MAX
        if A_e_frac == 0.0:
            out = out_CBF
            print(f"     A_e/u_max = {A_e_frac:.2f}: re-using AC+CBF run")
        elif np.isclose(A_e_frac, 0.10):
            out = out_PE
            print(f"     A_e/u_max = {A_e_frac:.2f}: re-using AC+CBF+PE run")
        else:
            print(f"     A_e/u_max = {A_e_frac:.2f}: running...")
            out = crossswap_run(A_e, T_final, log_every, use_safety_filter=True)
            print(_summary(f"A_e={A_e_frac:.2f}", out))
        sweep.append((A_e, out))

    # --- Communication-delay sweep for figure 6 ---
    print("[comm-delay sweep] for figure 6:")
    delay_runs = []
    for tau_ms in [0, 5, 20, 50, 100]:
        if tau_ms == 0:
            out = out_PE   # already have A_e=0.10 u_max, delay=0 result
            print(f"     tau = {tau_ms} ms: re-using AC+CBF+PE run")
        else:
            print(f"     tau = {tau_ms} ms: running...")
            out = crossswap_run(0.10 * pp.U_MAX, T_final, log_every,
                                use_safety_filter=True, comm_delay=tau_ms * 1e-3)
            print(_summary(f"tau={tau_ms}ms", out))
        delay_runs.append((tau_ms, out))

    print()
    print("Generating figures...")
    plots.figure_1_trajectories(out_AC, out_CBF, out_PE, OUT / "figure_1_trajectories.pdf")
    plots.figure_2_param_convergence(out_AC, out_CBF, out_PE, OUT / "figure_2_param_convergence.pdf")
    plots.figure_3_identifiability(out_PE, OUT / "figure_3_identifiability.pdf")
    plots.figure_4_safety(out_PE, OUT / "figure_4_safety.pdf")
    plots.figure_5_ae_sweep(sweep, OUT / "figure_5_ae_sweep.pdf")
    plots.figure_6_comm_delay(delay_runs, OUT / "figure_6_comm_delay.pdf")

    print()
    print(f"All 6 figures written to {OUT}/")
    print(f"Total wall time: {time.time() - t0:.1f} s")


if __name__ == "__main__":
    main(quick=("--quick" in sys.argv))
