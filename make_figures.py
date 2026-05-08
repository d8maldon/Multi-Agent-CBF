"""Generate v17 paper §8.4 figures 1-7 (council-vetted Passes 19-30).

v17 differences from v16:
- Plant state is complex (r, v_a) in C^2 per agent; agents follow curved
  Dubins paths instead of straight lines.
- Output to output/v17/ (v16 figures retained at output/v16/).
- Figure 7 NEW: §8.1 N=2 head-on Filippov sliding-mode demonstration.
- Figure 1 uses oriented-triangle agent rendering (psi = arg(v_a)).

Runs:
  - 3 cross-swap scenarios for figs 1, 2 (AC alone, AC+CBF, AC+CBF+PE)
  - 4 A_e values for fig 5 (0, 0.05, 0.10, 0.20 * psi_dot_max)
  - 5 comm-delay values for fig 6 (0, 5, 20, 50, 100 ms)
  - 2 N=2 head-on scenarios for fig 7 (no PE / with PE)
Total: 9 cross-swap sims + 2 head-on sims; ~1-2 min wall time on a desktop CPU.

Outputs to: output/v17/figure_{1..7}.pdf
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
OUT = HERE / "output" / "v17"
OUT.mkdir(parents=True, exist_ok=True)


def crossswap_run(A_e: float, T_final: float, log_every: int,
                   use_safety_filter: bool = True,
                   comm_delay: float = 0.0) -> dict:
    """One §8.2 cross-swap run with given excitation amplitude + delay (v17)."""
    r0 = pp.CROSSSWAP_R0.copy()
    v_a0 = pp.crossswap_v0()
    return integrator.run(
        r0=r0, v_a0=v_a0,
        r_ref0=r0.copy(), v_ref0=v_a0.copy(),
        edges=pp.CROSSSWAP_EDGES,
        t_targets_fn=pp.crossswap_targets_oscillating,
        A_e=A_e,
        T_final=T_final,
        log_every=log_every,
        use_safety_filter=use_safety_filter,
        comm_delay=comm_delay,
    )


def headon_run(A_e: float, T_final: float, log_every: int) -> dict:
    """One §8.1 N=2 head-on closing run with given PE amplitude (v17)."""
    L = 1.0  # initial separation
    r0 = np.array([-L + 0.0j, L + 0.0j], dtype=complex)
    v_a0 = pp.V_0 * np.array([1.0 + 0.0j, -1.0 + 0.0j])  # head-on
    edges = ((0, 1),)
    # Constant target: agents heading straight toward each other (reference is
    # frozen at their initial positions; the cross-swap target_fn isn't used).

    def constant_targets(t: float) -> np.ndarray:
        return r0.copy()

    return integrator.run(
        r0=r0, v_a0=v_a0,
        r_ref0=r0.copy(), v_ref0=v_a0.copy(),
        edges=edges,
        t_targets_fn=constant_targets,
        A_e=A_e,
        T_final=T_final,
        log_every=log_every,
        use_safety_filter=True,
        comm_delay=0.0,
    )


def _summary(name: str, out: dict) -> str:
    N = out['theta_hat'].shape[1]   # support N=2 head-on as well as N=4 cross-swap
    err = float(np.linalg.norm(out['theta_hat'][-1] - 1.0 / pp.LAMBDA_TRUE[:N]))
    return (f"     [{name}] wall {out['wall_time_s']:.1f}s, min h = "
            f"{out['h'].min():.3f}, theta-err = {err:.3f}")


def main(quick: bool = False):
    if quick:
        T_cross, log_cross = 4.0, 8
        T_headon, log_headon = 0.6, 4
    else:
        T_cross, log_cross = 16.0, 8
        T_headon, log_headon = 1.0, 4
    print(f"v17 cross-swap: T_final = {T_cross} s, log_every = {log_cross}")
    print(f"v17 head-on:    T_final = {T_headon} s, log_every = {log_headon}")
    print()

    t0 = time.time()

    # --- 3 cross-swap scenarios for figures 1 + 2 ---
    print("[1/3] AC alone  (no safety filter, no PE)")
    out_AC = crossswap_run(0.0, T_cross, log_cross, use_safety_filter=False)
    print(_summary("AC", out_AC))

    print("[2/3] AC + CBF  (safety filter on, no PE)")
    out_CBF = crossswap_run(0.0, T_cross, log_cross, use_safety_filter=True)
    print(_summary("AC+CBF", out_CBF))

    print("[3/3] AC + CBF + PE  (paper headline scenario, A_e = 0.10*psi_dot_max)")
    out_PE = crossswap_run(0.10 * pp.PSI_DOT_MAX, T_cross, log_cross,
                            use_safety_filter=True)
    print(_summary("AC+CBF+PE", out_PE))

    # --- A_e Pareto sweep for figure 5 ---
    print("[A_e sweep] for figure 5:")
    sweep = []
    for A_e_frac in [0.0, 0.05, 0.10, 0.20]:
        A_e = A_e_frac * pp.PSI_DOT_MAX
        if A_e_frac == 0.0:
            out = out_CBF
            print(f"     A_e/psi_dot_max = {A_e_frac:.2f}: re-using AC+CBF run")
        elif np.isclose(A_e_frac, 0.10):
            out = out_PE
            print(f"     A_e/psi_dot_max = {A_e_frac:.2f}: re-using AC+CBF+PE run")
        else:
            print(f"     A_e/psi_dot_max = {A_e_frac:.2f}: running...")
            out = crossswap_run(A_e, T_cross, log_cross, use_safety_filter=True)
            print(_summary(f"A_e={A_e_frac:.2f}", out))
        sweep.append((A_e, out))

    # --- Communication-delay sweep for figure 6 ---
    print("[comm-delay sweep] for figure 6:")
    delay_runs = []
    for tau_ms in [0, 5, 20, 50, 100]:
        if tau_ms == 0:
            out = out_PE
            print(f"     tau = {tau_ms} ms: re-using AC+CBF+PE run")
        else:
            print(f"     tau = {tau_ms} ms: running...")
            out = crossswap_run(0.10 * pp.PSI_DOT_MAX, T_cross, log_cross,
                                 use_safety_filter=True, comm_delay=tau_ms * 1e-3)
            print(_summary(f"tau={tau_ms}ms", out))
        delay_runs.append((tau_ms, out))

    # --- N=2 head-on Filippov demo for figure 7 (v17 NEW) ---
    print("[1/2] N=2 head-on, no PE (Filippov sliding-mode demo)")
    out_headon_no_pe = headon_run(0.0, T_headon, log_headon)
    print(_summary("head-on no-PE", out_headon_no_pe))
    print("[2/2] N=2 head-on, with PE (locus broken by injection)")
    out_headon_with_pe = headon_run(0.10 * pp.PSI_DOT_MAX, T_headon, log_headon)
    print(_summary("head-on with-PE", out_headon_with_pe))

    print()
    print("Generating figures...")
    plots.figure_1_trajectories(out_AC, out_CBF, out_PE,
                                 OUT / "figure_1_trajectories.pdf")
    plots.figure_2_param_convergence(out_AC, out_CBF, out_PE,
                                      OUT / "figure_2_param_convergence.pdf")
    plots.figure_3_identifiability(out_PE, OUT / "figure_3_identifiability.pdf")
    plots.figure_4_safety(out_PE, OUT / "figure_4_safety.pdf")
    plots.figure_5_ae_sweep(sweep, OUT / "figure_5_ae_sweep.pdf")
    plots.figure_6_comm_delay(delay_runs, OUT / "figure_6_comm_delay.pdf")
    plots.figure_7_headon_filippov(out_headon_no_pe, out_headon_with_pe,
                                    OUT / "figure_7_headon_filippov.pdf")

    print()
    print(f"All 7 v17 figures written to {OUT}/")
    print(f"Total wall time: {time.time() - t0:.1f} s")


if __name__ == "__main__":
    main(quick=("--quick" in sys.argv))
