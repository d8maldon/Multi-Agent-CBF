"""Generate v17.2 paper §8.4 figures 1-7 (council-vetted Passes 19-37).

v17.2 differences from v17.1:
- Figures 1, 2, 3, 4, 5, 6 now driven from the §8.2 N=8 antipodal-ring rosette
  demo (Klein 1872 Erlangen / Sepulchre-Paley-Leonard 2007 / Mesbahi-Egerstedt
  2010), replacing the v17.1 N=4 cross-swap as the empirical showcase. The
  rosette has D_8 ⋉ U(1)^8 symmetry, K_8 communication graph (28 HOCBF pairs),
  and Kirchhoff Laplacian L(K_8) with algebraic connectivity λ_2 = 8.
- For the N=8 demo only, H_OUTER 5 → 10 ms and SLACK_PENALTY 1e4 → 5e4
  (Pass 36/37 controls consensus). Worked example §VII (N=2 head-on) keeps
  baseline params, so figure 7 is unchanged.
- Figure 7 still §8.1 N=2 head-on Filippov demo at H_OUTER = 5 ms.

Runs:
  - 3 ring8 scenarios for figs 1, 2 (AC alone, AC+CBF, AC+CBF+PE)
  - 4 A_e values for fig 5
  - 5 comm-delay values for fig 6
  - 2 N=2 head-on scenarios for fig 7 (baseline H_OUTER)

Outputs to: output/v17/figure_{1..7}.pdf
"""

from __future__ import annotations

import contextlib
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


@contextlib.contextmanager
def numerical_overrides(H_OUTER: float, SLACK_PENALTY: float):
    """Temporarily override pp.H_OUTER and pp.SLACK_PENALTY for the N=8 demo.

    Pass 37 controls-expert-reviewer consensus: H_OUTER 5 → 10 ms preserves the
    Tikhonov singular-perturbation cascade (epsilon = K_T·Λ_min·H_OUTER = 0.024
    ≪ 1, separation factor 42×). SLACK_PENALTY 1e4 → 5e4 follows the
    sqrt(N(N-1)/2) ≈ 5.3 exact-penalty threshold (Bertsekas 1999 §5.4).
    """
    saved_H, saved_M = pp.H_OUTER, pp.SLACK_PENALTY
    pp.H_OUTER = H_OUTER
    pp.SLACK_PENALTY = SLACK_PENALTY
    try:
        yield
    finally:
        pp.H_OUTER = saved_H
        pp.SLACK_PENALTY = saved_M


def ring8_run(A_e: float, T_final: float, log_every: int,
              use_safety_filter: bool = True,
              comm_delay: float = 0.0,
              slack_penalty: float | None = None) -> dict:
    """One §8.2 v17.2 N=8 antipodal-ring rosette run (council Pass 37 consensus).

    H_OUTER = 10 ms, SLACK_PENALTY = 5e4 by default; pass slack_penalty=1e5 for
    the M=10× fallback if empirical h_min < 0 (Pass 37 Ames gate).
    """
    r0 = pp.RING8_R0.copy()
    v_a0 = pp.ring8_v0()
    M = slack_penalty if slack_penalty is not None else pp.SLACK_PENALTY_RING8
    with numerical_overrides(pp.H_OUTER_RING8, M):
        return integrator.run(
            r0=r0, v_a0=v_a0,
            r_ref0=r0.copy(), v_ref0=v_a0.copy(),
            edges=pp.RING8_EDGES,
            t_targets_fn=pp.ring8_targets_oscillating,
            A_e=A_e,
            T_final=T_final,
            log_every=log_every,
            use_safety_filter=use_safety_filter,
            comm_delay=comm_delay,
        )


def crossswap_run(A_e: float, T_final: float, log_every: int,
                   use_safety_filter: bool = True,
                   comm_delay: float = 0.0) -> dict:
    """One §8.2 N=4 cross-swap run (kept for back-compat / unit tests; not used
    for v17.2 figures 1-6, which use ring8_run instead)."""
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
        T_cross, log_cross = 4.0, 4   # log finer at H_OUTER=10ms (was 8 at 5ms)
        T_headon, log_headon = 0.6, 4
    else:
        T_cross, log_cross = 16.0, 4
        T_headon, log_headon = 1.0, 4
    print(f"v17.2 ring8 rosette: T_final = {T_cross} s, log_every = {log_cross}")
    print(f"v17.2 head-on:       T_final = {T_headon} s, log_every = {log_headon}")
    print()

    t0 = time.time()

    # --- 3 ring8 rosette scenarios for figures 1 + 2 ---
    print("[1/3] AC alone  (no safety filter, no PE) — N=8 antipodal ring")
    out_AC = ring8_run(0.0, T_cross, log_cross, use_safety_filter=False)
    print(_summary("AC", out_AC))

    print("[2/3] AC + CBF  (safety filter on, no PE) — N=8 antipodal ring")
    out_CBF = ring8_run(0.0, T_cross, log_cross, use_safety_filter=True)
    print(_summary("AC+CBF", out_CBF))

    print("[3/3] AC + CBF + PE  (paper headline scenario, A_e = 0.10*psi_dot_max)")
    out_PE = ring8_run(0.10 * pp.PSI_DOT_MAX, T_cross, log_cross,
                       use_safety_filter=True)
    print(_summary("AC+CBF+PE", out_PE))

    # Pass 37 Ames empirical h_min gate: if h_min < 0, re-run at M=1e5
    if out_PE['h'].min() < 0.0:
        print(f"  ⚠ h_min = {out_PE['h'].min():.3f} < 0 — re-running at M=1e5 fallback")
        out_PE = ring8_run(0.10 * pp.PSI_DOT_MAX, T_cross, log_cross,
                           use_safety_filter=True, slack_penalty=pp.SLACK_PENALTY_RING8_FALLBACK)
        print(_summary("AC+CBF+PE [M=1e5]", out_PE))

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
            out = ring8_run(A_e, T_cross, log_cross, use_safety_filter=True)
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
            out = ring8_run(0.10 * pp.PSI_DOT_MAX, T_cross, log_cross,
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
