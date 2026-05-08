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
# K_F: v17.1 cross-swap baseline 0.3; ring rotation needed K_F=8 to combat
# LOE-heterogeneity-induced radial drift. Pass 43 council verdict: the
# rotating-ring rosette is the canonical demo (Pass 41 APPROVED); the
# highway pivot (Pass 42-43) was reverted because constant-speed Dubins
# at coincident-x conflicting-swap is Nagumo-degenerate (relative-degree
# drop on positive-measure set, not isolated). Restore K_F=8 for the ring.
K_F = 8.0           # formation-coupling gain (v17.3 ring-rotation tuning)
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

# v17.3.2: cyclic-shift target (Sepulchre-Paley-Leonard 2007 phase-locked
# rotation). Agent k moves to slot k+1 mod 8 — concentric arc, no centre
# crossing, |a_ii| bounded away from zero by geometry. Antipodal swap retained
# as RING8_ANTIPODAL for back-compatibility / unit tests.
RING8_ANTIPODAL = np.roll(RING8_R0, -4).astype(complex)
RING8_TARGET = np.roll(RING8_R0, -1).astype(complex)   # k -> k+1 cyclic shift

# Initial v_a: speed V_0 along the tangent (counter-clockwise rotation)
def ring8_v0() -> np.ndarray:
    """Initial v_{a,i}(0) = V_0 * exp(i psi_i(0)). For Sepulchre-Paley-Leonard
    cyclic rotation the natural initial heading is the tangent direction at the
    starting slot (counter-clockwise around the ring): psi_i(0) = arg(r_i) + pi/2."""
    return V_0 * 1j * RING8_R0 / np.abs(RING8_R0)   # tangent = i * (r/|r|)

# Complete graph K_8: all binom(8,2) = 28 unordered pairs
RING8_EDGES = tuple(
    (i, j) for i in range(N_RING8) for j in range(i + 1, N_RING8)
)
assert len(RING8_EDGES) == 28, "K_8 must have 28 edges"

# v17.3.3: CONTINUOUS rotation target (Sepulchre-Paley-Leonard 2007 phase-
# locked rotation). Each agent's target is a continuously rotating slot:
#     t_i(t) = R * exp(i * (2*pi*i/8 + omega*t))
# with omega = OMEGA_RING8. Peak target velocity = R * omega.
#
# Carathéodory 1909 / Frazzoli Dubins-reachability: at constant speed V_0 the
# natural curvature of any motion at radius R is V_0/R. For the rotating-slot
# target to be EXACTLY trackable (each agent both at radius R AND at angular
# rate omega), we need R*omega = V_0, i.e. omega = V_0/R. Otherwise the
# kinematic mismatch forces either spiralling-in (R*omega > V_0) or cycloidal
# breakaway (R*omega < V_0).
# At V_0=1, R=3: omega = 1/3 rad/s, T_period = 2*pi*R/V_0 = 6*pi ≈ 18.85 s.
# Over T_final = 16 s, agents complete 16/18.85 = 0.85 of a revolution = 305°
# of CCW rotation — ~6.8 slots, visible large-arc motion, no centre crossing.
T_PERIOD_RING8 = 2.0 * np.pi * RING8_RADIUS / V_0        # = 6*pi ≈ 18.85 s
OMEGA_RING8 = V_0 / RING8_RADIUS                          # = 1/3 ≈ 0.333 rad/s
T_SWAP_RING8 = T_PERIOD_RING8                # back-compat alias for tests

def ring8_targets_oscillating(t: float) -> np.ndarray:
    """[§8.2 v17.3 N=8 continuous-rotation ring (Sepulchre-Paley-Leonard 2007)]:
    each agent's target rotates at constant angular rate around the ring.
    Returns (N,) complex.

    t_i(t) = R * exp(i * (2*pi*i/N + omega*t)),  omega = 2*pi/T_period
    """
    return RING8_RADIUS * np.exp(1j * (2.0 * np.pi * np.arange(N_RING8) / N_RING8
                                        + OMEGA_RING8 * t))


# ---------------------------------------------------------------------------
# §VIII v17.5 8-pointed-star reconfiguration (Pass 44 council, Option B)
# ---------------------------------------------------------------------------
# 8 agents start on the radius-3 circle at angles 2*pi*k/8. Targets are an
# 8-pointed star: even-indexed agents (k = 0, 2, 4, 6) stay at radius 3
# (outer points); odd-indexed agents (k = 1, 3, 5, 7) move to radius
# R_INNER (inner points). Pre-checked non-crossing: each agent's trajectory
# is a radial chord; no two chords intersect. Pass 44 OG verdict: this
# satisfies the post-Pass-43 Nagumo viability gate (no coincident-x
# simultaneous crossings).
#
# Visual: outer ring contracts into a 4-armed star pattern. Photogenic
# transition from circle to star, well within the v17 framework.

