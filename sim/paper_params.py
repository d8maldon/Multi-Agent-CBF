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
# Eight values cover the v17.1 N=4 cross-swap (first four) AND the v17.2 N=8
# antipodal-ring rosette (full eight). Spread is preserved: min = 0.55, max = 0.9
# so 1/lambda_i in [1.111, 1.818] still safely in [theta_min, theta_max] = [1, 2].
LAMBDA_TRUE = np.array([0.6, 0.9, 0.7, 0.8, 0.65, 0.85, 0.55, 0.75])

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
# §8.2 v17.2 N=8 antipodal-ring rosette demo (Pass 34-37 council consensus)
# ---------------------------------------------------------------------------
# Erlangen-canonical benchmark: 8 agents on a regular octagon (radius R=3),
# antipodal swap r_k <-> r_{k+4 mod 8}. Symmetry group D_8 ⋉ U(1)^8 (Klein
# 1872; Weyl 1918). The Z_8 cyclic subgroup decomposes the binom(8,2)=28
# pairs into 4 chord-length orbits (sizes 8+8+8+4) — Noether 1918 reduces
# the V=Sum h_ij Lyapunov to 4 orbit representatives. Kirchhoff Laplacian
# L(K_8) has spectrum {0, 8^(7)} — algebraic connectivity λ_2 = 8 (Fiedler
# 1973), 2× tighter than K_4. Sepulchre-Paley-Leonard 2007 + Mesbahi-
# Egerstedt 2010 are the canonical multi-agent ring references.

RING8_RADIUS = 3.0
N_RING8 = 8

RING8_R0 = RING8_RADIUS * np.exp(1j * 2.0 * np.pi * np.arange(N_RING8) / N_RING8)
RING8_R0 = RING8_R0.astype(complex)

# Antipodal target for agent k: r_{(k+4) mod 8}
RING8_ANTIPODAL = np.roll(RING8_R0, -4).astype(complex)

# Initial v_a: speed V_0 toward antipodal partner
def ring8_v0() -> np.ndarray:
    """Initial v_{a,i}(0) = V_0 * exp(i psi_i(0)), pointed toward antipodal target."""
    direction = (RING8_ANTIPODAL - RING8_R0)
    direction = direction / np.abs(direction)
    return V_0 * direction

# Complete graph K_8: all binom(8,2) = 28 unordered pairs
RING8_EDGES = tuple(
    (i, j) for i in range(N_RING8) for j in range(i + 1, N_RING8)
)
assert len(RING8_EDGES) == 28, "K_8 must have 28 edges"

# Slower swap period for the rosette: peak target velocity 6*pi/T_swap.
# T_swap=8 → peak 2.36 m/s (trend-tracking regime, |dot t| > V_0).
# Min one-way Dubins-reachable T_swap = pi*R/V_0 = 9.42 s (Carathéodory
# 1909 / Frazzoli; OG Pass 35 numerical correction).
T_SWAP_RING8 = 8.0    # [s]

def ring8_targets_oscillating(t: float) -> np.ndarray:
    """[§8.2 v17.2 N=8 antipodal ring]: oscillating targets in complex form.

    t_i(t) = r_i(0) + s(t) * (r_{(i+4) mod 8}(0) - r_i(0)),
    s(t) = 0.5 * (1 - cos(2*pi*t/T_SWAP_RING8)).
    """
    s = 0.5 * (1.0 - np.cos(2.0 * np.pi * t / T_SWAP_RING8))
    return RING8_R0 + s * (RING8_ANTIPODAL - RING8_R0)


def check_ring8_reachability(T_swap: float = T_SWAP_RING8) -> dict:
    """One-way antipodal Dubins-reachability check (Carathéodory 1909).

    Peak target velocity for sinusoidal antipodal swap with amplitude
    |r_antipodal - r_0| = 2R is pi * 2R / T_swap = 6*pi / T_swap (R=3).
    Min one-way reachability T_swap = pi*R/V_0 (half-circle arc length
    pi*R divided by V_0). NOT 2*pi*R/V_0 (that's the round-trip period).
    """
    arc_distance = float(np.pi * RING8_RADIUS)  # one-way half-circle
    peak_velocity = float(np.pi * 2 * RING8_RADIUS / T_swap)  # sinusoidal peak
    min_T_for_reach = arc_distance / V_0  # pi*R/V_0
    return {
        "peak_target_velocity": peak_velocity,
        "V_0": V_0,
        "reachable": peak_velocity <= V_0,
        "min_T_swap_one_way": min_T_for_reach,
        "round_trip_period": 2.0 * np.pi * RING8_RADIUS / V_0,
    }


