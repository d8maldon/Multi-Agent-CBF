"""Single source of truth for the v17 paper parameters [§8.3 — Dubins].

Every numerical value is copied verbatim from the v17 paper (complex-Dubins
multi-agent LOE-adaptive CBF). Per the council protocol, do not change
values without updating the paper first AND adding a council-log entry.
"""

from __future__ import annotations

import numpy as np


# ---------------------------------------------------------------------------
# §8.3 v17 Dubins simulation parameters (paper, verbatim)
# ---------------------------------------------------------------------------

# Reference-feedback / adaptive gains
K_T = 4.0           # tracking gain                                   [§8.3]
K_F = 0.3           # formation-coupling gain                         [§8.3]
GAMMA = 0.15        # adaptive-law gain (rate of theta_hat update)    [§8.3]

# HOCBF class-K gains [§3.1: ddot h + (alpha_1 + alpha_2) dot h + alpha_1 alpha_2 h >= 0]
ALPHA_1 = 5.0       # first class-K gain (psi_1 = dot h + alpha_1 h)  [§3.1]
ALPHA_2 = 5.0       # second class-K gain                              [§3.1]

# Dubins-vehicle constants
V_0 = 1.0           # constant cruise speed (constant-speed simplif.)  [§2.1]
PSI_DOT_MAX = 5.0   # maximum turn rate |u_2| <= psi_dot_max [rad/s]   [§3.1]

# Safety
R_SAFE = 0.4        # pair-safe distance                              [§8.3]

# True unknown LOE on turn-rate channel: lambda_i in [lambda_min, 1]
# Chosen so that 1/lambda_i in [theta_min, theta_max] = [1, 2] for every agent.
LAMBDA_TRUE = np.array([0.6, 0.9, 0.7, 0.8])    # 1/L = (1.667, 1.111, 1.429, 1.25)

# Projection bounds [§8.3 axiom A1]: hat_theta in [theta_min, theta_max]
THETA_MIN = 1.0
THETA_MAX = 2.0
KAPPA_LAMBDA = THETA_MAX / THETA_MIN  # = 2

# (A3') initial-safety margin: zeta = 0.5 r_safe^2
ZETA = 0.5 * R_SAFE ** 2

# QP slack penalty  [§3.2: M = 10^4]
SLACK_PENALTY = 1e4

# Hysteresis threshold  [§3.1: eps in [delta_ij + tol, 0.1 r_safe^2]]
EPS_HYST = 0.05 * R_SAFE ** 2

# PE excitation [§8.3 v17]: per-agent staggered turn-rate excitation
PE_F0 = 0.7              # base frequency [Hz]
PE_DELTA_F = 0.2         # per-agent stagger [Hz]
PE_SEED = 42

def pe_omegas(N: int) -> np.ndarray:
    """Per-agent (omega_i^1, omega_i^2) frequencies in rad/s. Returns (N, 2).

    The v17 PE injection is now a SCALAR (turn-rate channel only). We keep two
    frequencies per agent so that e_pe(t) = A_e [sin(w1 t + phi1) + sin(w2 t + phi2)]
    is a richer scalar signal than a single sinusoid.
    """
    return 2.0 * np.pi * np.array([
        [PE_F0 + i * PE_DELTA_F + 0.0,
         PE_F0 + i * PE_DELTA_F + PE_DELTA_F / 2]
        for i in range(N)
    ])

# A_e sweep [§8.4 fig 5]
A_E_SWEEP = np.array([0.0, 0.05, 0.10, 0.20]) * PSI_DOT_MAX

# Numerical scheme [§3.3]
H_OUTER = 5e-3          # 5 ms outer step
QP_TOL = 1e-7           # OSQP tolerance


# ---------------------------------------------------------------------------
# §8.2 v17 cross-swap geometry (Dubins waypoints)
# ---------------------------------------------------------------------------

# 4 agents at corners (±3, ±3); diagonal swap.
# Initial positions in complex form:
CROSSSWAP_R0 = np.array([
    -3.0 - 3.0j,
     3.0 - 3.0j,
     3.0 + 3.0j,
    -3.0 + 3.0j,
], dtype=complex)

# Initial headings: pointed at the diagonal target
CROSSSWAP_DIAGONAL = np.array([
     3.0 + 3.0j,
    -3.0 + 3.0j,
    -3.0 - 3.0j,
     3.0 - 3.0j,
], dtype=complex)

# Initial v_a: speed V_0 directed toward target
def crossswap_v0() -> np.ndarray:
    """Initial v_{a,i}(0) = V_0 * exp(i psi_i(0)), pointed toward diagonal target."""
    direction = (CROSSSWAP_DIAGONAL - CROSSSWAP_R0)
    direction = direction / np.abs(direction)
    return V_0 * direction

# Communication graph: complete K4
CROSSSWAP_EDGES = ((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3))

# Sustained cross-swap: targets oscillate sinusoidally between starting and
# diagonal corners with period T_swap.
T_SWAP = 8.0    # [s] full swap-and-back period for Dubins (slower than v16)

def crossswap_targets_oscillating(t: float) -> np.ndarray:
    """[§8.2 v17]: oscillating cross-swap targets in complex form. Returns (N,) complex."""
    s = 0.5 * (1.0 - np.cos(2.0 * np.pi * t / T_SWAP))   # in [0, 1]
    return CROSSSWAP_R0 + s * (CROSSSWAP_DIAGONAL - CROSSSWAP_R0)


# ---------------------------------------------------------------------------
# Sanity checks
# ---------------------------------------------------------------------------

def verify_paper_consistency() -> dict:
    checks = {}

    # 1/lambda in projection bounds
    inv = 1.0 / LAMBDA_TRUE
    in_range = (inv >= THETA_MIN) & (inv <= THETA_MAX)
    checks["1/lambda in [theta_min, theta_max]"] = (
        bool(np.all(in_range)),
        f"1/lambda = {inv}; in [{THETA_MIN}, {THETA_MAX}]: {in_range}",
    )

    # eta-feasibility (carries over from v16; same Lambda spread → same K_T·Λ_min margin)
    Lambda_min = float(LAMBDA_TRUE.min())
    val = K_T * Lambda_min
    checks["K_T*Lambda_min == 2.4"] = (
        np.isclose(val, 2.4, atol=0.01),
        f"K_T*Lambda_min = {val:.4f}",
    )

    # eps_hyst window
    upper = 0.1 * R_SAFE ** 2
    checks["eps_hyst <= 0.1 r_safe^2"] = (
        EPS_HYST <= upper,
        f"eps_hyst = {EPS_HYST:.4f}, upper = {upper:.4f}",
    )

    # HOCBF gains positive
    checks["alpha_1, alpha_2 > 0"] = (
        ALPHA_1 > 0 and ALPHA_2 > 0,
        f"alpha_1 = {ALPHA_1}, alpha_2 = {ALPHA_2}",
    )

    # Initial speed match
    v0 = crossswap_v0()
    speeds = np.abs(v0)
    checks["|v_a(0)| == V_0"] = (
        np.allclose(speeds, V_0),
        f"|v_a(0)| = {speeds}, V_0 = {V_0}",
    )

    return checks


if __name__ == "__main__":
    print("v17 paper parameter consistency checks:")
    for name, (ok, detail) in verify_paper_consistency().items():
        flag = "OK" if ok else "FAIL"
        print(f"  [{flag}] {name}: {detail}")