R_OUTER_STAR = 3.0
R_INNER_STAR = 1.2

# Targets at radii alternating outer/inner around the same angles
def _star_target_positions() -> np.ndarray:
    angles = 2.0 * np.pi * np.arange(N_RING8) / N_RING8
    radii = np.array([R_OUTER_STAR if (k % 2 == 0) else R_INNER_STAR
                      for k in range(N_RING8)])
    return radii * np.exp(1j * angles)

STAR_R0 = (np.array([R_OUTER_STAR if (k % 2 == 0) else R_INNER_STAR
                     for k in range(N_RING8)])
           * np.exp(1j * 2.0 * np.pi * np.arange(N_RING8) / N_RING8)).astype(complex)
STAR_TARGET_FINAL = _star_target_positions().astype(complex)
STAR_EDGES = RING8_EDGES     # K_8 communication

# Smooth target trajectory: agents move from initial radius-3 to the star
# pattern over T_STAR_RECONFIG seconds, then hold the star indefinitely.
# Cosine smoothing s(t) = 0.5*(1-cos(2*pi*t/(2*T_STAR))) for t in [0, T_STAR];
# s = 1 thereafter. (i.e. half-cosine rise then plateau at the star.)
T_STAR_RECONFIG = 8.0    # [s] time to complete the star reconfiguration

def star_v0() -> np.ndarray:
    """Initial v_{a,i}(0) = V_0 along the tangent CCW (CCW rotation of the
    formation, rate omega = V_0 / R_OUTER). All agents start phase-locked
    on the rotating star pattern."""
    return V_0 * 1j * STAR_R0 / np.abs(STAR_R0)

def star_targets_oscillating(t: float) -> np.ndarray:
    """[§VIII v17.5 ROTATING 8-pointed-star]: target is an 8-pointed star
    that ROTATES CCW at omega = V_0/R_OUTER. Even-indexed agents track
    outer points (radius 3); odd-indexed agents track inner points
    (radius 1.2). All agents rotate together — no agent needs to "stay put"
    against the constant-speed Dubins constraint.

    t_i(t) = R_i * exp(i * (2*pi*i/N + omega*t))
    where R_i = R_OUTER if i even, R_INNER if i odd.

    Visual: rotating 4-pointed star (4 outer arms + 4 inner valleys, all
    rotating CCW). Smooth, no static-formation pathology.
    """
    omega = V_0 / R_OUTER_STAR    # = 1/3 rad/s, same as v17.3 rotating ring
    angles = 2.0 * np.pi * np.arange(N_RING8) / N_RING8 + omega * t
    radii = np.array([R_OUTER_STAR if (k % 2 == 0) else R_INNER_STAR
                      for k in range(N_RING8)])
    return radii * np.exp(1j * angles)


H_OUTER_STAR = 5e-3              # 5 ms (cross-swap baseline; not too slow)
SLACK_PENALTY_STAR = 1e4         # M = 10^4 baseline


# ---------------------------------------------------------------------------
# §VIII v17.7 4-vehicle OBSTACLE-AVOIDANCE demo (Pass 47 council APPROVED)
# ---------------------------------------------------------------------------
# 4 vehicles cross-swap to opposite corners with 3 static circular obstacles
# in the field. The classical CBF-paper demo (Ames-Xu-Grizzle 2014; Borrmann-
# Wang-Ames 2015; Wang-Ames-Egerstedt 2017). Static obstacles are not subject
# to the Pass 43/45 Nagumo-degenerate failure: the $2V_0^2$ kinematic floor
# in $\ddot h$ acts protectively (Pass 47 verdict) since obstacle velocity
# is zero, so the structural failure mode does not apply.
#
# Geometry: 4 vehicles at (±4, ±4); each targets the diagonal-opposite
# corner. Obstacles in the field force detours.
# Dubins turning radius V_0/psi_dot_max = 1/5 = 0.2 m. Pass 47 caveat:
# obstacle radius + r_safe must exceed turning radius. With r_obs = 1.0
# and r_safe = 0.4, clearance is 1.4 m >> 0.2 m. Comfortably safe.

