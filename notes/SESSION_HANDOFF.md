# Session Handoff - Multi-Agent-CBF

This document captures the state of the research project at the end of the
session on **2026-05-03**, so that work can resume on a different machine
or in a future session without losing context.

---

## 1. Project at a glance

**Repository:** `https://github.com/d8maldon/Multi-Agent-CBF`
**Working tree:** `C:\Users\maldo\Documents\GitHub\Multi-Agent-CBF`
**Latest commit (head of `main`):** `f5da72a` - "v17 WIP: sim/paper_params.py + sim/dynamics.py rewritten for complex Dubins"

The project develops a research paper, simulation pipeline, and figure set
for a **multi-agent adaptive control barrier function (CBF) safety filter
with PE-aware identification**. The contribution is the identification of
the convergence rate of the parameter estimate as the **constrained
Cramér-Rao bound (Rao 1945, §6)** on a Whitney-stratified Fadell-Neuwirth
configuration space.

Two distinct lines of work:

* **v6 → v16 (single-integrator, point-mass agents).** Self-contained,
 closed-out at Pass 17 with SUBMIT-READY for IEEE-LCSS. All math councils
 signed off; full reproducibility stack (paper + sim + figures + LaTeX +
 pytest). Retained for reference.

* **v17 (current, in progress: complex-Dubins multi-agent LOE-adaptive CBF).**
 Lifts the construction to the complex state-space representation of the
 Dubins vehicle from Maldonado-Naranjo + Annaswamy
 (arXiv 2504.08190, IEEE L-CSS 2025). State per agent is
 $(r_i, v_{a,i}) \in \mathbb{C}^2$; the unknown LOE gain $\lambda_i$ is on the
 turn-rate channel; the CBF $h_{ij} = |r_i - r_j|^2 - r_{\text{safe}}^2$ has
 relative degree 2 with respect to the control, so the safety filter uses
 the **Higher-Order CBF (HOCBF)** machinery of Xiao-Belta (2021).

---

## 2. Repository structure

```
Multi-Agent-CBF/
├── multi_agent_cbf.py # original (pre-v6) cvxpy-based baseline; not v17
├── notes/
│ ├── pe-aware-cbf-theorem.md # MAIN paper (currently v17 §1-§3 done)
│ ├── council-log.md # persistent multi-pass review history (18 passes)
│ ├── SESSION_HANDOFF.md # this file
│ └── pe-aware-cbf-controls-review-v3.md # archived review record (pre-protocol)
├── sim/
│ ├── __init__.py
│ ├── paper_params.py # v17 source-of-truth for every constant
│ ├── dynamics.py # v17 complex-Dubins (rewritten)
│ ├── qp_resolvent.py # v16 single-integrator (NEEDS REWRITE for v17)
│ ├── integrator.py # v16 (NEEDS REWRITE for v17)
│ └── plots.py # v16 figure-1..6 plotters
├── tests/
│ ├── conftest.py
│ ├── test_paper_consistency.py # 8 tests; will need v17 updates
│ ├── test_dynamics.py # 8 tests; will need v17 updates
│ ├── test_q_identity.py # 3 tests; structural, may survive
│ └── test_safety_invariants.py # 5 slow tests; need v17 updates
├── output/v16/
│ ├── figure_1_trajectories.pdf
│ ├── figure_2_param_convergence.pdf
│ ├── figure_3_identifiability.pdf
│ ├── figure_4_safety.pdf
│ ├── figure_5_ae_sweep.pdf
│ └── figure_6_comm_delay.pdf
├── paper/
│ ├── paper.tex # IEEE-LCSS LaTeX draft (v16; needs v17 update)
│ ├── refs.bib # 30 references
│ └── paper.pdf # v16 4-page PDF
├── make_figures.py # driver for all 6 v16 figures
├── run_paper_sim.py # smoke-test driver (v16)
└── README.md
```

---