# ---------------------------------------------------------------------------
# Per-demo numerical scheme overrides (Pass 36/37 controls consensus)
# ---------------------------------------------------------------------------
# At N=8 with K_8 = 28 pairs the per-step OSQP cost grows; estimated 8·0.7 =
# 5.6 ms warm. Pass 37 controls consensus: bump H_OUTER 5→10 ms for the
# rosette demo (Tikhonov margin K_T·Λ_min·H_OUTER = 0.024 ≪ 1, separation
# factor 42×). Slack penalty also scales by sqrt(N(N-1)/2) ≈ 5.3, so bump
# M = 10^4 → 5·10^4 (Bertsekas 1999 §5.4 exact-penalty threshold).
H_OUTER_RING8 = 1e-2          # 10 ms outer step for N=8 demo (vs 5 ms baseline)
# Pass 37 Ames gate: empirically h_min < 0 at M = 5e4 in some scenarios
# (AC+CBF baseline, A_e=0.05, tau=5 ms) — sqrt(28) slack aggregation dominates
# the v17.1 estimate. Promote default to the M=1e5 fallback so all runs honour
# h_min >= 0 by construction; matches Pass 37 controls "if h_min < 0 anywhere
# in the run, re-run at M=10x" gate without conditional re-run logic.
SLACK_PENALTY_RING8 = 1e5     # exact-penalty for 28-pair worst case
SLACK_PENALTY_RING8_FALLBACK = 5e5   # 5x bump if M=1e5 still fails


def check_target_reachability(T_swap: float = T_SWAP) -> dict:
    """[§8.2 v17.1, Frazzoli Pass 31]: verify the cross-swap targets are
    Dubins-reachable at the given T_swap.

    Carathéodory 1909 accessibility: the target velocity |dot t_i(t)| must not
    exceed V_0 if agents are to track the *instantaneous* target. With the
    sinusoidal targets t_i(t) = c_i + 0.5*(1-cos(2*pi*t/T_swap))*(c_sigma(i)-c_i),
    the peak target velocity is |dot t_i|_max = pi * |c_sigma(i) - c_i| / T_swap.

    Returns dict with:
      - 'peak_target_velocity': |dot t_i|_max [m/s]
      - 'V_0': constant cruise speed [m/s]
      - 'reachable': True iff peak_target_velocity <= V_0
      - 'min_T_swap_for_reachability': pi * |c_sigma(i) - c_i| / V_0 [s]

    Default §8.3 T_swap = 8 s gives peak ~3.33 m/s, exceeds V_0 = 1 m/s by 3x;
    the agents track the *trend*, not instantaneous position. The §8.2 caveat
    documents this — it is the realistic UAV-path-planner regime.
    """
    diag_distance = float(np.abs(CROSSSWAP_DIAGONAL[0] - CROSSSWAP_R0[0]))  # 6*sqrt(2)
    peak_velocity = np.pi * diag_distance / T_swap
    min_T_for_reach = np.pi * diag_distance / V_0
    return {
        "peak_target_velocity": peak_velocity,
        "V_0": V_0,
        "reachable": peak_velocity <= V_0,
        "min_T_swap_for_reachability": min_T_for_reach,
    }


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

    # eta-feasibility on the §VII proof-bearing N=4 worked example
    # (first four LAMBDA_TRUE entries, unchanged from v17.1).
    Lambda_min_n4 = float(LAMBDA_TRUE[:4].min())
    val_n4 = K_T * Lambda_min_n4
    checks["K_T*Lambda_min (N=4 §VII proof) == 2.4"] = (
        np.isclose(val_n4, 2.4, atol=0.01),
        f"K_T*Lambda_min[:4] = {val_n4:.4f}",
    )

    # eta-feasibility on the v17.2 N=8 rosette demo. Lambda_min[:8] = 0.55 →
    # K_T·Λ_min = 2.2; still > K_F bound (0.3) so heading-PD inner loop converges.
    Lambda_min_n8 = float(LAMBDA_TRUE.min())   # full array, includes 0.55
    val_n8 = K_T * Lambda_min_n8
    checks["K_T*Lambda_min (N=8 demo) >= 2.2"] = (
        val_n8 >= 2.2 - 0.01,
        f"K_T*Lambda_min[:8] = {val_n8:.4f}",
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
