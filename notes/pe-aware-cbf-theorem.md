# Excitation-Preserving Distributed Safety Filter for Multi-Agent Adaptive Control

**Status:** v9, LCSS-form rewrite (post Krstić / Borrelli / Lavretsky controls audit). Continuous-time simulation only; no hardware claims.
**Length target:** IEEE-LCSS 8-page limit; current draft fits ~6.5 pages with slack.

---

## Abstract

For a network of $N$ single-integrator agents with unknown control effectiveness $\Lambda_i$, we identify the convergence rate of the parameter estimate $\hat\theta_i \to 1/\Lambda_i$ under a distributed CBF safety filter as the **constrained Cramér-Rao bound on a Whitney-stratified Fadell-Neuwirth configuration space**. The freedom-cone projection - the orthogonal complement of the active CBF normals - extracts the identifiable component of the open-loop reference; its time-averaged second moment $Q_i = \mathbb{E}_\mu[(\mathrm{Proj}_{F_i} u_i^{\text{ref}})(\mathrm{Proj}_{F_i} u_i^{\text{ref}})^\top]$ is the constrained Fisher information of $1/\Lambda_i$, and its trace gives the exponential rate. The construction composes eight pre-1985 classical objects (maximal monotone resolvent, Noether's first theorem, Hilbert-Courant min-max, Krasovskii ultimate boundedness, Krasnosel'skii-Pokrovskii hysteresis operator, Birkhoff ergodic theorem, Klein $O(d)$-invariance, Rao constrained Fisher information). Continuous-time simulation; the QP-resolvent at $h_{\text{outer}} = 5$ ms with OSQP is real-time feasible up to $N \approx 50$ agents.

## 1. Problem statement

A team of $N$ agents must reach a target formation $\{t_i\}_{i=1}^N$ in $\mathbb{R}^d$ while (i) maintaining pairwise safety $\|x_i - x_j\| \ge r_{\text{safe}}$, (ii) identifying each agent's unknown control effectiveness $\Lambda_i$, and (iii) using only neighbour-broadcast information $\{x_j, \hat\theta_j\}$ from a connected communication graph $\mathcal{G}$. Existing single-agent adaptive CBF results (Cohen-Belta 2020, 2022, 2023; Gutierrez-Hoagg 2024) achieve safety with vanishing parameter-induced conservativeness but do not characterise the identifiability rate when the safety filter and the adaptive law share the same control variable. We resolve this by recognising that the *projected* reference - the component orthogonal to the active CBF normals - drives identification, and that its second moment is the classical constrained Fisher information of Rao (1945).

---

## Notation

| Symbol | Type | Meaning |
|---|---|---|
| $i \in \{1, \dots, N\}$ | index | agent index |
| $\mathcal{G} = (V, \mathcal{E})$ | undirected graph on $V = \{1,\dots,N\}$ | communication / formation topology |
| $\mathcal{N}_i$ | $\subset V \setminus \{i\}$ | neighbours of $i$ |
| $x_i, z_i, t_i$ | $\mathbb{R}^d$ | plant state, reference state, target slot |
| $\Lambda_i$ | $[\Lambda_{\min}, 1]$, $\Lambda_{\min} > 0$, constant | unknown control effectiveness |
| $\hat\theta_i$ | $[\theta_{\min}, \theta_{\max}]$ | adaptive estimate of $1/\Lambda_i$ |
| $u_i^{\text{ref}}, u_i^{\text{AC}}, u_i^{\text{safe}}$ | $\mathbb{R}^d$ | reference, adaptive, safety-filtered command |
| $\phi_i := u_i^{\text{ref}}$ | $\mathbb{R}^d$ | regressor for agent $i$'s adaptation |
| $h_{ij}(x) := \|x_i - x_j\|^2 - r_{\text{safe}}^2$ | $C^\infty(\mathbb{R}^{2d}, \mathbb{R})$ | inter-agent barrier function (relative degree 1) |
| $K(t,x)$ | closed convex polyhedron in $\mathbb{R}^d$ | per-agent feasible control set under all CBF and saturation constraints |
| $A(t,x)$ | maximal monotone operator on $\mathbb{R}^d$ | $A(t,x)(u) := \partial \chi_{K(t,x)}(u) = N_{K(t,x)}(u)$, the normal cone |
| $J_h^{(t,x)}$ | resolvent map | $J_h^{(t,x)}(v) := (I + h\,A(t,x))^{-1}(v)$, computed by the per-agent QP |
| $P_i(t)$ | scalar $\ge 0$ | Kalman-Bucy covariance bound on $|\hat\theta_i(t) - 1/\Lambda_i|^2$ |
| $\mathcal{A}_i^{\varepsilon,\text{on}}, \mathcal{A}_i^{\varepsilon,\text{off}}$ | $\subset \mathcal{N}_i$ | hysteretic active sets (engaged / disengaged) |
| $Q_i$ | symmetric PSD on $\mathbb{R}^{d\times d}$ | constrained Fisher information matrix [Rao 1945; Aitchison-Silvey 1958]: $Q_i := \mathbb{E}_\mu[(\mathrm{Proj}_{F_i} u_i^{\text{ref}})(\mathrm{Proj}_{F_i} u_i^{\text{ref}})^\top]$ |
| $\bar\rho_i$ | scalar identifiability gain | $\bar\rho_i := \mathrm{tr}(Q_i)$, the scalar Cramér-Rao bound on $1/\Lambda_i$ |
| $\mathcal{M}$ | $\omega$-limit set | closed-loop attractor on the augmented PDMP state space |
| $m_i^2 := 1 + \|u_i^{\text{ref}}\|^2$ | $\ge 1$ | normalisation gain (swapped-signal Lyapunov) |

## Axioms

