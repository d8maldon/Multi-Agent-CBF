"""OSQP warm-start timing benchmark for v17 scalar QP (Pass 21 + 27 deferred item).

Paper §3.3 claims: "OSQP solves in ~0.05 ms warm-started on a desktop CPU".
This benchmark verifies that claim empirically on the v17 scalar-u_2 QP.

Benchmark methodology:
- Set up the §8.2 cross-swap initial state.
- Build the QP for one agent at a representative configuration (mid-traversal).
- Cold-start: time the first solve (includes OSQP setup + factorisation).
- Warm-start: re-solve with slightly perturbed parameters; time only the
  prob.update() + prob.solve() path.
- Average over many warm-start calls to get a stable estimate.

Per Pass 27 Wise: the timing must be < 0.5 ms warm-started for real-time at
h_outer = 5 ms with N = 4 agents (16 OSQP calls per outer step).
"""

from __future__ import annotations

import time

import numpy as np
import pytest

from sim import paper_params as pp
from sim import dynamics as dyn
from sim import qp_resolvent as qpr


@pytest.mark.slow
def test_v17_osqp_warm_start_timing():
    """Benchmark v17 scalar QP cold-start vs warm-start timing.

    Reports timing to stdout (run with `pytest -s` to see it).
    Asserts warm-start < 1 ms (loose; tightening to 0.5 ms is the Pass 27 target,
    but allowing 2x headroom for slow CI machines).
    """
    # §8.2 cross-swap config at mid-traversal
    r = np.array([
        -1.5 - 1.5j,
        1.5 - 1.5j,
        1.5 + 1.5j,
        -1.5 + 1.5j,
    ], dtype=complex)
    psi0 = [np.pi / 4, 3 * np.pi / 4, -3 * np.pi / 4, -np.pi / 4]
    v_a = pp.V_0 * np.array([np.exp(1j * p) for p in psi0])
    theta_hat = np.array([1.5, 1.5, 1.5, 1.5])
    u_2_AC = np.array([0.5, -0.5, 0.5, -0.5])
    edges = pp.CROSSSWAP_EDGES
    pair_active = {frozenset({i, j}): False for (i, j) in edges}
    delta_ij = {frozenset({i, j}): 0.01 for (i, j) in edges}
    solver_cache: dict = {}

    # Cold-start: first OSQP solve (includes setup + factorisation)
    t_cold_start = time.perf_counter()
    u_safe, _, status_cold = qpr.solve_qp(0, r, v_a, theta_hat, u_2_AC, 0.0,
                                            pair_active, edges, delta_ij,
                                            solver_cache)
    t_cold = time.perf_counter() - t_cold_start
    print(f"\n  Cold-start (first solve, agent 0): {t_cold * 1000:.3f} ms, "
          f"status = {status_cold}")
    assert status_cold == "solved", \
        f"cold-start solve failed: {status_cold}"

    # Warm 1000-call benchmark: same active-set, perturbed parameters
    n_warm = 1000
    rng = np.random.default_rng(42)
    t_warm_start = time.perf_counter()
    for _ in range(n_warm):
        # Small parameter perturbations to avoid trivial-cache cases
        u_2_AC_perturbed = u_2_AC + 0.01 * rng.standard_normal(4)
        u_safe, _, _ = qpr.solve_qp(0, r, v_a, theta_hat, u_2_AC_perturbed,
                                      0.0, pair_active, edges, delta_ij,
                                      solver_cache)
    t_warm_total = time.perf_counter() - t_warm_start
    t_warm_avg = t_warm_total / n_warm * 1000  # ms
    print(f"  Warm-start (avg of {n_warm} calls, agent 0): {t_warm_avg:.3f} ms/call")

    # Speedup factor
    speedup = t_cold * 1000 / t_warm_avg if t_warm_avg > 0 else float("inf")
    print(f"  Speedup: {speedup:.1f}x")

    # Assertion (loose; Pass 27 target is < 0.5 ms; CI may be slower)
    assert t_warm_avg < 1.0, \
        f"OSQP warm-start avg {t_warm_avg:.3f} ms exceeds 1 ms threshold"


