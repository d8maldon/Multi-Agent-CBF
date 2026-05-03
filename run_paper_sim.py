"""Run the sec8.2 cross-swap with EXACT paper-v14 parameters.

No tuning. No workarounds. If the sim diverges or hits projection bounds,
that is a council finding to log against the paper, not a sim bug to patch.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

from sim import paper_params as pp
from sim import integrator


HERE = Path(__file__).resolve().parent
OUT = HERE / "output" / "v14"
OUT.mkdir(parents=True, exist_ok=True)


def run_crossswap(T_final: float = 4.0, A_e: float = 0.10 * pp.U_MAX,
                  log_every: int = 4) -> dict:
    """Section sec8.2 scenario, exact paper parameters."""
    print("=" * 70)
    print("sec8.2 cross-swap, exact v14 paper parameters")
    print("=" * 70)
    print(f"  Lambda_true        = {pp.LAMBDA_TRUE}    [sec8.3]")
    print(f"  K_T, K_F, gamma    = {pp.K_T}, {pp.K_F}, {pp.GAMMA}    [sec8.3]")
    print(f"  alpha, r_safe      = {pp.ALPHA}, {pp.R_SAFE}             [sec8.3]")
    print(f"  u_max              = {pp.U_MAX}                          [sec8.3]")
    print(f"  theta_min, theta_max = {pp.THETA_MIN}, {pp.THETA_MAX}    [sec8.3]")
    print(f"  M (slack penalty)  = {pp.SLACK_PENALTY:g}                [sec8.3]")
    print(f"  eps_hyst           = {pp.EPS_HYST:g}                     [sec8.3]")
    print(f"  A_e (this run)     = {A_e:g}             [sec8.4 figure 5: A_e in {{0, .05, .10, .20}} u_max]")
    print(f"  T_final, h_outer   = {T_final}s, {pp.H_OUTER*1000:.1f}ms")
    print()

    print("Paper consistency checks:")
    for name, (ok, detail) in pp.verify_paper_consistency().items():
        print(f"  [{'OK' if ok else 'FAIL'}] {name}: {detail}")
    print()

    # Run with sec8.2 v16 OSCILLATING-target geometry (PE-preserving)
    out = integrator.run(
        x0=pp.CROSSSWAP_X0,
        z0=pp.CROSSSWAP_X0.copy(),
        edges=pp.CROSSSWAP_EDGES,
        t_targets_fn=pp.crossswap_targets_oscillating,
        A_e=A_e,
        T_final=T_final,
        log_every=log_every,
    )

    # Report per-agent PE frequencies for traceability
    omegas = pp.pe_omegas(pp.LAMBDA_TRUE.shape[0])
    print("Per-agent PE frequencies (sec8.3 v16):")
    for i, w in enumerate(omegas):
        print(f"  agent {i}: ({w[0]/(2*np.pi):.2f}, {w[1]/(2*np.pi):.2f}) Hz")
    print()

    print(f"Wall time:  {out['wall_time_s']:.2f} s for {out['n_steps']} steps "
          f"({out['wall_time_s']/out['n_steps']*1000:.1f} ms/step)")
    print()

    # Parameter convergence
    inv_L = 1.0 / pp.LAMBDA_TRUE
    print("Parameter convergence:")
    print(f"  theta_hat final = {out['theta_hat'][-1]}")
    print(f"  1/Lambda true   = {inv_L}")
    print(f"  abs error       = {np.abs(out['theta_hat'][-1] - inv_L)}")
    print(f"  in [theta_min, theta_max]: {(inv_L >= pp.THETA_MIN) & (inv_L <= pp.THETA_MAX)}")
    print()

    # Identifiability gain rho_bar_i = tr(Q_i)
    print("Identifiability gain (paper sec5: rho_bar_i = tr(Q_i)):")
    beta_1_i = np.array([
        np.mean(np.sum(out['u_ref'][:, i, :] ** 2, axis=1)) for i in range(out['u_ref'].shape[1])
    ])
    for i in range(len(out['rho_bar_i'])):
        ratio = out['rho_bar_i'][i] / max(beta_1_i[i], 1e-12)
        print(f"  agent {i}: tr(Q_{i}) = {out['rho_bar_i'][i]:.4f}, "
              f"beta_{i} = {beta_1_i[i]:.4f}, ratio = {ratio:.4f}")
    print()

    # Active-set duty cycle vs sec8.2 prediction
    mu_bar_global = out['active_count'].mean() / len(pp.CROSSSWAP_EDGES)
    print(f"Active-set fraction:")
    print(f"  mu_bar (global mean across pairs) = {mu_bar_global:.4f}")
    print(f"  sec8.2 reference value: mu_bar = 0.30")
    print(f"  sec8.2 predicted ratio at this mu_bar: "
          f"(1 - 2*mu_bar/3) = {pp.predicted_rho_bar_over_beta(mu_bar_global):.4f}")
    print()

    # Safety
    h_min = float(out['h'].min())
    print(f"Safety: min h_ij over time = {h_min:.4f}    "
          f"(>0 means safe; >= zeta = {pp.ZETA:.4f} means margin)")
    print(f"  any safety violation: {h_min < 0}")
    print()

    return out


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "long":
        out = run_crossswap(T_final=8.0, log_every=8)
    else:
        out = run_crossswap(T_final=4.0, log_every=4)