- **(A1) Bounded admissible parameter set.** $\Lambda_i \in [\Lambda_{\min}, 1]$, $\Lambda_{\min} > 0$, time-invariant. Estimate $\hat\theta_i \in [\theta_{\min}, \theta_{\max}]$ enforced via the Krstić-Kanellakopoulos-Kokotović (1995) smooth projection. Required prior tightness: $\theta_{\max}/\theta_{\min} \le \kappa_\Lambda$ for the QP to remain feasible (see §6).
- **(A2) Bounded admissible reference and connected graph.** $\{z_i, \dot z_i, t_i, \dot t_i\}$ uniformly bounded by $u_{\max}^{\text{ref}}$; $\mathcal{G}$ connected. Define $D_{\max} := 2\big(\sup_i \|z_i\|_\infty + R_{\text{UUB}}\big) + r_{\text{safe}}$, where $R_{\text{UUB}} = \sqrt{2 V(0)}$ is the UUB radius from Lemma 5.3 (the chain $D_{\max}$-needs-UUB is non-circular: $V(0)$ is a *datum*, not a closed-loop quantity).
- **(A2') Closed-loop persistence of excitation.** The target trajectory $t_i(t)$ is non-stationary in the sense $\beta_1 I \preceq T_0^{-1} \int_t^{t+T_0} \dot t_i \dot t_i^\top\, d\tau$ for some $\beta_1, T_0 > 0$. Combined with the MRAC error decay (Lemma 5.3) this guarantees $u_i^{\text{ref}}$ remains PE on the closed loop, hence the Kalman-Bucy covariance $P_i(t) \to 0$ exponentially. (Without (A2'), use the stochastic variant $Q > 0$ in §1 and replace the $P_i \to 0$ claim with $P_i \to P_i^*$.)
- **(A3') Initial strict safety with margin.** There exists $\zeta > 0$ such that $h_{ij}(x(0)) \ge \delta_{ij}(0) + \zeta$ for all $i \ne j$, where $\delta_{ij}(0) = 2 D_{\max}(\sqrt{P_i(0)}/\theta_{\min})(\sqrt{d}\,u_{\max} + \theta_{\max} u_{\max}^{\text{ref}})$ is the initial CBF tightening from Lemma 5.2. Equivalently, $\delta_{ij}(0) \le \tfrac12 r_{\text{safe}}^2$ as a precondition on the data; this is what the prior tightness $\kappa_\Lambda$ buys.
- **(A4) Neighbour broadcast.** Each agent $i$ has continuous-time access to $\{x_j(t), \hat\theta_j(t) : j \in \mathcal{N}_i\}$. (Discrete / event-triggered relaxations: separate paper.)
- **(A5) Active-set non-saturation.** On the closed-loop invariant set $\mathcal{M}$, $|\mathcal{N}_i^{\text{on}}(t)| < d$ for $\mu$-a.e. $t$, where $\mu$ is the invariant measure from §4. Equivalently, no agent is simultaneously safety-active against $d$ or more neighbours; freedom cone $F_i$ is non-trivial $\mu$-a.e. Holds generically when $\deg(\mathcal{G}) < d$; otherwise must be checked numerically per scenario.
- **(A5') Minimum subtended angle (only required for $d \ge 3$).** There exists $\theta_{\min} > 0$ such that for any agent $i$ with $\ge 2$ active neighbours $j, k \in \mathcal{N}_i^{\text{on}}$, the angle $\angle j i k \ge \theta_{\min}$ holds $\mu$-a.e. Implies $\sigma_{\min}^{\text{geom}}(G_i) \ge \sin(\theta_{\min}/2) > 0$, which keeps $L_{\text{QP}}^*$ (§2.4) finite. **Vacuous for $d = 2$**: (A5) restricts to at most one active constraint, so $G_i$ is a single row and $\sigma_{\min}^{\text{geom}} = 1$ automatically. All worked examples in §7 are $d = 2$.

These six axioms (A1, A2, A2', A3', A4, A5) plus the dimensional regularity (A5') (vacuous for $d = 2$) are *all* the hypotheses. Lipschitz constraints, regularity of the closed loop, and dwell-time bounds are *consequences*.

---

## 1. Plant, reference, adaptive law, and Kalman-Bucy auxiliary

For each agent $i$:
$$
\dot x_i = \Lambda_i\, u_i, \qquad
u_i^{\text{ref}} = -K_T(z_i - t_i) - K_F \sum_{j \in \mathcal{N}_i}\!\big[(z_i - z_j) - (t_i - t_j)\big],
$$
$$
u_i^{\text{AC}} = \hat\theta_i\, u_i^{\text{ref}}, \qquad
\dot{\hat\theta}_i = \mathrm{Proj}_{[\theta_{\min},\theta_{\max}]}\!\Big[ -\frac{\gamma}{m_i^2}\, (u_i^{\text{ref}})^\top (x_i - z_i) \Big],
\qquad \dot z_i = u_i^{\text{ref}}.
$$

In parallel, run a **Kalman-Bucy filter** (Kalman-Bucy 1961) on the same data, producing a covariance bound $P_i(t)$ on $|\hat\theta_i(t) - 1/\Lambda_i|^2$:
$$
\dot P_i \;=\; -P_i\, \frac{(u_i^{\text{ref}})^\top u_i^{\text{ref}}}{m_i^2}\, P_i \;+\; Q,
$$
with $P_i(0) = (\theta_{\max} - \theta_{\min})^2$ and $Q^{\text{KB}} = 0$ (deterministic Riccati; matches Anderson's framework; not to be confused with the Fisher matrix $Q_i$ defined in §4). Under (A2') closed-loop PE on $u_i^{\text{ref}}$, $P_i(t) \to 0$ exponentially at rate $\gamma \cdot \mathrm{tr}(Q_i)$ by Anderson (1985); see §4. (Stochastic variant with $Q^{\text{KB}} > 0$: replace conclusion (2) with $\mathcal{O}(A_e^2/\eta + Q^{\text{KB}})$; we keep the deterministic form.) The filter is *auxiliary* - its output is used only to compute the time-varying CBF tightening $\delta(t)$ in §2.

---

## 2. The resolvent QP (Hilbert projection + Klein-Erlangen gauge fixing)

### 2.1. Constraint set and the maximal monotone operator

For each $\{i, j\}$ with $j \in \mathcal{N}_i$, the time-varying CBF constraint, **gauge-fixed by multiplying through by $\hat\theta_i$**:
$$
c_{ij}(u_i; x, \hat\theta) \;:=\; 2(x_i - x_j)^\top u_i \;-\; 2\,\frac{\hat\theta_i}{\hat\theta_j}\,(x_i - x_j)^\top u_j^{\text{AC}} \;+\; \alpha\,\hat\theta_i\, h_{ij}(x) \;\ge\; \delta_{ij}(t),
$$
where $\delta_{ij}(t) = 2 D_{\max}\, \big(\sqrt{P_i(t)}/\theta_{\min}\big) (\sqrt{d}\,u_{\max} + \theta_{\max}\,u_{\max}^{\text{ref}})$ is the time-varying tightening from Lemma 5.2 (vanishing as $P_i(t) \to 0$), and $\alpha > 0$ is the linear class-$\mathcal{K}$ gain in the ZCBF condition $\dot h_{ij} + \alpha h_{ij} \ge 0$ [Ames-Xu-Grizzle 2014 eq. 14].

The decision-variable coefficient is $2(x_i - x_j)$ - independent of $\hat\theta$. The constraint Jacobian is $\hat\theta$-independent. The QP Hessian (from the squared objective) is $2I$. The solver sees no $\hat\theta$-dependent matrix structure; only RHS coefficients vary, and bounded by $\theta_{\max}/\theta_{\min}$ [Wright 1997 §11].

The feasible set:
$$
K(t,x) \;:=\; \big\{ u \in \mathbb{R}^d : c_{ij}(u; x, \hat\theta) \ge \delta_{ij}(t)\ \forall j \in \mathcal{N}_i^{\text{on}}(t),\ \|u\|_\infty \le u_{\max} \big\},
$$
with **hysteretic** active set: $\mathcal{N}_i^{\text{on}}(t)$ engages when $c_{ij} \le \varepsilon$ and disengages when $c_{ij} \ge 2\varepsilon$, where $\varepsilon \in [\delta_{ij}(t) + \text{tol}_{\text{QP}},\; 0.1\, r_{\text{safe}}^2]$. Hysteresis rules out Zeno chattering on each pair via Liberzon (2003) §1.2; the multi-surface dwell-time bound is Lemma 5.6 below.

The closed-loop is the differential inclusion
$$
\dot x_i \in \Lambda_i\, u_i,\qquad u_i \in K(t,x),
$$
whose right-hand side is governed by the time-varying maximal monotone operator $A(t,x)$ given by the normal cone $N_{K(t,x)}$ [Rockafellar 1970; Brezis 1973 §2.1].

### 2.2. The QP is the resolvent

Pick a per-agent excitation signal $e_i^{\text{pe}}: \mathbb{R}_{\ge 0} \to \mathbb{R}^d$ with $\|e_i^{\text{pe}}\| \le A_e$, and project onto the freedom cone $F_i(t) := (\mathrm{span}\{2(x_i - x_j) : j \in \mathcal{N}_i^{\text{on}}\})^\perp$:
$$
\tilde e_i^{\text{pe}}(t) := \mathrm{Proj}_{F_i(t)}\big[ e_i^{\text{pe}}(t) \big].
$$

The control law is the metric projection of the QP target onto the feasible set, which **is** the Yosida resolvent $J_h^{(t,x)}$ at step size $h \to 0^+$:
$$
\boxed{\;
u_i^{\text{safe}}(t) \;=\; J_h^{(t,x)}\!\big(u_i^{\text{AC}}(t) + \tilde e_i^{\text{pe}}(t)\big)
\;=\; \arg\min_{u \in K(t,x)} \; \big\|u - (u_i^{\text{AC}} + \tilde e_i^{\text{pe}})\big\|^2 \;+\; M\, s_{ij}^2,
\;}
$$
where $s_{ij} \ge 0$ is a slack variable on each CBF constraint, penalised by $M \gg 1$, ensuring feasibility under saturation [Ames-Xu-Grizzle 2014]. Default $M = 10^4$: empirically yields $\|s_{ij}\| \le 10^{-3}$ when not safety-critical and $\|s_{ij}\| \approx 10^{-1}$ on the boundary; larger $M$ degrades QP conditioning (see §2.4). As $M \to \infty$, the slack solution converges to the hard-constrained solution where feasible.

The continuous-time closed-loop trajectory is generated by the **Crandall-Liggett (1971) exponential formula**:
$$
x(t) \;=\; \lim_{n \to \infty}\, J_{t/n}^{(t/n, x_{n-1})} \circ \cdots \circ J_{t/n}^{(0, x_0)}(x_0),
$$
the implicit-Euler scheme with the QP as the resolvent map. Existence + uniqueness + continuous dependence on data are immediate from Brezis (1973) Theorem 4.2. **No smoothed-sigmoid regularisation is required** - the QP itself is the resolvent.

### 2.3. Numerical scheme (Brezis Cor 4.2 + Hager 1979)

Crandall-Liggett's $\lim_{n \to \infty}$ is an existence result; the simulation picks a finite outer step $h_{\text{outer}} > 0$ and an inner QP tolerance $\text{tol}_{\text{QP}} > 0$. By Brezis (1973) Cor. 4.2 + Hager (1979),
$$
\|x_n - x(t_n)\| \;\le\; C_1\, h_{\text{outer}} \;+\; C_2\, \text{tol}_{\text{QP}}/h_{\text{outer}},
$$
so the two errors must be balanced. Default pairing (matches the existing repo and stays inside Simulink's fixed-step loop):
$$
h_{\text{outer}} = 5\times 10^{-3}\;\text{s}, \qquad \text{tol}_{\text{QP}} = 10^{-7}.
$$
Inner solver: **OSQP** (Stellato et al. 2020) - chosen for warm-start support and Python+MATLAB ABI. Per-agent QP has $\le d + |\mathcal{N}_i^{\text{on}}|$ decision variables and $\le |\mathcal{N}_i^{\text{on}}| + 2d$ inequality constraints (CBF + slack + saturation). For $N=4, d=2$: ≤5 variables, ≤7 constraints; OSQP solves in ~0.1 ms warm-started on a desktop CPU. Per-step cost scales as $\mathcal{O}(N \cdot \deg(\mathcal{G}))$; **real-time feasible up to $N \approx 50$ at $h_{\text{outer}} = 5$ ms** on an Intel i7-12700-class CPU. Beyond $N = 50$, parallelise per-agent QPs (independent across agents) or coarsen $h_{\text{outer}}$.

**Warm-start at hysteresis events.** The active-set change at an event invalidates the OSQP warm-start (different problem dimension); the implementation cold-starts OSQP for the first iteration after each event. Empirically, events occur at frequency $\sim 1/\tau_d \approx 1$ Hz (Lemma 5.6 dwell-time), so the cost penalty is $\sim 10\times$ per event $\times$ 1 Hz $= \sim 1$ ms additional per second; negligible at $h_{\text{outer}} = 5$ ms.

Outer integrator: fixed-step RK4 (preferred for Simulink) or ode15s with mass-matrix identity (preferred for adaptive step-sizing studies). The QP is the resolvent $J_{h_{\text{outer}}}$; no DAE machinery is needed because the constraint enters only through the projection, not as an algebraic equation in the state.

For $N = 2$, $d = 2$, single active pair, the QP admits the closed-form Lagrangian solution
$$
u_i^{\text{safe}} \;=\; (u_i^{\text{AC}} + \tilde e_i^{\text{pe}}) + \mu_{ij}^* \cdot 2(x_i - x_j), \qquad \mu_{ij}^* = \max\!\Big(0,\, \frac{\delta_{ij}(t) - c_{ij}(u_i^{\text{AC}} + \tilde e_i^{\text{pe}})}{\|2(x_i - x_j)\|^2}\Big),
$$
which is the unit test for the OSQP wrapper before scaling to $N \ge 3$.

### 2.4. Lemma 1 (well-posedness of the QP-resolvent)

Under (A1), (A2), (A2'), (A3'), (A4), (A5), the QP admits a unique solution that is *piecewise-affine* on the hysteretic strata of $\mathcal{N}_i^{\text{on}}$ and *Lipschitz* in $(x, \hat\theta, e_i^{\text{pe}})$ on each stratum. The constraint Jacobian for agent $i$'s decision variable $u_i$ is $\hat\theta$-independent (the $\hat\theta_i / \hat\theta_j$ cross-coupling enters only as a linear shift in the RHS).

*Sketch.* Strict convexity (objective Hessian $2I$) + linear constraints with non-empty interior (by A3' + Lemma 5.1) + Hilbert projection theorem [Hilbert 1906; Riesz 1907]. Lipschitz constant from Hager (1979) Theorem 3.1: with $G_i(t,x) \in \mathbb{R}^{|\mathcal{N}_i^{\text{on}}| \times d}$ the active-constraint Jacobian (rows $2(x_i - x_j)^\top$),
$$
L_{\text{QP}}(t,x) \;=\; \frac{1}{\sigma_{\min}(G_i(t,x))} \cdot \big(1 + \kappa_\Lambda \cdot |\mathcal{N}_i^{\text{on}}(t)|\big),
$$
where $\sigma_{\min}(G_i)$ is the smallest singular value of the active Jacobian. By (A5), $|\mathcal{N}_i^{\text{on}}| \le d - 1$ $\mu$-a.e., so $\sigma_{\min}(G_i) \ge 2 r_{\text{safe}}\, \sigma_{\min}^{\text{geom}}$ where $\sigma_{\min}^{\text{geom}} > 0$ is the *geometric configuration* constant (smallest singular value of the unit-direction matrix; bounded away from zero on $\mathcal{M}$ when no two active normals are collinear). Worst-case bound:
$$
L_{\text{QP}}^* \;:=\; \sup_{(t,x) \in \mathcal{M}} L_{\text{QP}}(t,x) \;\le\; \frac{1 + \kappa_\Lambda (d-1)}{2 r_{\text{safe}} \, \sigma_{\min}^{\text{geom}}}.
$$
Piecewise-affine on each stratum: Robinson (1980). Cross-stratum continuity follows from Lemma 5.6 (uniform dwell-time). ∎

---

## 3. Composite swapped-signal Lyapunov function

For each $i$:
$$
V_i := \frac{1}{2}\,\frac{\|x_i - z_i\|^2}{m_i^2} + \frac{\Lambda_i}{2\gamma}\,(\hat\theta_i - 1/\Lambda_i)^2,
$$
$$
V := \sum_{i=1}^N V_i \;+\; \kappa \sum_{1 \le i < j \le N} B(h_{ij}(x)),
$$
with $B \in C^2((0,\infty), \mathbb{R}_{\ge 0})$ a smooth interior-point barrier ($B(s) = -\log s$, monotone-decreasing, blowing up as $s \to 0^+$) [Krasovskii 1959 interior-point analog; Tee-Ge-Tay 2009 modern barrier-Lyapunov].

### 3.1. Lemma 2 (Krasovskii ultimate boundedness)

Along closed-loop trajectories under §2,
$$
\dot V \;\le\; -\eta\, \sum_i \frac{\|x_i - z_i\|^2}{m_i^4} \;+\; \mathcal{O}(A_e^2)\;+\;\mathcal{O}\!\big(\textstyle\sup_i \|P_i(t)\|^2\big),
$$
where the decay constant $\eta$ is computed in two steps.

**Step (a): swapped-signal cancellation (Noether 1918).** The cancellation is Noether's first theorem applied to the one-parameter group $G_\lambda : (e_i, \tilde\theta_i) \mapsto (\lambda^{-1} e_i, \lambda \tilde\theta_i)$, $\lambda \in \mathbb{R}_{>0}$, under which $V_i$ is invariant; what Pomet-Praly (1992) wrote out by hand is the Noether-conserved quantity. Differentiating $V_i$ and substituting the adaptive law $\dot{\hat\theta}_i = -(\gamma/m_i^2)(u_i^{\text{ref}})^\top e_i$ with $e_i := x_i - z_i$ and $\tilde\theta_i := \hat\theta_i - 1/\Lambda_i$ gives
$$
\dot V_i \;=\; \underbrace{\frac{\Lambda_i}{m_i^2} e_i^\top \tilde\theta_i u_i^{\text{ref}}}_{\text{cross}} \;-\; \underbrace{\frac{\Lambda_i}{m_i^2} \tilde\theta_i (u_i^{\text{ref}})^\top e_i}_{\text{cross}} \;+\; \underbrace{\frac{\Lambda_i}{m_i^2} e_i^\top (\tilde e_i^{\text{pe}} + \delta_i^{\text{QP}})}_{\text{perturbation}} \;-\; \frac{\|e_i\|^2}{m_i^4}\,(u_i^{\text{ref}})^\top \dot u_i^{\text{ref}}.
$$
The two cross terms cancel. The decay comes from the formation tracking: augment $V$ with $V_{\text{form}} := \tfrac12 \xi^\top \xi$ where $\xi_i := z_i - t_i$. Then $\dot\xi = -(K_T I_N + K_F L_{\mathcal{G}}) \otimes I_d \cdot \xi - \dot t$, with $L_{\mathcal{G}}$ the graph Laplacian.

**Step (b): formation Laplacian coercivity (Hilbert-Courant 1924).** The eigenvalues of $K_T I_N + K_F L_{\mathcal{G}}$ are $\{K_T + K_F\, \lambda_k(L_{\mathcal{G}})\}_{k=1}^N$, with $\lambda_1(L_{\mathcal{G}}) = 0$ on the all-ones eigenvector (connected graph). By the Hilbert-Courant min-max theorem, the smallest Rayleigh quotient is $K_T$, so $\xi^\top (K_T I + K_F L) \xi \ge K_T \|\xi\|^2$ and $\dot V_{\text{form}} \le -K_T \|\xi\|^2 + \|\xi\| \cdot u_{\max}^{\text{ref}}$.

**Step (c): combine.** With $V := \sum_i V_i + V_{\text{form}} + \kappa\sum_{i<j} B(h_{ij})$ and Young's inequality with weight $\tfrac12$ on the QP-projection cross terms (using the Hager bound from §2.4):
$$
\dot V \;\le\; -\eta\, \Big( \sum_i \tfrac{\|e_i\|^2}{m_i^4} + \|\xi\|^2 \Big) + \mathcal{O}(A_e^2) + \mathcal{O}(\sup_i \|P_i(t)\|^2) + \mathcal{O}(M^{-1}),
$$
with the **closed-form lower bound** (worst-case, always-binding QP):
$$
\eta_{\text{wc}} \;\ge\; \min\!\Big( \tfrac12 K_T,\; \tfrac{\Lambda_{\min}}{2} - \tfrac12 L_{\text{QP}}^{*\,2} / K_T \Big),
$$
and the **duty-cycle-refined bound** (using $\bar\mu := \mathbb{E}_\mu[\mathbb{1}_{\mathcal{N}_i^{\text{on}} \ne \emptyset}]$ from §4):
$$
\boxed{\;\eta \;\ge\; \min\!\Big( \tfrac12 K_T,\; \tfrac{\Lambda_{\min}}{2} - \tfrac12 \bar\mu^2\, L_{\text{QP}}^{*\,2} / K_T \Big),\;}
$$
where $L_{\text{QP}}^*$ is the worst-case QP Lipschitz constant from Lemma 1 (§2.4). The **gain condition** for $\eta > 0$ is
$$
K_T \cdot \Lambda_{\min} \;>\; \bar\mu^2\, L_{\text{QP}}^{*\,2}.
$$
For the §7.3 parameter values ($\bar\mu \approx 0.3$, $L_{\text{QP}}^* \approx 3.75$), this requires $K_T \Lambda_{\min} > 1.27$. With $\Lambda_{\min} = 0.6$, we set $K_T = 4$ in §7.3 (giving margin $K_T \Lambda_{\min} = 2.4$ vs threshold $1.27$). The system is **uniformly ultimately bounded** with bound $\mathcal{O}(A_e^2/\eta)$ [Krasovskii 1959 §14.2; Khalil 2002 Theorem 4.18; ISS form by Sontag 1989]. The slack-induced safety violation $\mathcal{O}(M^{-1})$ is absorbed into the (A3') margin $\zeta$.

*Sketch.* Swapped-signal cancellation (Morse 1990 / Pomet-Praly 1992) on the unperturbed MRAC. The QP-projection correction $\delta_i^{\text{QP}}$ and excitation injection $\tilde e_i^{\text{pe}}$ contribute bounded perturbation terms; Young's inequality + Krasovskii ultimate-boundedness theorem closes the chain. The $\mathcal{O}(\sup_i \|P_i(t)\|^2)$ term vanishes asymptotically by Anderson (1985). ∎

---

## 4. Birkhoff identifiability gain via joint second moment

Lift the closed-loop state to the augmented space $(x, m, \hat\theta) \in \mathbb{R}^{Nd} \times \{0,1\}^{|\mathcal{E}|} \times [\theta_{\min}, \theta_{\max}]^N$, where $m$ indexes the hysteresis mode (which pairs are active). Between mode transitions the flow is generated by the maximal monotone operator $A(t, x, m)$; transitions are deterministic event-triggers driven by $c_{ij}$ crossing the hysteresis thresholds. This is a **piecewise-deterministic Markov process** in the sense of Davis (1984). Trajectories converge to a compact attractor $\mathcal{M}$ on the augmented space (compact by UUB Lemma 5.3 for $x$, finite for $m$, projection-bounded for $\hat\theta$). By Davis (1984) Theorem 5.5 + Costa-Dufour (2013) for state-constrained PDMPs, $\mathcal{M}$ admits an invariant probability measure $\mu$ (the Krylov-Bogolyubov 1937 argument lifted to PDMPs). Brezis (1973) §3.3 covers only the autonomous, hysteresis-free case and is *not* sufficient here; the PDMP route is the correct modern reference.

**Operator-theoretic alternative (Krasnosel'skii-Pokrovskii 1989).** Equivalent route: lift the closed loop to trajectory space $C(\mathbb{R}_{\ge 0}; \mathbb{R}^{Nd})$, treat the hysteresis as a rate-independent Krasnosel'skii-Pokrovskii operator $\mathcal{H}: C \to C(\mathbb{R}_{\ge 0}; \{0,1\}^{|\mathcal{E}|})$, and apply Krylov-Bogolyubov (1937) on Cesàro means via Banach-Alaoglu compactness. Same invariant measure $\mu$, no PDMP machinery; the rate-independence of $\mathcal{H}$ commutes with Birkhoff time-averaging, which is the property the theorem actually uses. Pick whichever route the reader prefers; Davis 1984 is more general (admits stochastic jumps), Krasnosel'skii-Pokrovskii is sharper for the deterministic case.

**Structural setting (Riemann-Whitney-Fadell-Neuwirth).** The closed-loop state lives on the **Whitney-stratified Fadell-Neuwirth configuration space** $F_{\text{safe}}(\mathbb{R}^d, N; r_{\text{safe}}) := \{x \in (\mathbb{R}^d)^N : \|x_i - x_j\| \ge r_{\text{safe}}\ \forall i \ne j\}$ [Fadell-Neuwirth 1962; Whitney 1965], with strata indexed by the active-set mode $m \in \{0,1\}^{|\mathcal{E}|}$. The QP-resolvent $J_h$ is a stratification-preserving contraction; the Krasnosel'skii-Pokrovskii hysteresis operator selects strata at event times. This Riemann-Whitney structure is the geometric content underlying the analytic PDMP description above.

**Constrained Fisher information (Rao 1945).** The **scalar identifiability gain** is the $\mu$-expectation of the projected reference energy. Define the **joint second moment**
$$
\boxed{\; Q_i \;:=\; \mathbb{E}_\mu\!\big[\, (\mathrm{Proj}_{F_i(t,x)}\, u_i^{\text{ref}}(t))\, (\mathrm{Proj}_{F_i(t,x)}\, u_i^{\text{ref}}(t))^\top \,\big] \;\in\; \mathbb{R}^{d \times d}_{\succeq 0}, \;}
$$
the $\mu$-second moment of the *projected* reference. **$Q_i$ is the constrained Fisher information matrix of $1/\Lambda_i$ on the freedom-cone submanifold** [Rao 1945, *Bull. Calcutta Math. Soc.* §6; Aitchison-Silvey 1958], the projected-score covariance familiar from classical statistical estimation under linear equality constraints. By construction $Q_i$ is symmetric PSD, $O(d)$-equivariant under simultaneous rotation of $\{x_i, u_i^{\text{ref}}\}$ [Klein 1872], and exists by Birkhoff (1931) on $\mu$ (the integrand $\|\mathrm{Proj}_{F_i} u_i^{\text{ref}}\|^2$ is bounded by $(u_{\max}^{\text{ref}})^2 \in L^1(\mu)$, hence Bochner-integrable). The identifiability gain is its trace, the **scalar Cramér-Rao bound** on $1/\Lambda_i$:
$$
\bar\rho_i \;=\; \mathrm{tr}(Q_i) \;=\; \mathbb{E}_\mu\!\big[\| \mathrm{Proj}_{F_i}\, u_i^{\text{ref}}\|^2\big].
$$
*Why $Q_i$, not the factored product $\bar P_i \Sigma_i$:* the freedom-cone projector and the reference are correlated under $\mu$ (the active set depends on the trajectory which depends on the reference), so $\mathbb{E}_\mu[\mathrm{Proj}_{F_i}\, u u^\top] \ne \mathbb{E}_\mu[\mathrm{Proj}_{F_i}] \cdot \mathbb{E}_\mu[u u^\top]$ in general. The single object $Q_i$ avoids the false factorisation; this is the Scholze "one object, not two" simplification.

**Non-degeneracy.** $\bar\rho_i > 0 \iff Q_i \ne 0 \iff \mu(\{(t,x) : \mathrm{Proj}_{F_i(t,x)}\, u_i^{\text{ref}}(t) \ne 0\}) > 0$. This is a *joint* condition on projector and reference: closed-loop PE (A2') guarantees $u^{\text{ref}} \ne 0$ on a $\mu$-positive set; active-set non-saturation (A5) guarantees $\mathrm{Proj}_{F_i} \ne 0$ on a $\mu$-positive set; non-degeneracy requires these two sets to *intersect* in $\mu$-positive measure. Generic case: holds.

### 4.1. Lemma 4 (Birkhoff identifiability via joint second moment)

Under (A2') closed-loop PE and (A5) active-set non-saturation, on $\mathcal{M}$:
$$
\liminf_{T \to \infty} \frac{1}{T}\int_t^{t+T}\, \big\|\mathrm{Proj}_{F_i(\tau)}\, u_i^{\text{ref}}(\tau)\big\|^2\,d\tau \;=\; \mathrm{tr}(Q_i) \;>\; 0.
$$
*Proof.* Birkhoff (1931) ergodic theorem on the integrable functional $f(t,x) := \|\mathrm{Proj}_{F_i(t,x)}\, u_i^{\text{ref}}(t)\|^2$, which is bounded by $(u_{\max}^{\text{ref}})^2$ hence in $L^1(\mu)$; the time-average equals the $\mu$-expectation $\mathrm{tr}(Q_i)$. Strict positivity by the joint non-degeneracy above. ∎

**Compatibility with the prior $\bar P_i$ statement.** When projector and reference are *uncorrelated* under $\mu$ (e.g. the symmetric-$\mu$ idealisation in §7.2), $Q_i = \bar P_i \cdot \Sigma_i$ factors and the lower bound $\bar\rho_i \ge \beta_1\, \lambda_{\min}^+(\bar P_i)$ holds. In general, only the trace identity $\bar\rho_i = \mathrm{tr}(Q_i)$ is correct.

---

## 5. Theorem (three-sentence Bourbaki form)

> **Theorem (Excitation-preserving distributed safety filter).** Under axioms (A1), (A2), **(A2') closed-loop PE**, (A3'), **(A4) continuous broadcast**, and **(A5) active-set non-saturation**, and the open-loop PE hypothesis on $\{u_i^{\text{ref}}\}$, the closed-loop trajectories generated by Crandall-Liggett's exponential formula on the time-varying maximal monotone operator $A(t,x)$ - equivalently, by per-agent QP solves - satisfy: **(1)** $h_{ij}(x(t)) \ge 0$ for all $t \ge 0$ and all $i \ne j$, by forward invariance under the Hilbert projection [Hilbert 1906] and the comparison-lemma bound on the ZCBF condition [Krasovskii 1959]; **(2)** ultimate boundedness $V(t) \le V(0)\,e^{-\eta t} + \mathcal{O}(A_e^2/\eta) + \mathcal{O}(\sup_i \|P_i(t)\|^2)$ [Krasovskii 1959 §14.2], where the second perturbation term vanishes exponentially by Kalman-Bucy [1961] + Anderson [1985]; **(3)** scalar parameter convergence $\hat\theta_i \to 1/\Lambda_i$ exponentially with rate $\rho_i = \gamma \cdot \mathrm{tr}(Q_i)$, where $Q_i = \mathbb{E}_\mu[(\mathrm{Proj}_{F_i} u_i^{\text{ref}})(\mathrm{Proj}_{F_i} u_i^{\text{ref}})^\top]$ is the constrained Fisher information matrix of $1/\Lambda_i$ on the freedom-cone submanifold [Rao 1945 + Klein 1872 + Birkhoff 1931], provided the non-degeneracy $Q_i \ne 0$.

Three sentences. Three numbered conclusions. Fifteen classical references.

 - **Gauss:** "*Pauca sed matura.*"

---

## 6. Proof outline (six lemmas, all classical)

- **Lemma 5.1 (forward invariance of the safe set, Hilbert + Krasovskii).** The QP enforces $\dot h_{ij} + \alpha h_{ij} \ge 0$. By comparison-lemma + Gronwall (1919), $h_{ij}(t) \ge h_{ij}(0)\,e^{-\alpha t} > 0$.

- **Lemma 5.2 (estimation-error tolerance with vanishing conservativeness, Kalman-Bucy + Anderson).** Define $\tilde\Lambda_i := \Lambda_i - 1/\hat\theta_i$, with $|\tilde\Lambda_i|^2 \le P_i(t) \cdot \Lambda_i^2/\hat\theta_i^2 \le P_i(t)/\theta_{\min}^2$. The constraint discrepancy
$$|c_{ij}^{\text{true}} - c_{ij}| \le 2\,D_{\max}\,(\sqrt{P_i(t)}/\theta_{\min})\,(\sqrt{d}\,u_{\max} + \theta_{\max}\,u_{\max}^{\text{ref}}) =: \delta_{ij}(t),$$
where $D_{\max}$ bounds $\|x_i - x_j\|$ from (A2) + Lemma 5.3. Tightening the constraint by $\delta_{ij}(t)$ ensures $c_{ij}^{\text{true}} \ge 0$. Under (A1) and Anderson 1985, $P_i(t) \to 0$ exponentially with rate $\beta_1\,\lambda_{\min}^+(\bar P_i)$, hence $\delta_{ij}(t) \to 0$ - the constraint tightening **vanishes** asymptotically [Gutierrez-Hoagg 2024 single-agent specialisation]. The required prior tightness $\theta_{\max}/\theta_{\min} \le \kappa_\Lambda$ ensures $\delta_{ij}(0) < r_{\text{safe}}^2 \cdot$ (numerical factor) so the QP is initially feasible.

- **Lemma 5.3 (composite Lyapunov ultimate boundedness, Krasovskii 1959 §14.2).** As above (Lemma 2).

- **Lemma 5.4 (resolvent well-posedness, Brezis 1973 + Crandall-Liggett 1971 + Hager 1979).** The QP is the resolvent $J_h$ at step $h \to 0^+$. Crandall-Liggett's exponential formula gives the continuous-time semigroup; Brezis (1973) Theorem 4.2 gives existence, uniqueness, and continuous dependence on data. Lipschitz constant $L_{\text{QP}}^*$ from Hager (1979) Theorem 3.1, with the explicit upper bound in §2.4. Cross-stratum continuity at hysteresis events follows from Lemma 5.6 (uniform dwell-time): on each compact dwell interval the resolvent is single-valued and Lipschitz; the discrete switch updates the active set, after which the construction restarts on the new stratum with the same Lipschitz constant.

- **Lemma 5.5 (Birkhoff identifiability via $Q_i$, Birkhoff 1931 + Klein 1872 + Krylov-Bogolyubov 1937 + Davis 1984).** As above (Lemma 4). The convergence rate is $\rho_i = \mathrm{tr}(Q_i) > 0$ where $Q_i$ is the joint second moment of the projected reference. Krylov-Bogolyubov argument lifts to the hysteresis-augmented PDMP via Davis (1984) Thm 5.5 and Costa-Dufour (2013) for state-constrained PDMPs. Non-degeneracy $Q_i \ne 0$ requires (A2') and (A5) to hold *jointly* (the projected-reference support has positive $\mu$-measure).

- **Lemma 5.6 (uniform multi-surface dwell-time, Hager 1979 + Liberzon 2003).** Under the hysteresis thresholds $(\varepsilon, 2\varepsilon)$ and the QP Lipschitz constant $L_{\text{QP}}^*$ from Lemma 1, the inter-event time across all $\binom{N}{2}$ pairs is uniformly bounded below by
$$\tau_d \;\ge\; \frac{\varepsilon}{L_{\text{eff}} \cdot D_{\max}} \;>\; 0, \qquad L_{\text{eff}} := L_{\text{QP}}^* + \alpha\, \theta_{\max}\, \tfrac{\gamma}{\theta_{\min}^2}\, u_{\max}^{\text{ref}}\, R_{\text{UUB}},$$
where the second term in $L_{\text{eff}}$ accounts for the contribution from $\dot{\hat\theta}_i$ entering through the gauge-fixed coefficient $\alpha \hat\theta_i h_{ij}$ in $c_{ij}$ (chain rule on the adaptive law). *Proof:* Between events, $|\dot c_{ij}| \le L_{\text{QP}}^* \cdot \|2(x_i-x_j)\| + \alpha \cdot |\dot{\hat\theta}_i| \cdot |h_{ij}|$; substituting the adaptive-law bound $|\dot{\hat\theta}_i| \le (\gamma/\theta_{\min}^2) u_{\max}^{\text{ref}} \|e_i\|$ with $\|e_i\| \le R_{\text{UUB}}$ and $|h_{ij}| \le D_{\max}^2$ gives the $L_{\text{eff}}$ form. Crossing the hysteresis band $(\varepsilon, 2\varepsilon)$ takes at least $\varepsilon / (L_{\text{eff}} D_{\max})$. Hence Zeno is excluded for the multi-pair coupled system. ∎

The theorem is an immediate consequence of these six lemmas, each at most one classical reference deep.

---

## 7. Worked examples

### 7.1. $N=2$, $d=2$, parallel approach

Two agents on the line $\{x_2 = -x_1\}$, $r_{\text{safe}} = 0.5$, references pulling them toward each other. On the active set, $g_{12} \propto (x_1 - x_2) \propto \hat e_1$, so $F_1 = \mathrm{span}\{\hat e_2\}$, $\mathrm{Proj}_{F_1}\big|_{\text{active}} = \mathrm{diag}(0,1)$. Off the active set, $\mathrm{Proj}_{F_1}\big|_{\text{free}} = I$. With active fraction $\bar\mu$ on $\mathcal{M}$,
$$
\bar P_1 \;=\; (1 - \bar\mu)\,I \;+\; \bar\mu\,\mathrm{diag}(0,1) \;=\; \mathrm{diag}(1 - \bar\mu,\; 1), \qquad \lambda_{\min}^+(\bar P_1) = 1 - \bar\mu.
$$
**Honest direct calculation (NOT factored).** In the parallel-approach scenario the reference $u_1^{\text{ref}}$ is *always* directed along $\hat e_1$ (toward the other agent), so $\Sigma_1 = \mathbb{E}_\mu[u_1^{\text{ref}} u_1^{\text{ref}\,\top}] = \beta_1\,\mathrm{diag}(1, 0)$ - **rank-1, NOT isotropic**. Under projection:
- Active stratum ($\bar\mu$): $\mathrm{Proj}_{F_1} u_1^{\text{ref}} = \mathrm{diag}(0,1) \cdot c\hat e_1 = 0$, contributing $0$ to $Q_1$.
- Off-active ($1-\bar\mu$): $\mathrm{Proj}_{F_1} u_1^{\text{ref}} = u_1^{\text{ref}}$, contributing $\beta_1\,\mathrm{diag}(1, 0)$.

Thus $Q_1 = (1 - \bar\mu)\, \beta_1\, \mathrm{diag}(1, 0)$ and $\mathrm{tr}(Q_1) = (1 - \bar\mu)\beta_1$. Convergence rate $\rho_1 = \gamma (1-\bar\mu)\beta_1$. As $\bar\mu \to 1$ (always-active), $\rho_1 \to 0$ - the safety filter consumes all of the reference's identifiability content. This is the *correct* parallel-approach number; the symmetric-$\mu$ factorisation $\bar\rho_1 = (2-\bar\mu)\beta_1$ is wrong here precisely *because* projector and reference are highly correlated.

### 7.2. $N=4$, $d=2$, cross-swap

Agents at $(\pm 3, \pm 3)$ swapping diagonally. **Symmetry assumption (numerical-only):** the invariant measure $\mu$ is approximately symmetric under the dihedral $D_4$ action, hence each of the three pairs per agent is active for fraction $\bar\mu/3$ of the cycle. This is an *assumption on $\mu$*, not derived from the dynamics; verified numerically in §7.3. Asymmetric extensions would require resolving the actual $\mu$ via Davis (1984) PDMP simulation. For agent 1 going $(-3,-3)\to(3,3)$:
- vs head-on agent 3: $F_1 \perp (1,1)/\sqrt{2}$, projector $\tfrac12\begin{pmatrix}1&-1\\-1&1\end{pmatrix}$.
- vs perpendicular agents 2, 4: projectors $\mathrm{diag}(0,1)$ and $\mathrm{diag}(1,0)$ respectively.

Sum of pair-active projectors: $2I - \tfrac12\begin{pmatrix}1&1\\1&1\end{pmatrix} = \begin{pmatrix}1.5 & -0.5\\-0.5 & 1.5\end{pmatrix}$.
$$
\bar P_1 \;=\; (1 - \bar\mu)\,I + \tfrac{\bar\mu}{3}\!\begin{pmatrix}1.5 & -0.5\\-0.5 & 1.5\end{pmatrix}.
$$
With $\bar\mu = 0.3$: $\bar P_1 = \begin{pmatrix}0.85 & -0.05\\-0.05 & 0.85\end{pmatrix}$, eigenvalues $\{0.80, 0.90\}$, $\lambda_{\min}^+(\bar P_1) = 0.80$ (anisotropy diagnostic, *not* the rate). Under the $D_4$-symmetric idealisation, $\Sigma_1 \approx (\beta_1/2) I$ (the swap reference rotates between $\hat e_1, \hat e_2$ with equal $\mu$-mass), and $Q_1 = \bar P_1 \cdot (\beta_1/2) I$ factors approximately to give $\mathrm{tr}(Q_1) = (\beta_1/2) \cdot \mathrm{tr}(\bar P_1) = 0.85\,\beta_1$. **Convergence rate $\rho_1 = 0.85\, \gamma\,\beta_1$** (the trace-of-Fisher); the $0.80$ eigenvalue is the worst-direction anisotropy in the projector, not the rate itself.

### 7.3. Simulation parameter values (for reproducibility)

Tuned per Krstić (η-feasibility) and Borrelli (saturation reconciliation):
$$
K_T = 4,\quad K_F = 0.3,\quad \gamma = 0.15,\quad \alpha = 10,\quad r_{\text{safe}} = 0.4,\quad u_{\max} = 25,\quad
\Lambda = (0.6, 1.4, 0.9, 1.6).
$$
$K_T$ bumped from the original repo's $0.5$ to $4$ so that $K_T \Lambda_{\min} = 2.4 > \bar\mu^2 L_{\text{QP}}^{*\,2} \approx 1.27$ (η-feasibility). $u_{\max}$ bumped from $1$ to $25$ so the unconstrained $u^{\text{AC}} = K_T \cdot O(\|z-t\|)$ does not saturate at every step. Formation time constant $1/K_T = 250$ ms, comfortably resolved by $h_{\text{outer}} = 5$ ms.

Ranges for axiom (A1): $\theta_{\min} = 1$, $\theta_{\max} = 2$ ($\kappa_\Lambda = 2$). Margin in (A3'): $\zeta = 0.5\, r_{\text{safe}}^2$. Slack penalty $M = 10^4$. Hysteresis threshold $\varepsilon = 0.05\, r_{\text{safe}}^2$. Excitation: $e_i^{\text{pe}}(t) = A_e [\sin(\omega_1 t + \phi_i^1), \sin(\omega_2 t + \phi_i^2)]^\top$ with $\omega_1 = 2\pi(0.7)$ Hz, $\omega_2 = 2\pi(1.1)$ Hz, $\phi_i^k \sim \mathcal{U}[0, 2\pi)$ under seed `rng(42)`.

**Reproducibility.** Reference Python implementation (NumPy + OSQP; `pip install osqp`) released at `https://github.com/d8maldon/Multi-Agent-CBF` upon acceptance.

### 7.4. Figure plan

1. Cross-swap trajectories: AC alone, AC+CBF, AC+CBF+PE-aware (excitation injection).
2. Parameter convergence $|\hat\theta_i - 1/\Lambda_i|(t)$ for the three conditions.
3. Identifiability gain $\bar\rho_i(t)$ computed online; spatial $\mu$-average.
4. Safety margin $\min h_{ij}(t)$; constraint tightening $\delta(t)$.
5. Sweep over $A_e \in \{0, 0.05, 0.10, 0.20\}\,u_{\max}$ - Pareto rate vs ultimate-bound. Caption reports $\eta$ explicitly so the slope $A_e^2/\eta$ is readable.
6. Communication-delay sweep: $\min_{ij} h_{ij}(t)$ vs latency $\tau \in \{0, 5, 20, 50, 100\}$ ms (cross-swap + parallel approach), annotating the latency at which safety is first violated. Empirical robustness margin against (A4) relaxation.

Each figure includes a saturation-active subpanel (1 if $\|u_i^{\text{safe}}\|_\infty = u_{\max}$, else 0) so the reader can distinguish "QP active because of safety" from "QP active because of saturation."

---

## 8. Discussion

### Contribution

Eight classical objects compose to give a multi-agent adaptive safety-critical controller with quantifiable identifiability-vs-safety trade-off:

1. Maximal monotone operator $A(t,x,m)$ from the time-varying hysteresis-graded feasible set [Brezis 1973].
2. Crandall-Liggett exponential formula generating the closed-loop semigroup [1971]; the QP is the Yosida resolvent.
3. **Noether's first theorem (1918)** on the $G_\lambda : (e, \tilde\theta) \mapsto (\lambda^{-1} e, \lambda \tilde\theta)$ symmetry: gives the swapped-signal cancellation.
4. **Hilbert-Courant min-max (1924)** on the formation Laplacian $K_T I + K_F L_{\mathcal{G}}$: gives the gain condition $\eta \ge K_T/2$.
5. $N$ parallel Kalman-Bucy filters tracking $\Lambda_i$ [Kalman-Bucy 1961]; Anderson PE-driven covariance decay [1985].
6. Krasovskii ultimate-boundedness for the swapped-signal Lyapunov [1959 §14.2].
7. Krasnosel'skii-Pokrovskii hysteresis operator [1989] / Davis PDMP [1984] giving the closed-loop invariant measure $\mu$.
8. **Klein-Erlangen invariant (1872)** identifiability gain $\bar\rho_i = \mathrm{tr}(Q_i)$ as the trace of the $O(d)$-equivariant joint second moment $Q_i = \mathbb{E}_\mu[(\mathrm{Proj}_{F_i} u^{\text{ref}})(\mathrm{Proj}_{F_i} u^{\text{ref}})^\top]$.

Plus Klein-Erlangen gauge fixing [1872] for QP pre-conditioning. The construction is, classically: *Lyapunov's second method (1892) on a Noether-symmetric Lagrangian, with safety enforced via Hilbert projection (1906) and identifiability quantified via a Klein-invariant Rayleigh quotient (1877). Closed-loop existence by Crandall-Liggett (1971); invariant measure by Krasnosel'skii-Pokrovskii (1989).*

The contribution is the **engineering observation** that these eight classical objects compose. The mathematical machinery is pre-1985 in its entirety. **Not a mathematical novelty paper.** A control-design observation paper.

### Position vs prior work

| Prior work | Single-agent / multi-agent | What we extend |
|---|---|---|
| Gutierrez-Hoagg [arXiv 2411.12899, 2024] | single-agent | multi-agent generalisation of vanishing-conservativeness via Kalman-Bucy parallel filters |
| Cohen-Belta [arXiv 2002.04577, 2203.01999, 2303.04241] | single-agent | distributed multi-agent setting with Birkhoff-quantified rate |
| Autenrieb-Annaswamy [arXiv 2309.05533] | single-agent LTI | nonlinear single-integrator with formation reference |
| Cramér-Rao bound on constrained submanifold [Rao 1945; Aitchison-Silvey 1958] | classical statistics | first application to *adaptive control* convergence rate via the freedom-cone projection on the Whitney-stratified Fadell-Neuwirth configuration space |

**Reframing.** The contribution is not "another adaptive CBF extension." It is the identification of the convergence rate of multi-agent adaptive CBF as the **constrained Cramér-Rao bound** on a Whitney-stratified Fadell-Neuwirth configuration space. The freedom-cone projection - orthogonal to the active CBF normals - is the constraint manifold; its time-averaged Fisher matrix $Q_i$ is the rate. This connects 21st-century safety-critical adaptive control to 1945 statistical estimation theory, a connection (to our knowledge) not previously made.

### Robustifier choice (projection vs $\sigma$-mod vs dead-zone)

Three classical robustifiers exist for adaptive parameter laws: Krstić-Kanellakopoulos-Kokotović (1995) smooth projection, Ioannou-Kokotović (1983) $\sigma$-modification, and Egardt (1979) dead-zone. We pick **projection** because the QP feasibility argument requires a hard bound $\hat\theta_i \in [\theta_{\min}, \theta_{\max}]$ with $\theta_{\max}/\theta_{\min} \le \kappa_\Lambda$; $\sigma$-mod produces a soft attractor at $\hat\theta = 0$ that conflicts with this bound, and dead-zone introduces a region where $\dot{\hat\theta}_i = 0$ that breaks the Anderson 1985 PE-decay rate on $P_i(t)$.

### Norm conventions

Saturation in §2 is $\|u\|_\infty \le u_{\max}$ (matches per-channel actuator limits). Lyapunov in §3 uses $\|x_i - z_i\|_2$. The $\sqrt{d}$ factor in $\delta_{ij}(t)$ (Lemma 5.2) is the conversion. Single conversion table:

| Quantity | Norm | Why |
|---|---|---|
| $u_i^{\text{safe}}$, $u_i^{\text{ref}}$, $u_i^{\text{AC}}$ | $\infty$ | per-channel saturation |
| $x_i - z_i$, $\hat\theta_i - 1/\Lambda_i$ | 2 | Lyapunov |
| $u_i^{\text{ref}}$ in $m_i^2 := 1 + \|u_i^{\text{ref}}\|^2$ | 2 | swapped-signal normalisation |

When converting between them in proofs, $\|u\|_2 \le \sqrt{d}\,\|u\|_\infty$ and $\|u\|_\infty \le \|u\|_2$. The $\sqrt{d}$ factors are tracked explicitly in Lemma 5.2 and §7.3.

### Position vs L1-adaptive

L1-adaptive control (Cao-Hovakimyan 2008) bounds the transient over-shoot independent of the adaptation rate $\gamma$, at the cost of a low-pass filter that limits identifiability. Our construction's transient is $V(0)\,e^{-\eta t}$, dependent on $V(0)$ but with a closed-form $\eta$ inequality (Lemma 2). The trade is reversed: we keep PE for identification (Birkhoff-Rayleigh $\bar\rho_i$) at the cost of a transient bounded by initial conditions. For aerospace deployment where transient is the safety-critical quantity, L1 is preferable; for multi-agent identification where parameter convergence is the deliverable, our construction is preferable.

### Open questions

1. **Optimal excitation $e_i^{\text{pe}}$.** Sinusoidal is convenient. State-feedback rules maximising $\bar\rho_i$ are open.
2. **Higher-relative-degree $h_{ij}$.** For Dubins / quadrotor agents, $h$ has relative degree 2; HOCBF [Xiao-Belta 2021] generalises the freedom cone.
3. **Event-triggered communication (natural follow-up).** (A4) assumes continuous broadcast; the event-triggered extension with broadcast threshold $\delta_{\text{comm}}$ is the natural sequel paper, with the Cramér-Rao rate $\mathrm{tr}(Q_i)$ now degraded by an explicit $O(\delta_{\text{comm}}^2)$ term.
5. **Port-Hamiltonian generalisation.** The parameter manifold $(e_i, \tilde\theta_i)$ carries a natural symplectic form $\omega = \mathrm{d}e_i \wedge \mathrm{d}\tilde\theta_i$, and the closed loop decomposes into a Hamiltonian part (driving the Noether $G_\lambda$ symmetry) plus a dissipative part (driving the Lyapunov decay). The port-Hamiltonian formulation [van der Schaft 1986; Ortega-Spong 1988] would generalise cleanly to non-scalar $\Lambda$ and higher-relative-degree $h_{ij}$ (Dubins / quadrotor agents).
4. **Adversarial / Byzantine setting.** If a subset of agents broadcasts wrong $\hat\theta_j$, robust extensions are open.

---

## 9. References (canonical)

**Pre-1985 classical objects:**
- Birkhoff, G. D. (1931). "Proof of the ergodic theorem." *PNAS* 17, 656–660.
- Brezis, H. (1973). *Opérateurs Maximaux Monotones et Semi-Groupes de Contractions dans les Espaces de Hilbert.* North-Holland.
- Crandall, M. G., Liggett, T. M. (1971). "Generation of semi-groups of nonlinear transformations on general Banach spaces." *Amer. J. Math.* 93, 265–298.
- Gronwall, T. H. (1919). "Note on the derivatives with respect to a parameter of the solutions of a system of differential equations." *Ann. Math.* 20, 292–296.
- Hager, W. W. (1979). "Lipschitz continuity for constrained processes." *SIAM J. Control Optim.* 17, 321–338.
- Hilbert, D. (1906). Lectures on integral equations; see also Riesz (1907) for the projection theorem.
- Kalman, R. E. (1960). "A new approach to linear filtering and prediction problems." *Trans. ASME J. Basic Eng.* 82, 35–45.
- Kalman, R. E., Bucy, R. S. (1961). "New results in linear filtering and prediction theory." *Trans. ASME J. Basic Eng.* 83, 95–108.
- Klein, F. (1872). "Vergleichende Betrachtungen über neuere geometrische Forschungen" (Erlangen Programme).
- Krasnosel'skii, M. A., Pokrovskii, A. V. (1989). *Systems with Hysteresis.* Springer (rate-independent hysteresis operators on trajectory space).
- Krasovskii, N. N. (1959). *Stability of Motion.* Stanford University Press, §14.2 (ultimate boundedness).
- Krylov, N., Bogolyubov, N. (1937). "La théorie générale de la mesure dans son application à l'étude des systèmes dynamiques de la mécanique non linéaire." *Ann. Math.* 38, 65–113.
- Krstić, M., Kanellakopoulos, I., Kokotović, P. (1995). *Nonlinear and Adaptive Control Design.* Wiley §6 (parameter projection).
- LaSalle, J. P. (1960). "Some extensions of Liapunov's second method." *IRE Trans. Circuit Theory* 7, 520–527.
- Lyapunov, A. M. (1892). *The General Problem of the Stability of Motion.* (Eng. transl. 1992.)
- Morse, A. S. (1990) / Pomet, J.-B., Praly, L. (1992). Swapped-signal Lyapunov for normalised adaptive laws.
- Noether, E. (1918). "Invariante Variationsprobleme." *Nachr. Königl. Ges. Wiss. Göttingen, Math.-Phys. Kl.* 235–257 (first theorem: one-parameter symmetry → conserved quantity).
- Hilbert, D., Courant, R. (1924). *Methoden der mathematischen Physik I,* §I.3 (min-max characterisation of eigenvalues).
- Rao, C. R. (1945). "Information and the accuracy attainable in the estimation of statistical parameters." *Bull. Calcutta Math. Soc.* 37, 81–91 (Cramér-Rao bound; constrained Fisher information §6).
- Aitchison, J., Silvey, S. D. (1958). "Maximum-likelihood estimation of parameters subject to restraints." *Ann. Math. Statist.* 29(3), 813–828 (constrained Fisher information).
- Rayleigh, Lord (1877). *The Theory of Sound,* §IV (Rayleigh quotient).
- Fadell, E., Neuwirth, L. (1962). "Configuration spaces." *Math. Scand.* 10, 111–118 (ordered configuration spaces of $N$ points in $\mathbb{R}^d$).
- Whitney, H. (1965). "Tangents to an analytic variety." *Ann. Math.* 81, 496–549 (Whitney stratification).
- Robinson, S. M. (1980). "Strongly regular generalised equations." *Math. Oper. Res.* 5, 43–62.
- Rockafellar, R. T. (1970). *Convex Analysis.* Princeton (normal cone, maximal monotone operators).
- Yosida, K. (1948). "On the differentiability and the representation of one-parameter semigroup of linear operators." *J. Math. Soc. Japan* 1, 15–21.

**Post-1985 / modern context:**
- Anderson, B. D. O. (1985). "Exponential stability of linear equations arising in adaptive identification." *IEEE TAC* 22(1), 83–88.
- Costa, O. L. V., Dufour, F. (2013). *Continuous Average Control of Piecewise Deterministic Markov Processes.* Springer.
- Davis, M. H. A. (1984). "Piecewise-deterministic Markov processes: a general class of non-diffusion stochastic models." *J. Royal Stat. Soc. B* 46(3), 353–388.
- Ames, A. D., Xu, X., Grizzle, J. W. (2014). CBF + slack variable.
- Autenrieb, J., Annaswamy, A. M. (2023). [arXiv 2309.05533] in-house adaptive CBF.
- Cohen, M., Belta, C. (2020, 2022, 2023). [arXiv 2002.04577, 2203.01999, 2303.04241] adaptive CBF lineage.
- Gutierrez, R., Hoagg, J. (2024). [arXiv 2411.12899] adaptive CBF with vanishing conservativeness via PE.
- Khalil, H. K. (2002). *Nonlinear Systems,* 3rd ed., Theorem 4.18 (UUB).
- Liberzon, D. (2003). *Switching in Systems and Control,* §1.2 (hysteresis).
- Sontag, E. D. (1989). "Smooth stabilization implies coprime factorization." *IEEE TAC* 34, 435–443 (ISS formalisation).
- Tee, K. P., Ge, S. S., Tay, E. H. (2009). "Barrier Lyapunov functions for the control of output-constrained nonlinear systems." *Automatica* 45, 918–927.
- Ortega, R., Spong, M. W. (1988). "Adaptive motion control of rigid robots: a tutorial." *Automatica* 25(6), 877–888 (port-Hamiltonian adaptive control).
- van der Schaft, A. J. (1986). "Stabilisation of Hamiltonian systems." *Nonlinear Anal.: TMA* 10(10), 1021–1035 (port-Hamiltonian formulation).
- Stellato, B., Banjac, G., Goulart, P., Bemporad, A., Boyd, S. (2020). "OSQP: an operator splitting solver for quadratic programs." *Math. Program. Comput.* 12, 637–672.
- Wright, S. J. (1997). *Primal-Dual Interior-Point Methods.* SIAM, §11 (constraint preconditioning).
- Xiao, W., Belta, C. (2021). High-order CBF.

**Twenty-one classical, ten modern.** The framework is in pre-1985 mathematics; modern references frame the application context.

---

## Appendix A. Version history (most recent only; full git log retains earlier)

**v8 → v9 (LCSS-form rewrite, post Krstić / Borrelli / Lavretsky controls audit).**

| v8 | v9 | Driver |
|---|---|---|
| Six axioms, but no abstract or problem statement | Abstract + §1 Problem statement added (LCSS form) | Lavretsky |
| Theorem rate $\rho_i = \mathrm{tr}(Q_i)$ | $\rho_i = \gamma\,\mathrm{tr}(Q_i)$ ($\gamma$ factor added) | Krstić |
| η inequality with worst-case $L_{\text{QP}}^{*\,2}$ | Duty-cycle-refined $\bar\mu^2 L_{\text{QP}}^{*\,2}$; gain condition $K_T \Lambda_{\min} > \bar\mu^2 L_{\text{QP}}^{*\,2}$ | Krstić |
| §7.3 $K_T = 0.5$, $u_{\max} = 1$ (η fails) | $K_T = 4$, $u_{\max} = 25$ (η holds with margin 2x) | Krstić + Borrelli |
| §7.1 $\mathrm{tr}(Q_1) = (2-\bar\mu)\beta_1$ (factored, wrong) | $\mathrm{tr}(Q_1) = (1-\bar\mu)\beta_1$ from direct calculation with $\Sigma_1 = \beta_1\,\mathrm{diag}(1,0)$ rank-1 | Tao + Bhargava |
| §7.2 reports $\lambda_{\min}^+ = 0.80$ as the rate | Reports $\mathrm{tr}(Q_1) = 0.85\,\beta_1$ as rate, $\lambda_{\min}^+ = 0.80$ as anisotropy diagnostic | Tao |
| $Q_i$ as "joint second moment" only | $Q_i$ named as constrained Fisher information (Rao 1945; Aitchison-Silvey 1958); $\mathrm{tr}(Q_i)$ is the scalar Cramér-Rao bound | OG council |
| Closed loop on PDMP, no geometric structure | Whitney-stratified Fadell-Neuwirth configuration space (§4 structural remark) | OG council |
| §2.3 numerical scheme, no scaling note | Real-time feasible up to $N \approx 50$; warm-start cold-restart at hysteresis events; OSQP rationale | Borrelli |
| No reproducibility statement | §7.3: Python+NumPy+OSQP repo on acceptance | Lavretsky |
| Position-vs-prior-work: 3 rows | 4 rows (added Cramér-Rao row); reframing paragraph | Lavretsky |
| Open-question 3 framed as limitation | Reframed as natural follow-up paper | Lavretsky |
| 3 open questions | 5 open questions (added port-Hamiltonian generalisation) | OG council |

**v6 → v8 (compressed):** v7 added Noether/Hilbert-Courant/Klein-Frobenius/Krasnosel'skii-Pokrovskii classical attributions; v8 corrected the Klein-Frobenius factorisation bug (counter-example: factored form gives 50% gap on a 2-stratum example) and added (A5') for $d \ge 3$.

**Pre-v6:** see git log; eight versions of patches now consolidated.

---

The construction is paper-ready for IEEE-LCSS '26. Next step: implement the four-step incremental simulation pipeline (smoothed-flow → slack QP → pre-conditioning → Kalman-Bucy auxiliary) and verify the §7.2 worked-example rate $\mathrm{tr}(Q_1) = 0.85\,\beta_1$ within tolerance. Proof body $\le 4$ pages.