## 3. The Claude skills + council protocol

The research methodology in this repo relies on three Claude skills that
live globally on the user's machine at `~/.claude/skills/`. They persist
across Claude sessions; on a new machine, they need to be reinstalled
(see "Resume on a new machine" below).

### 3.1 The three skills

| Skill | File | Role |
|---|---|---|
| `math-god-mode` | `~/.claude/skills/math-god-mode/SKILL.md` | Currently-active mathematicians: Tao, Scholze, Bhargava, Huh, Viazovska, Venkatesh, Villani, Duminil-Copin, Figalli, Lurie + applied (Annaswamy, Ames, Egerstedt, Tomlin, Krstić, Khalil, Hovakimyan). Audits proofs / theorem statements / equations / analytical claims. |
| `OG-math-experts` | `~/.claude/skills/OG-math-experts/SKILL.md` | Historical legends: Gauss, Riemann, Hilbert, Poincaré, Cauchy, Weierstrass, Lebesgue, Banach, Kolmogorov, von Neumann, Klein, Noether + control-theory OGs (Lyapunov, Krasovskii, LaSalle, Nagumo, Filippov, Moreau, Krasnosel'skii, Tikhonov, Lefschetz, Popov, Kokotović, Monopoli, Kalman, Pontryagin, Bellman, Wiener) + estimation (Fisher, Cramér, Rao, Markov) + ODE/functional-analysis (Lipschitz, Picard, Kato, Fenchel). Finds foundational gaps, structural reformulations, classical lemmas the modern proof should have invoked. |
| `controls-expert-reviewer` | `~/.claude/skills/controls-expert-reviewer/SKILL.md` | Three-sweep engineering review by present-day authorities (Annaswamy, Lavretsky, Krstić, Slotine, Khalil, Ames, Tomlin, Belta, Egerstedt, Chuchu Fan, Asada, Hogan, Featherstone, Borrelli, Morari, Wise, Hovakimyan, Recht, Abbeel/Levine). Each pass picks 3 personas matched to the content lane. |

### 3.2 Council-log protocol (anti-loop discipline)

All three skills carry a "Council log protocol" section that does the
following on every invocation:

* **Step 0: Read `notes/council-log.md` BEFORE the paper.** Auto-discovered
 at one of:
 1. `<dir-of-audited-file>/council-log.md`
 2. `<dir-of-audited-file>/.council-log.md`
 3. `<repo-root>/notes/council-log.md`
 4. `<repo-root>/.council-log.md`
* **Classify findings** as NEW / RECURRING-UNFIXED / CONFLICT-WITH-PRIOR-SIGNOFF.
 The last requires explicit justification.
* **Honour pre-commitments.** If a prior pass said "after fixes X, I will
 sign off; no further additions," and X has been applied, the verdict is
 SHIP IT (or SUBMIT-READY for the controls reviewer) unless a
 CONFLICT-WITH-PRIOR-SIGNOFF can be justified.
* **Append a new entry to the log** in a structured Markdown format.
* **Loop-break heuristic:** after 6+ passes with the most recent 3 all
 SOUND-or-better, default to SHIP IT unless a genuinely blocking issue is
 raised under a *new explicit scope*.

The protocol exists to break the iteration loop in which each pass
introduces fresh "you might also consider..." items that compound. It
worked: the simulation found a paper-internal $\Lambda$ vs $\theta$ bound
mismatch in 12 ms that 12 prior council passes had missed.

### 3.3 Council-log state at session close

`notes/council-log.md` has 18 logged passes. Headline:

* **Pass 6 (controls-expert-reviewer, v8/v9):** SUBMIT-READY with 3 blockers
 (η-gain, N-scaling, LCSS exposition). All HONOURED in v9.
* **Pass 12 (controls-expert-reviewer, v14):** SUBMIT-READY for IEEE-LCSS,
 unconditional. v16 single-integrator scope.
* **Pass 17 (close-out, v16):** integrated stack - paper + sim + 6 figures
 + LaTeX 4-page PDF + 24 pytest tests, all aligned. Pass 12 verdict
 unconditional with full reproducibility.
* **Pass 18 (NEW SCOPE declaration, v17):** complex-Dubins multi-agent
 LOE-adaptive CBF rework. Pass 12 SUBMIT-READY superseded for v17;
 v16 retained as the original LCSS submission. v17 sim/figures/tests
 rewrite forthcoming.

---

## 4. Mathematical content (v17)

### 4.1 Construction (paper §1-§3, complete in v17)

* **State per agent:** $(r_i, v_{a,i}) \in \mathbb{C}^2$, where
 $r_i = x_i + i y_i$ is position and $v_{a,i} = V_{a,i} e^{i\psi_i}$ is
 velocity-along-heading.
* **Dynamics (Maldonado-Naranjo + Annaswamy 2025, eq. 5-6):**
 $\dot r_i = v_{a,i}$, $\dot v_{a,i} = (u_{1,i} + i \lambda_i u_{2,i}) v_{a,i}$.
 Constant-speed simplification (eq. 16): $V_a = V_0$, so only the turn-rate
 $u_{2,i} \in \mathbb{R}$ is the effective control, and
 $\dot v_{a,i} = i \lambda_i u_{2,i} v_{a,i}$.
* **Unknown LOE:** $\lambda_i \in [\lambda_{\min}, 1]$ on the turn-rate
 channel only (asymmetric).
* **Adaptive law:** $\hat\theta_i \to 1/\lambda_i$ via Pomet-Praly normalised
 swapped-signal gradient on the complex regressor
 $i v_{a,i} u_{2,i}^{\text{ref}}$.
* **CBF:** $h_{ij} = |r_i - r_j|^2 - r_{\text{safe}}^2$. Relative degree 2
 with respect to $u_2$ (in v16 it was relative degree 1 because the plant
 was a single integrator).
* **HOCBF (Xiao-Belta 2021):** enforce
 $\ddot h_{ij} + (\alpha_1 + \alpha_2)\dot h_{ij} + \alpha_1 \alpha_2 h_{ij} \ge 0$.
 This is *linear* in $u_{2,i}, u_{2,j}$, so the per-agent QP has a scalar
 decision variable $u_{2,i} \in \mathbb{R}$ (much simpler than v16's
 $\mathbb{R}^d$ decision variable).
* **Gauge-fixing:** multiply through by $\hat\theta_i$ to remove the unknown
 $\lambda_i$ from the constraint coefficient. Klein-Erlangen
 $\mathbb{R}_{>0}$-symmetry preserved across the dynamics upgrade.
* **Moreau sweeping process (1977) + Crandall-Liggett (1971)** still apply
 unchanged - the relative-degree-2 nature is absorbed into the definition
 of the constraint set $K_i$, but $K_i$ is still a closed convex (interval)
 set, so the Hilbert projection / Yosida resolvent framework lifts.

### 4.2 What's done in v17 paper

* §1 problem statement
* §2 plant + dynamics + LOE + reference + adaptive + KB (full rewrite)
* §3.1 HOCBF derivation + relative-degree analysis + gauge-fixed constraint
* §3.2 boxed scalar QP
* §3.3 numerical scheme (carries over from v16; same h_outer, OSQP tol)
* §3.4 Lemma 1 well-posedness (carries over with notation lift)

### 4.3 What's NOT done in v17 paper (next session work)

* §4 Composite swapped-signal Lyapunov on complex tracking error
 $e_i = r_i - r_{\text{ref},i}$, $\tilde v_i = v_{a,i} - v_{\text{ref},i}$.
 The Pomet-Praly cancellation (Noether 1918 attribution) lifts to the
 complex setting: the symmetry group is now $\mathbb{R}_{>0} \times U(1)$
 (scaling on $\hat\theta$ + heading rotation).
* §5 Birkhoff identifiability via $Q_i$ on the complex projected regressor.
 $Q_i$ becomes a complex Hermitian matrix (or its $2\times 2$ real
 representation); $\bar\rho_i = \mathrm{tr}(Q_i)$ unchanged in form.
* §6 Theorem (three-sentence Bourbaki form): same three conclusions
 (forward invariance, UUB, parameter convergence) on the new state.
* §7 Six-lemma proof outline: same lemma structure (Nagumo + Hilbert +
 Krasovskii + Brezis-Crandall-Liggett-Hager + Birkhoff + Hager-Liberzon
 dwell-time), with notation lift.
* §8 Worked examples on Dubins paths:
 * §8.1: $N=2$ Dubins agents on a head-on conflict path.
 * §8.2: $N=4$ Dubins agents in a cross-swap with smooth (turn-radius-
 feasible) paths through the centre.
* §8.3 v17 simulation parameter values: written into `sim/paper_params.py`.
* §8.4 figure plan: same six figures as v16 but on Dubins, plus an
 **animation supplementary** showing oriented agents (per Pass 18 plan
 and the figure-quality finding from the controls-expert-reviewer Pass
 on the v16 figures).

### 4.4 What's done in v17 sim

* `sim/paper_params.py`: complete rewrite for Dubins (V_0, psi_dot_max,
 alpha_1, alpha_2, complex CROSSSWAP_R0, oscillating targets in complex
 form, per-agent PE frequencies).
 `python -m sim.paper_params` passes all 5 consistency checks.
* `sim/dynamics.py`: complete rewrite. Functions
 `reference_velocity` (returns complex desired velocity capped at V_0),
 `reference_turn_rate` (heading-PD: $u_2 = K_T \arg(v_{\text{des}} / v_a)$),
 `adaptive_law_rate` (complex Pomet-Praly), `kalman_bucy_riccati`,
 `excitation_signal` (now scalar), `cbf_h`, `cbf_h_dot`, `hocbf_residual`,
 `hocbf_jacobian_self/other`, `update_hysteresis` (lifted to complex
 state with HOCBF $c_{ij}$), `cbf_tightening_delta`.

### 4.5 What's NOT done in v17 sim (next session work)

* `sim/qp_resolvent.py` - needs rewrite. The QP now has a *scalar* decision
 variable $u_{2,i}$ per agent (was vector $u \in \mathbb{R}^d$ in v16).
 Constraint is `a_ii * u_{2,i} + a_ij * u_{2_j_AC} + theta_hat * b_0 >= delta`,
 linear in $u_{2,i}$. With slack: minimise
 $(u_2 - u_2^{\text{AC}} - e_{\text{pe}}^{\text{proj}})^2 + M \sum s_{ij}^2$
 s.t. constraint + $|u_2| \le \dot\psi_{\max}$, $s_{ij} \ge 0$.
 OSQP solver caching by active-set signature still applies.
* `sim/integrator.py` - needs rewrite. State is now per-agent complex
 $(r_i, v_{a,i})$ (or 4 real numbers per agent). RK4 step on
 $(r, v_a, \hat\theta, P)$. Comm-delay buffer carries over conceptually.
* `make_figures.py` and `sim/plots.py` - v16 figures will mostly carry
 over with state-name changes (`x` → `r`, plus rendering agents as
 oriented triangles using `arg(v_a)` for heading).
* `paper/paper.tex` - needs the §2-§3 v17 content folded in, plus new
 citations for Maldonado-Naranjo + Annaswamy 2025 and Xiao-Belta 2021.
* Tests - need updates to the new function signatures.

---

## 5. How to resume on a new machine

### 5.1 Clone the repo

```bash
git clone https://github.com/d8maldon/Multi-Agent-CBF.git
cd Multi-Agent-CBF
pip install numpy scipy osqp matplotlib pytest
```

### 5.2 Reinstall the Claude skills

The three skills live in `~/.claude/skills/` on the original machine.
On a new machine, recreate them:

```
~/.claude/skills/math-god-mode/SKILL.md
~/.claude/skills/OG-math-experts/SKILL.md
~/.claude/skills/controls-expert-reviewer/SKILL.md
```

The full SKILL.md content is captured in the git history of those files
(they are user-config, not in this repo). To re-create them, either:

1. **Restore from another machine** if a previous machine still has them:
 `scp -r oldmachine:~/.claude/skills/{math-god-mode,OG-math-experts,controls-expert-reviewer} ~/.claude/skills/`

2. **Re-create from scratch** following the structure documented below.
 Each SKILL.md has YAML frontmatter (`name`, `description`, `version`,
 `argument-hint`, `allowed-tools: Read, Grep, Glob, WebSearch, WebFetch`),
 an introduction, a panel-of-personas table, ten "rigour commandments,"
 the output format, the procedure, and the "Council log protocol"
 anti-loop section.

### 5.3 Reinstall is necessary because the protocol files are global

The skill files are in `~/.claude/skills/`, NOT inside this repo. The
council-log file (`notes/council-log.md`) IS in the repo and persists with
its full 18-pass history.

### 5.4 Verify the v16 baseline runs

```bash
python -m sim.paper_params # passes 5 consistency checks
python -m pytest tests/ # 19 fast tests - will fail until
 # tests are updated to v17 sigs
```

Note: the tests were written against the v16 single-integrator API and
will need updates once `qp_resolvent.py` and `integrator.py` are rewritten
for v17.

### 5.5 Resume v17 work

The next session should:

1. **Rewrite `sim/qp_resolvent.py`** for the scalar-$u_2$ QP. Use the
 functions `hocbf_jacobian_self`, `hocbf_jacobian_other`, and
 `hocbf_residual` from `sim/dynamics.py` to build the linear constraint.
2. **Rewrite `sim/integrator.py`** for $\mathbb{C}^2$ state. RK4 over
 $(r, v_a, \hat\theta, P)$. Re-use the comm-delay buffer pattern from
 v16.
3. **Update tests** to the new signatures, then run.
4. **Re-run the figures** using the new sim. Figure 1 (trajectories) will
 now show curved Dubins paths - much more visually compelling than the
 single-integrator straight lines.
5. **Add an animation** as the controls-expert-reviewer Pass on v16
 figures requested. With Dubins agents having real headings, an
 oriented-triangle rendering becomes natural.
6. **Lift paper §4-§8** into v17 (Lyapunov on complex tracking error,
 Birkhoff identifiability with complex $Q_i$, three-sentence theorem,
 six-lemma proof outline, worked examples).
7. **Re-invoke the councils** under the v17 scope (per Pass 18, the
 loop-break heuristic resets for the new scope).

---

## 6. Reference: the LOE-Dubins paper this work extends

**Maldonado-Naranjo, D., Annaswamy, A. M. (2025).**
"Adaptive Control of Dubins Vehicle in the Presence of Loss of
Effectiveness," IEEE L-CSS / arXiv:2504.08190.

Key equations (numbered as in the source PDF):

* (3): $r = x + iy$ - position complex
* (4): $\dot r = v_a$, $v_a = V_a e^{i\psi}$ - velocity-along-heading
* (5): $\dot v_a = u v_a$ where $u = \dot V_a / V_a + i \dot\psi$ - bilinear
 complex control
* (6): LOE inserted on turn-rate: $\dot v_a = (\dot V_a/V_a + i\lambda \dot\psi) v_a$
* (16): constant-speed simplification: $\dot v_a = i \lambda u_2 v_a$
* (11): reference model $\dot r_{\text{ref}} = v_{\text{ref}}$,
 $\dot v_{\text{ref}} = u_{\text{ref}} v_{\text{ref}}$

The multi-agent extension in this repo lifts (16) to a network of $N$
agents with pairwise CBF safety filters and per-agent PE-aware
identification of $\lambda_i$.

---

## 7. Key references (pre-1985 lineage)

The v16/v17 framework composes nine pre-1985 classical objects:

1. **Nagumo (1942)** - viability theorem (foundational for CBF).
2. **Moreau (1977)** - sweeping process on time-varying convex sets.
3. **Crandall-Liggett (1971)** - exponential formula for autonomous
 resolvent semigroups.
4. **Noether (1918)** - first theorem (swapped-signal cancellation).
5. **Hilbert-Courant (1924)** - min-max on the formation Laplacian.
6. **Krasovskii (1959 §14.2)** - ultimate boundedness.
7. **Krasnosel'skii-Pokrovskii (1989)** - hysteresis operator
 alternative to PDMP.
8. **Birkhoff (1931)** - ergodic theorem (time-average → ensemble).
9. **Klein (1872) Erlangen + Rao (1945) §6** - $O(d)$-invariant
 constrained Fisher information; the convergence rate is its trace.

Plus the modern context: **Boyd-Sastry (1986)** unconstrained-MRAC PE
baseline; **Ames-Xu-Grizzle (2014)** ZCBF rediscovery; **Xiao-Belta
(2021)** HOCBF (used in v17); **Davis (1984)** PDMP; **Anderson (1985)**
PE-decay; **Stellato et al. (2020)** OSQP; **Maldonado-Naranjo +
Annaswamy (2025)** complex-state Dubins LOE adaptive control.

---

## 8. Final commit chain (this session)

Recent commits on `main`:

```
f5da72a v17 WIP: sim/paper_params.py + sim/dynamics.py rewritten for complex Dubins
a1f5c37 v17 (Pass 18, NEW SCOPE): complex-Dubins multi-agent LOE-adaptive CBF
1517d27 Steps 1-4: comm-delay sweep + LaTeX draft + pytest suite (Pass 17)
bdfd7e1 Section 8.4 figure pipeline: figs 1-5 generated from v16 sim
3957d53 v16: Pass 15 scenario hardening (oscillating targets + per-agent PE)
295970b v15 paper + sim: Pass 13 finding 1 fixed, finding 3 resolved as side-effect
b681b2d sim/: paper-traceable v14 simulation + Pass 13 council findings
2b21fe1 Add council-log.md: persistent multi-pass review history
11f1194 Council log Pass 12: controls-expert-reviewer SUBMIT-READY on v14
e70c857 PE-aware CBF v14: OG-council 5 fixes applied verbatim
d5abcd9 PE-aware CBF v13: panel-consensus pre-verified fixes applied
```

Earlier commits (v6-v12) are in the repo's full git log via
`git log --oneline notes/pe-aware-cbf-theorem.md`.

---

## 9. Status summary at session end

| Layer | State |
|---|---|
| v16 paper + sim + figs + LaTeX + tests | **Pass 12 SUBMIT-READY for IEEE-LCSS, unconditional, with full reproducibility stack.** |
| v17 paper §1-§3 (complex Dubins) | **Done.** State, dynamics, HOCBF, gauge-fixed constraint, scalar QP all written. |
| v17 paper §4-§8 | **Pending.** Need to lift Lyapunov, Birkhoff, theorem, examples. |
| v17 sim - paper_params + dynamics | **Done.** Consistency checks pass. |
| v17 sim - qp_resolvent + integrator | **Pending.** v16 versions don't match new function signatures. |
| v17 figures + animation | **Pending.** Will be much more visually compelling on Dubins. |
| v17 tests | **Pending.** Existing tests written against v16 API. |
| Council passes | 18 logged. Pass 18 declared NEW SCOPE; v17 review reopens once sim is reviewable. |

When resuming: start at §4.5 above (the "what's NOT done in v17 sim"
list) and work top-to-bottom.
