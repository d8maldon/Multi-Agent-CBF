"""Single source of truth for the v14 paper parameters [§8.3].

Every numerical value here is copied verbatim from
notes/pe-aware-cbf-theorem.md §8.3. Do not change values without updating
the paper first AND adding a council-log entry.
"""

from __future__ import annotations

import numpy as np


# ---------------------------------------------------------------------------
# §8.3 Simulation parameter values (paper, verbatim)
# ---------------------------------------------------------------------------

# Reference-feedback / adaptive gains [§8.3 line: $K_T = 4, ..., \alpha = 10$]
K_T = 4.0           # tracking gain                            [§8.3]
K_F = 0.3           # formation-coupling gain                  [§8.3]
GAMMA = 0.15        # adaptive-law gain                        [§8.3]
ALPHA = 10.0        # ZCBF class-K gain                        [§8.3]

# Safety / actuator [§8.3 line: $r_{safe} = 0.4, u_{max} = 25$]
R_SAFE = 0.4        # pair-safe distance                       [§8.3]
U_MAX = 25.0        # per-channel saturation                   [§8.3]

# True unknown control effectiveness [§8.3 (v15): $\Lambda = (0.6, 0.9, 0.7, 0.8)$]
# Chosen so that 1/Lambda_i ∈ [theta_min, theta_max] = [1, 2] for every agent.
# (v14 used (0.6, 1.4, 0.9, 1.6); agents 2 + 4 had 1/Lambda outside the bounds —
#  Pass 13 finding 1 in notes/council-log.md. Fixed in v15.)
LAMBDA_TRUE = np.array([0.6, 0.9, 0.7, 0.8])    # ground truth, hidden from controller

# Projection bounds [§8.3: $\theta_{min} = 1, \theta_{max} = 2$]
THETA_MIN = 1.0
THETA_MAX = 2.0
KAPPA_LAMBDA = THETA_MAX / THETA_MIN  # = 2                    [§8.3 axiom A1]

# (A3') initial-safety margin [§8.3 line: $\zeta = 0.5\, r_{safe}^2$]
ZETA = 0.5 * R_SAFE ** 2

# QP slack penalty [§8.3 line: $M = 10^4$]
SLACK_PENALTY = 1e4

# Hysteresis threshold [§8.3 line: $\varepsilon = 0.05\, r_{safe}^2$]
EPS_HYST = 0.05 * R_SAFE ** 2

# PE excitation [§8.3 line: $\omega_1 = 2\pi(0.7), \omega_2 = 2\pi(1.1)$,
#                            $\phi_i^k \sim U[0, 2\pi)$ under seed rng(42)]
OMEGA_1 = 2.0 * np.pi * 0.7        # [Hz]
OMEGA_2 = 2.0 * np.pi * 1.1        # [Hz]
PE_SEED = 42

# A_e sweep values [§8.4 figure 5: $A_e \in \{0, 0.05, 0.10, 0.20\}\,u_{max}$]
A_E_SWEEP = np.array([0.0, 0.05, 0.10, 0.20]) * U_MAX

# Numerical scheme [§3.3 + §8.3 timing]
H_OUTER = 5e-3          # 5 ms outer step                       [§3.3]
QP_TOL = 1e-7           # OSQP solve tolerance                   [§3.3]


# ---------------------------------------------------------------------------
# §8.2 cross-swap geometry (paper, verbatim)
# ---------------------------------------------------------------------------

# 4 agents at corners (±3, ±3) [§8.2 line: "Agents at $(\pm 3, \pm 3)$"]
CROSSSWAP_X0 = np.array([
    [-3.0, -3.0],
    [ 3.0,  3.0],   # paper §8.2: "agent 1 going (-3,-3)→(3,3)" indexes from 1;
    [ 3.0, -3.0],   # we use 0-based; agent 0 ↔ paper agent 1; targets are
    [-3.0,  3.0],   # the diagonal-opposite corners.
])

# Targets: each agent swaps to the diagonally-opposite corner [§8.2]
CROSSSWAP_TARGETS = np.array([
    [ 3.0,  3.0],
    [-3.0, -3.0],
    [-3.0,  3.0],
    [ 3.0, -3.0],
])

# Communication graph: complete K4 (every pair) [§8.2: "Three pairs per agent"]
CROSSSWAP_EDGES = ((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3))


# ---------------------------------------------------------------------------
# Predicted §8.2 number (for verification)
# ---------------------------------------------------------------------------

def predicted_rho_bar_over_beta(mu_bar: float) -> float:
    """[§8.2 stratum-direct sum, eq. line 304]:
        tr(Q_1) = (1 - 2 mu_bar / 3) * beta_1
    """
    return 1.0 - 2.0 * mu_bar / 3.0


# ---------------------------------------------------------------------------
# Sanity checks at import (verifiable cross-references to the paper)
# ---------------------------------------------------------------------------

def verify_paper_consistency():
    """Run sanity checks against §8.3's stated relationships.

    Returns a dict {check_name: (ok, detail)} so the simulation can report
    paper inconsistencies as council-loggable findings rather than silently
    applying workarounds.
    """
    checks = {}

    # §8.3: $K_T \Lambda_{\min} = 2.4 > \bar\mu^2 L_{QP}^{*2} \approx 1.27$
    Lambda_min = float(LAMBDA_TRUE.min())
    val = K_T * Lambda_min
    checks["K_T*Lambda_min == 2.4"] = (
        np.isclose(val, 2.4, atol=0.01),
        f"K_T*Lambda_min = {val:.4f} (paper says 2.4)",
    )

    # axiom A1 / projection range covers all 1/Lambda_i
    inv_Lambda = 1.0 / LAMBDA_TRUE
    in_range = (inv_Lambda >= THETA_MIN) & (inv_Lambda <= THETA_MAX)
    checks["1/Lambda in [theta_min, theta_max]"] = (
        bool(np.all(in_range)),
        f"1/Lambda = {inv_Lambda}; in [{THETA_MIN}, {THETA_MAX}]: {in_range}",
    )

    # Hysteresis threshold within the §3.1 prescribed window
    # paper §3.1 line 92: $\varepsilon \in [\delta_{ij}(t)+\text{tol}, 0.1\,r_{safe}^2]$
    upper = 0.1 * R_SAFE ** 2
    checks["eps_hyst <= 0.1 r_safe^2"] = (
        EPS_HYST <= upper,
        f"eps_hyst = {EPS_HYST}, upper = {upper}",
    )

    return checks


if __name__ == "__main__":
    # Print verification results.
    print("Paper parameter consistency checks:")
    for name, (ok, detail) in verify_paper_consistency().items():
        flag = "OK" if ok else "FAIL"
        print(f"  [{flag}] {name}: {detail}")