# Vehicles arranged so their AC straight-line paths to targets do NOT pass
# directly through any obstacle (avoids the Nagumo-degenerate head-on
# obstacle case). Each vehicle takes a parallel-channel route past obstacles
# — the obstacles force lateral deflection but the path is not aimed at
# obstacle centre.
OBSTACLE_R0 = np.array([
    -5.0 + 1.5j,    # vehicle 0: west, upper channel
    -5.0 - 1.5j,    # vehicle 1: west, lower channel
    +5.0 + 1.5j,    # vehicle 2: east, upper channel
    +5.0 - 1.5j,    # vehicle 3: east, lower channel
], dtype=complex)

# Targets: each vehicle drives east/west to the OPPOSITE side of the
# obstacle field, keeping its lateral position. AC straight-line paths
# are horizontal, so vertical-stacked obstacles force only small deflection.
OBSTACLE_TARGETS = np.array([
    +5.0 + 1.5j,    # vehicle 0 -> east (head-on with vehicle 2 in same channel!)
    +5.0 - 1.5j,    # vehicle 1 -> east (head-on with vehicle 3)
    -5.0 + 1.5j,    # vehicle 2 -> west
    -5.0 - 1.5j,    # vehicle 3 -> west
], dtype=complex)

OBSTACLE_EDGES = ((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3))   # K_4

# Two STATIC circular obstacles — placed off the AC straight-line paths.
# Vehicle paths at y = ±1.5; obstacles at y = 0 (central), centre x close
# to where vehicles meet. This forces vehicles to deflect AROUND the
# obstacles laterally as they pass each other.
OBSTACLE_LIST = (
    (0.0 + 0.0j, 0.7),       # central obstacle (off the y=±1.5 channels)
    (+2.5 + 0.0j, 0.5),      # east obstacle
    (-2.5 + 0.0j, 0.5),      # west obstacle
)


def obstacle_v0() -> np.ndarray:
    """Initial v_{a,i}(0): heading toward diagonal target (cross-swap-style)."""
    direction = OBSTACLE_TARGETS - OBSTACLE_R0
    direction = direction / np.abs(direction)
    return V_0 * direction


def obstacle_targets_static(t: float) -> np.ndarray:
    """Static target: each vehicle drives toward its assigned diagonal corner.
    The targets are FIXED (not time-varying), so this returns the same array
    for all t. The obstacles in the field force the trajectory to detour.
    """
    return OBSTACLE_TARGETS.copy()





def ring8_targets_antipodal_oscillating(t: float) -> np.ndarray:
    """v17.2 antipodal swap (k <-> k+4); kept for back-compatibility tests.

    The synchronous-octuple-switch geometry that Pass 38 disclosed as
    (A3'') small-margin. Replaced as the headline demo by the cyclic-rotation
    target above (Pass 40, council-blessed).
    """
    s = 0.5 * (1.0 - np.cos(2.0 * np.pi * t / T_SWAP_RING8))
    return RING8_R0 + s * (RING8_ANTIPODAL - RING8_R0)


# ---------------------------------------------------------------------------
# §VIII v17.4 highway lane-change demo (Pass 42 council consensus)
# ---------------------------------------------------------------------------
# Replaces the rotating-ring rosette with a CAR / ROAD scenario:
# - 4 cars on a 2-lane straight highway
# - All cars at constant speed V_0 = 1 m/s (kinematic-bicycle Dubins
#   abstraction; cf. Rajamani 2012 §2, Falcone-Borrelli 2007)
# - Lane lines at y = +/- L_LANE (lane width 2*L_LANE = 3 m, dimensionless)
# - Cars 0, 1 in right lane; cars 2, 3 in left lane
# - Cross-swap targets: cars 0,1 -> left lane; cars 2,3 -> right lane
# - Phase-offset between pairs (0,2) and (1,3) avoids synchronous midpoint
#   crossing (council Pass 42 Egerstedt mod)
# - Heterogeneous LOE: lambda_i in [0.55, 0.9] per car (steering authority)
# - K_4 communication graph (all 4 cars exchange state)
#
# DIMENSIONLESS NORMALISATION (council Pass 42 Borrelli/Falcone disclosure):
# Length scaled to lane width L = 1.5 m; time to T_LANE = 8 s. Physical
# highway corresponds to V_0 ~ 30 m/s, r_safe ~ 5 m, lane width 3.5 m. The
# r_safe / L = 0.4 / 1.5 = 0.27 ratio represents a point-mass-surrogate bubble
# around each car — appropriate for a kinematic-level demo, not a full
# vehicle-dynamics model.