@pytest.mark.slow
def test_v17_osqp_active_set_change_cold_starts():
    """When the active set changes (engagement / disengagement), the QP
    dimension changes and OSQP must cold-start. Benchmark this transition."""
    r = np.array([0.0 + 0.0j, 0.5 + 0.5j], dtype=complex)
    v_a = np.array([1.0 + 0.0j, 0.0 - 1.0j])
    theta_hat = np.array([1.5, 1.5])
    u_2_AC = np.array([0.0, 0.0])
    edges = ((0, 1),)
    delta_ij = {frozenset({0, 1}): 0.01}
    solver_cache: dict = {}

    # Solve with no active pairs
    pa_off = {frozenset({0, 1}): False}
    t1 = time.perf_counter()
    qpr.solve_qp(0, r, v_a, theta_hat, u_2_AC, 0.0, pa_off, edges, delta_ij,
                 solver_cache)
    t_off = (time.perf_counter() - t1) * 1000

    # Solve with active pair (active-set change → cold start)
    pa_on = {frozenset({0, 1}): True}
    t2 = time.perf_counter()
    qpr.solve_qp(0, r, v_a, theta_hat, u_2_AC, 0.0, pa_on, edges, delta_ij,
                 solver_cache)
    t_on = (time.perf_counter() - t2) * 1000

    # Now solve again with the same on-state (should warm-start the on-cache)
    t3 = time.perf_counter()
    qpr.solve_qp(0, r, v_a, theta_hat, u_2_AC, 0.0, pa_on, edges, delta_ij,
                 solver_cache)
    t_on_warm = (time.perf_counter() - t3) * 1000

    print(f"\n  Active-set change benchmark (agent 0, 1 neighbour):")
    print(f"    Off-state cold-start: {t_off:.3f} ms")
    print(f"    On-state cold-start (transition): {t_on:.3f} ms")
    print(f"    On-state warm-start (after transition): {t_on_warm:.3f} ms")
    print(f"    Cold-to-warm speedup: {t_on / max(t_on_warm, 1e-6):.1f}x")

    # Loose check: warm-start should be at least somewhat faster than cold
    assert t_on_warm < t_on or t_on < 1.0, \
        f"warm-start ({t_on_warm:.3f} ms) not faster than cold ({t_on:.3f} ms)"


@pytest.mark.slow
def test_v17_2_osqp_ring8_p50_p99():
    """v17.2 N=8 antipodal-ring rosette OSQP timing (Pass 37 controls gate).

    Pass 36 Boyd: "p50 and p99 measured before quoting any caption number."
    Reports both percentiles for one agent of K_8 with up to 7 active
    constraints. The §VIII figure caption quotes these values (Pass 37).
    """
    # Mid-traversal rosette config (~ near antipodal-swap centre, all close)
    R = 1.0
    N = 8
    r = R * np.exp(1j * 2.0 * np.pi * np.arange(N) / N)
    psi0 = np.angle(np.roll(r, -4) - r)            # heading toward antipodal
    v_a = pp.V_0 * np.exp(1j * psi0)
    theta_hat = 1.5 * np.ones(N)
    u_2_AC = 0.5 * np.cos(psi0)                    # arbitrary representative
    edges = tuple((i, j) for i in range(N) for j in range(i + 1, N))
    pair_active = {frozenset({i, j}): True for (i, j) in edges}  # WORST CASE: all 28 active
    delta_ij = {frozenset({i, j}): 0.01 for (i, j) in edges}
    solver_cache: dict = {}

    # Cold-start
    t1 = time.perf_counter()
    _, _, status_cold = qpr.solve_qp(0, r, v_a, theta_hat, u_2_AC, 0.0,
                                       pair_active, edges, delta_ij,
                                       solver_cache)
    t_cold = (time.perf_counter() - t1) * 1000

    # 1000 warm-start solves with parameter perturbations
    n_warm = 1000
    rng = np.random.default_rng(42)
    times_ms = np.zeros(n_warm)
    for k in range(n_warm):
        u_perturbed = u_2_AC + 0.01 * rng.standard_normal(N)
        t0 = time.perf_counter()
        qpr.solve_qp(0, r, v_a, theta_hat, u_perturbed, 0.0,
                     pair_active, edges, delta_ij, solver_cache)
        times_ms[k] = (time.perf_counter() - t0) * 1000

    p50 = float(np.percentile(times_ms, 50))
    p99 = float(np.percentile(times_ms, 99))
    p_max = float(times_ms.max())
    print(f"\n  v17.2 N=8 K_8 OSQP (worst case: all 7 neighbours active for agent 0):")
    print(f"    Cold-start (first solve): {t_cold:.3f} ms, status = {status_cold}")
    print(f"    Warm-start p50: {p50:.3f} ms, p99: {p99:.3f} ms, max: {p_max:.3f} ms")
    print(f"    Per-step (8 agents serial, p99): {8 * p99:.3f} ms vs H_OUTER_RING8 = "
          f"{pp.H_OUTER_RING8 * 1000:.0f} ms budget")

    # Pass 37 controls gate: 8 * p99 must fit in H_OUTER_RING8 = 10 ms
    serial_per_step_ms = 8 * p99
    assert serial_per_step_ms < pp.H_OUTER_RING8 * 1000, (
        f"v17.2 N=8 serial OSQP p99 ({serial_per_step_ms:.2f} ms) exceeds "
        f"H_OUTER_RING8 budget ({pp.H_OUTER_RING8 * 1000:.0f} ms). "
        f"Either parallelise per-agent QPs OR coarsen H_OUTER further."
    )