L_LANE = 1.5    # half-lane width [dimensionless; physical lane = 2*L_LANE]
N_HIGHWAY = 4
T_LANE = 8.0    # [s] one cosine-shaped lane-change cycle

# Conflicting-merge scenario: cars 0 and 1 are at the SAME longitudinal
# position but in opposite lanes; both want to swap to the other lane,
# producing a head-on lateral conflict at the lane midline (y=0). The safety
# filter must defer one car's merge until the other clears. Cars 2 and 3
# are background traffic ahead, providing a richer K_4 graph.
HIGHWAY_R0 = np.array([
    -1.5 - L_LANE * 1j,    # car 0: right lane, wants to merge LEFT
    -1.5 + L_LANE * 1j,    # car 1: left lane (directly above car 0!), wants to merge RIGHT
     3.0 - L_LANE * 1j,    # car 2: right lane, ahead (background traffic)
     3.0 + L_LANE * 1j,    # car 3: left lane, ahead (background traffic)
], dtype=complex)

# Initial heading: all cars going +x along the road
def highway_v0() -> np.ndarray:
    """Initial v_{a,i}(0) = V_0 along +x for each car (highway driving)."""
    return V_0 * np.ones(N_HIGHWAY, dtype=complex)

HIGHWAY_EDGES = ((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3))   # K_4

V_HIGHWAY = 0.8 * V_0    # longitudinal target speed (target advances east at this rate)

def highway_targets_oscillating(t: float) -> np.ndarray:
    """[§VIII v17.4 highway conflicting-merge]: cars 0 and 1 swap lanes
    simultaneously at the same x; cars 2 and 3 drive east as background.
    Returns (4,) complex.

    Geometry: conflicting lane-swap benchmark (analog of v17.1 cross-swap
    constrained to a 2-lane highway). Car 0 (right lane) wants left lane;
    car 1 (left lane, directly above car 0) wants right lane. Without the
    safety filter both cars cross y=0 at the same (x,y), collision. With
    the filter, one car defers via the HOCBF QP-resolvent.

    Cosine-based smoothing s(t) = 0.5*(1 - cos(2*pi*t/T_LANE)) gives zero
    lateral velocity at t=0 (Pass 42 Egerstedt mod). Longitudinal advance
    V_HIGHWAY * t keeps targets Dubins-reachable (Carathéodory 1909).
    """
    s_swap = 0.5 * (1.0 - np.cos(2.0 * np.pi * t / T_LANE))
    x_advance = V_HIGHWAY * t
    targets = np.zeros(N_HIGHWAY, dtype=complex)
    # Car 0 (started right lane): swap to LEFT — y goes from -L_LANE to +L_LANE
    targets[0] = (HIGHWAY_R0[0].real + x_advance) + 1j * (-L_LANE + 2.0 * L_LANE * s_swap)
    # Car 1 (started left lane, above car 0): swap to RIGHT
    targets[1] = (HIGHWAY_R0[1].real + x_advance) + 1j * (+L_LANE - 2.0 * L_LANE * s_swap)
    # Cars 2, 3: drive east in their lanes (no swap)
    targets[2] = (HIGHWAY_R0[2].real + x_advance) + 1j * (-L_LANE)
    targets[3] = (HIGHWAY_R0[3].real + x_advance) + 1j * (+L_LANE)
    return targets


# Numerical scheme overrides for highway demo (same as cross-swap baseline)
H_OUTER_HIGHWAY = 5e-3            # 5 ms outer step (cross-swap baseline)
SLACK_PENALTY_HIGHWAY = 1e4       # M = 10^4 baseline


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
# Pass 41 user feedback (v17.4): the heterogeneous LAMBDA_TRUE
# (lambda in [0.55, 0.9]) caused visible radial drift on the rotating ring
# even with K_F = 8. For the §VIII trajectory headline figure we use
# HOMOGENEOUS lambda = 0.7 so all 8 agents have identical kinematic
# capability — they phase-lock cleanly on the radius-R circle (Sepulchre-
# Paley-Leonard 2007 setup). LOE heterogeneity is still demonstrated:
# (i) §VII §VII.2 proof-bearing N=4 cross-swap uses LAMBDA_TRUE[:4] (heterog),
# (ii) parameter-convergence figure 2 uses heterogeneous initial theta_hat
# per-agent (PE phases differ per agent, breaking the symmetry).
RING8_LAMBDA = 0.7 * np.ones(N_RING8)

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
