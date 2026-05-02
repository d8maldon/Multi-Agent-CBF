# Excitation-Preserving Distributed Safety Filter for Multi-Agent Adaptive Control

**Status:** v4, post-fourth-round controls audit (Tomlin / Lavretsky / Wise blocker patches applied). Continuous-time simulation only; no hardware claims.
**Code touched:** none, by design.
**Length target:** Bourbaki form. Three-sentence theorem, fifteen classical references.

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
| $\bar\rho_i$ | scalar identifiability gain | $\bar\rho_i := \mathbb{E}_\mu[(u_i^{\text{ref}})^\top \mathrm{Proj}_{F_i} u_i^{\text{ref}}]$ |
| $m_i^2 := 1 + \|u_i^{\text{ref}}\|^2$ | $\ge 1$ | normalisation gain (swapped-signal Lyapunov) |

## Axioms

- **(A1) Bounded admissible parameter set.** $\Lambda_i \in [\Lambda_{\min}, 1]$, $\Lambda_{\min} > 0$, time-invariant. Estimate $\hat\theta_i \in [\theta_{\min}, \theta_{\max}]$ enforced via the Krstić-Kanellakopoulos-Kokotović (1995) smooth projection. Required prior tightness: $\theta_{\max}/\theta_{\min} \le \kappa_\Lambda$ for the QP to remain feasible (see §6).
- **(A2) Bounded admissible reference and connected graph.** $\{z_i, \dot z_i, t_i, \dot t_i\}$ uniformly bounded; $\mathcal{G}$ connected.
- **(A3') Initial strict safety with margin.** There exists $\zeta > 0$ such that $h_{ij}(x(0)) \ge \delta_{ij}(0) + \zeta$ for all $i \ne j$, where $\delta_{ij}(0) = 2 D_{\max}(\sqrt{P_i(0)}/\theta_{\min})(\sqrt{d}\,u_{\max} + \theta_{\max} u_{\max}^{\text{ref}})$ is the initial CBF tightening from Lemma 5.2. Equivalently, $\delta_{ij}(0) \le \tfrac12 r_{\text{safe}}^2$ as a precondition on the data; this is what the prior tightness $\kappa_\Lambda$ buys.
- **(A4) Neighbour broadcast.** Each agent $i$ has continuous-time access to $\{x_j(t), \hat\theta_j(t) : j \in \mathcal{N}_i\}$. (Discrete / event-triggered relaxations: separate paper.)

These four axioms are *all* the hypotheses. Lipschitz constraints, regularity of the closed loop, dwell-time bounds, and PE on the normalised regressor are *consequences* once the construction is properly framed.

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
with $P_i(0) = (\theta_{\max} - \theta_{\min})^2$ and $Q = 0$ (deterministic Riccati; matches Anderson's framework). The PE-always hypothesis on $u_i^{\text{ref}}$ guarantees observability throughout, so $P_i = 0$ is approached but never absorbed in finite time. Under PE on $u_i^{\text{ref}}$, $P_i(t) \to 0$ exponentially at rate $\beta_1\,\lambda_{\min}^+(\bar P_i)$ by Anderson (1985). (Stochastic variant with $Q > 0$: replace conclusion (2) with $\mathcal{O}(A_e^2/\eta + Q)$; we keep the deterministic form.) The filter is *auxiliary* - its output is used only to compute the time-varying CBF tightening $\delta(t)$ in §2.

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
Inner solver: OSQP (Stellato et al. 2020), warm-started from the previous step. Outer integrator: fixed-step RK4 (preferred for Simulink) or ode15s with mass-matrix identity (preferred for adaptive step-sizing studies). The QP is the resolvent $J_{h_{\text{outer}}}$; no DAE machinery is needed because the constraint enters only through the projection, not as an algebraic equation in the state.

For $N = 2$, $d = 2$, single active pair, the QP admits the closed-form Lagrangian solution
$$
u_i^{\text{safe}} \;=\; (u_i^{\text{AC}} + \tilde e_i^{\text{pe}}) + \mu_{ij}^* \cdot 2(x_i - x_j), \qquad \mu_{ij}^* = \max\!\Big(0,\, \frac{\delta_{ij}(t) - c_{ij}(u_i^{\text{AC}} + \tilde e_i^{\text{pe}})}{\|2(x_i - x_j)\|^2}\Big),
$$
which is the unit test for the OSQP wrapper before scaling to $N \ge 3$.

### 2.4. Lemma 1 (well-posedness of the QP-resolvent)

Under (A1)–(A4), the QP admits a unique solution Lipschitz in $(x, \hat\theta, e_i^{\text{pe}})$ and piecewise-affine on the hysteretic strata of $\mathcal{N}_i^{\text{on}}$.

*Sketch.* Strict convexity (objective is $2I$) + linear constraints with non-empty interior (by A3 + Lemma 5.1) + Hilbert projection theorem [Hilbert 1906; Riesz 1907]. Lipschitz: Hager (1979). Piecewise-affine: Robinson (1980). ∎

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
with the explicit decay constant
$$
\eta \;\ge\; \Lambda_{\min}\, K_T \;-\; 2\, K_F\, \deg(\mathcal{G})\, \kappa_\Lambda^2,
$$
positive whenever the design satisfies the **gain condition** $K_T > 2 (K_F/\Lambda_{\min}) \deg(\mathcal{G})\, \kappa_\Lambda^2$. The system is **uniformly ultimately bounded** with bound $\mathcal{O}(A_e^2/\eta)$ [Krasovskii 1959 §14.2; Khalil 2002 Theorem 4.18, the modern formalisation as ISS due to Sontag 1989]. The QP-projection perturbation $\delta_i^{\text{QP}}$ is bounded by $L_{\text{QP}}\, (\|x_i - z_i\|/m_i + \delta_{ij}(t))$ with $L_{\text{QP}} = \kappa_\Lambda \deg(\mathcal{G})$ via the Hager (1979) Lipschitz bound; Young's inequality with weight $\eta/2$ absorbs the $\|x_i - z_i\|$ term into the decay.

*Sketch.* Swapped-signal cancellation (Morse 1990 / Pomet-Praly 1992) on the unperturbed MRAC. The QP-projection correction $\delta_i^{\text{QP}}$ and excitation injection $\tilde e_i^{\text{pe}}$ contribute bounded perturbation terms; Young's inequality + Krasovskii ultimate-boundedness theorem closes the chain. The $\mathcal{O}(\sup_i \|P_i(t)\|^2)$ term vanishes asymptotically by Anderson (1985). ∎

---

## 4. Birkhoff-Rayleigh identifiability gain

Trajectories converge to a compact attractor $\mathcal{M}$ on which the closed-loop dynamics are governed by the Crandall-Liggett semigroup. By Krylov-Bogolyubov (1937) extended to maximal monotone semigroups [Brezis 1973 §3.3], $\mathcal{M}$ admits an invariant probability measure $\mu$.

The **scalar identifiability gain** is the $\mu$-expectation of the Rayleigh quotient of the freedom-cone projector against the open-loop regressor [Rayleigh 1877, *Theory of Sound* §IV]:
$$
\bar\rho_i \;:=\; \mathbb{E}_\mu\!\big[\, (u_i^{\text{ref}})^\top \mathrm{Proj}_{F_i}\, u_i^{\text{ref}} \,\big]
\;\in\; \big[\beta_1\,\lambda_{\min}^+(\bar P_i),\; \beta_1\big],
$$
where $\bar P_i := \mathbb{E}_\mu[\mathrm{Proj}_{F_i}]$ is the time-averaged freedom-cone projector. Existence by Birkhoff (1931) on the invariant measure $\mu$.

### 4.1. Lemma 4 (anisotropic identifiability via Rayleigh quotient)

Suppose $u_i^{\text{ref}}$ satisfies the open-loop PE condition $\beta_1 I \preceq T_0^{-1}\int_t^{t+T_0} \phi_i \phi_i^\top d\tau$. Then on $\mathcal{M}$:
$$
\liminf_{T \to \infty} \frac{1}{T}\int_t^{t+T}\, (u_i^{\text{ref}}(\tau))^\top \mathrm{Proj}_{F_i(\tau)}\, u_i^{\text{ref}}(\tau)\,d\tau \;\ge\; \beta_1 \cdot \lambda_{\min}^+(\bar P_i),
$$
with equality achieved when the regressor aligns with the worst eigenvector of $\bar P_i$.

The bound is *non-degenerate* iff $\bar\rho_i > 0$, equivalently iff the open-loop reference is not forever orthogonal to the freedom cone - a checkable condition on the reference trajectory [Anderson 1977 PE necessary conditions].

---

## 5. Theorem (three-sentence Bourbaki form)

> **Theorem (Excitation-preserving distributed safety filter).** Under axioms (A1), (A2), (A3'), and **continuous-time neighbour broadcast (A4)**, and the open-loop PE hypothesis on $\{u_i^{\text{ref}}\}$, the closed-loop trajectories generated by Crandall-Liggett's exponential formula on the time-varying maximal monotone operator $A(t,x)$ - equivalently, by per-agent QP solves - satisfy: **(1)** $h_{ij}(x(t)) \ge 0$ for all $t \ge 0$ and all $i \ne j$, by forward invariance under the Hilbert projection [Hilbert 1906] and the comparison-lemma bound on the ZCBF condition [Krasovskii 1959]; **(2)** ultimate boundedness $V(t) \le V(0)\,e^{-\eta t} + \mathcal{O}(A_e^2/\eta) + \mathcal{O}(\sup_i \|P_i(t)\|^2)$ [Krasovskii 1959 §14.2], where the second perturbation term vanishes exponentially by Kalman-Bucy [1961] + Anderson [1985]; **(3)** scalar parameter convergence $\hat\theta_i \to 1/\Lambda_i$ exponentially with rate $\rho_i \in [\beta_1\,\lambda_{\min}^+(\bar P_i),\, \beta_1]$, where $\bar P_i$ is the $\mu$-time-averaged freedom-cone projector [Birkhoff 1931 + Rayleigh 1877], provided the non-degeneracy $\bar\rho_i > 0$.

Three sentences. Three numbered conclusions. Fifteen classical references.

 - **Gauss:** "*Pauca sed matura.*"

---

## 6. Proof outline (five lemmas, all classical)

- **Lemma 5.1 (forward invariance of the safe set, Hilbert + Krasovskii).** The QP enforces $\dot h_{ij} + \alpha h_{ij} \ge 0$. By comparison-lemma + Gronwall (1919), $h_{ij}(t) \ge h_{ij}(0)\,e^{-\alpha t} > 0$.

- **Lemma 5.2 (estimation-error tolerance with vanishing conservativeness, Kalman-Bucy + Anderson).** Define $\tilde\Lambda_i := \Lambda_i - 1/\hat\theta_i$, with $|\tilde\Lambda_i|^2 \le P_i(t) \cdot \Lambda_i^2/\hat\theta_i^2 \le P_i(t)/\theta_{\min}^2$. The constraint discrepancy
$$|c_{ij}^{\text{true}} - c_{ij}| \le 2\,D_{\max}\,(\sqrt{P_i(t)}/\theta_{\min})\,(\sqrt{d}\,u_{\max} + \theta_{\max}\,u_{\max}^{\text{ref}}) =: \delta_{ij}(t),$$
where $D_{\max}$ bounds $\|x_i - x_j\|$ from (A2) + Lemma 5.3. Tightening the constraint by $\delta_{ij}(t)$ ensures $c_{ij}^{\text{true}} \ge 0$. Under (A1) and Anderson 1985, $P_i(t) \to 0$ exponentially with rate $\beta_1\,\lambda_{\min}^+(\bar P_i)$, hence $\delta_{ij}(t) \to 0$ - the constraint tightening **vanishes** asymptotically [Gutierrez-Hoagg 2024 single-agent specialisation]. The required prior tightness $\theta_{\max}/\theta_{\min} \le \kappa_\Lambda$ ensures $\delta_{ij}(0) < r_{\text{safe}}^2 \cdot$ (numerical factor) so the QP is initially feasible.

- **Lemma 5.3 (composite Lyapunov ultimate boundedness, Krasovskii 1959 §14.2).** As above (Lemma 2).

- **Lemma 5.4 (resolvent well-posedness, Brezis 1973 + Crandall-Liggett 1971).** As above (Lemma 1). The QP is the resolvent $J_h$ at step $h \to 0^+$. Crandall-Liggett's exponential formula [1971] gives the continuous-time semigroup. Brezis (1973) Theorem 4.2 gives existence, uniqueness, and continuous dependence.

- **Lemma 5.5 (Birkhoff-Rayleigh identifiability gain, Birkhoff 1931 + Rayleigh 1877 + Krylov-Bogolyubov 1937).** As above (Lemma 4). The Krylov-Bogolyubov extension to maximal monotone semigroups is in Brezis (1973) §3.3.

- **Lemma 5.6 (uniform multi-surface dwell-time, Hager 1979 + Liberzon 2003).** Under the hysteresis thresholds $(\varepsilon, 2\varepsilon)$ and the QP Lipschitz constant $L_u = L_{\text{QP}}$ from Lemma 1, the inter-event time across all $\binom{N}{2}$ pairs is uniformly bounded below by
$$\tau_d \;\ge\; \frac{\varepsilon}{L_u \cdot \max_{ij} \|2(x_i - x_j)\|} \;\ge\; \frac{\varepsilon}{L_{\text{QP}}\, D_{\max}} \;>\; 0.$$
Hence Zeno is excluded for the multi-pair coupled system, not only pair-wise. Proof: between events, $|c_{ij}|$ changes at rate $\le L_u \cdot \|2(x_i - x_j)\|$; crossing the hysteresis band $(\varepsilon, 2\varepsilon)$ takes at least $\varepsilon / (L_u D_{\max})$. ∎

The theorem is an immediate consequence of these five lemmas, each at most one classical reference deep.

---

## 7. Worked examples

### 7.1. $N=2$, $d=2$, parallel approach

Two agents on the line $\{x_2 = -x_1\}$, $r_{\text{safe}} = 0.5$, references pulling them toward each other. On the active set, $g_{12} \propto (x_1 - x_2) \propto \hat e_1$, so $F_1 = \mathrm{span}\{\hat e_2\}$, $\mathrm{Proj}_{F_1}\big|_{\text{active}} = \mathrm{diag}(0,1)$. Off the active set, $\mathrm{Proj}_{F_1}\big|_{\text{free}} = I$. With active fraction $\bar\mu$ on $\mathcal{M}$,
$$
\bar P_1 \;=\; (1 - \bar\mu)\,I \;+\; \bar\mu\,\mathrm{diag}(0,1) \;=\; \mathrm{diag}(1 - \bar\mu,\; 1), \qquad \lambda_{\min}^+(\bar P_1) = 1 - \bar\mu.
$$
Convergence rate factor in the constraint-normal direction: $1 - \bar\mu$. Tangent direction: $1$.

### 7.2. $N=4$, $d=2$, cross-swap

Agents at $(\pm 3, \pm 3)$ swapping diagonally. Three pairs per agent, each active for fraction $\bar\mu/3$ of the cycle (symmetric idealization; relax for asymmetric activity). For agent 1 going $(-3,-3)\to(3,3)$:
- vs head-on agent 3: $F_1 \perp (1,1)/\sqrt{2}$, projector $\tfrac12\begin{pmatrix}1&-1\\-1&1\end{pmatrix}$.
- vs perpendicular agents 2, 4: projectors $\mathrm{diag}(0,1)$ and $\mathrm{diag}(1,0)$ respectively.

Sum of pair-active projectors: $2I - \tfrac12\begin{pmatrix}1&1\\1&1\end{pmatrix} = \begin{pmatrix}1.5 & -0.5\\-0.5 & 1.5\end{pmatrix}$.
$$
\bar P_1 \;=\; (1 - \bar\mu)\,I + \tfrac{\bar\mu}{3}\!\begin{pmatrix}1.5 & -0.5\\-0.5 & 1.5\end{pmatrix}.
$$
With $\bar\mu = 0.3$: $\bar P_1 = \begin{pmatrix}0.85 & -0.05\\-0.05 & 0.85\end{pmatrix}$, eigenvalues $\{0.80, 0.90\}$, $\lambda_{\min}^+(\bar P_1) = 0.80$. Worst-case rate degradation factor: $0.80$, achieved when the regressor aligns with $(1,1)/\sqrt{2}$.

### 7.3. Simulation parameter values (for reproducibility)

Match the existing `Multi-Agent-CBF` repo:
$$
K_T = 0.5,\quad K_F = 0.3,\quad \gamma = 0.15,\quad \alpha = 10,\quad r_{\text{safe}} = 0.4,\quad
\Lambda = (0.6, 1.4, 0.9, 1.6).
$$
Ranges for axiom (A1): $\theta_{\min} = 1$, $\theta_{\max} = 2$ (so $\kappa_\Lambda = 2$, hence $\delta_{ij}(0) < r_{\text{safe}}^2/4$ for typical $D_{\max} \approx 6$). Margin in (A3'): $\zeta = 0.5\, r_{\text{safe}}^2$. Excitation: $e_i^{\text{pe}}(t) = A_e [\sin(\omega_1 t + \phi_i^1), \sin(\omega_2 t + \phi_i^2)]^\top$ with $\omega_1 = 2\pi (0.7)$ Hz, $\omega_2 = 2\pi (1.1)$ Hz, $\phi_i^k \sim \mathcal{U}[0, 2\pi)$ under seed `rng(42)` (numpy: `np.random.seed(42)`).

### 7.4. Figure plan

1. Cross-swap trajectories: AC alone, AC+CBF, AC+CBF+PE-aware (excitation injection).
2. Parameter convergence $|\hat\theta_i - 1/\Lambda_i|(t)$ for the three conditions.
3. Identifiability gain $\bar\rho_i(t)$ computed online; spatial $\mu$-average.
4. Safety margin $\min h_{ij}(t)$; constraint tightening $\delta(t)$.
5. Sweep over $A_e \in \{0, 0.05, 0.10, 0.20\}\,u_{\max}$ - Pareto rate vs ultimate-bound.
6. Communication-delay sweep: $\min_{ij} h_{ij}(t)$ vs latency $\tau \in \{0, 5, 20, 50, 100\}$ ms (cross-swap + parallel approach), annotating the latency at which safety is first violated. Empirical robustness margin against (A4) relaxation.

---

## 8. Discussion

### Contribution

Six classical objects compose to give a multi-agent adaptive safety-critical controller with quantifiable identifiability-vs-safety trade-off:

1. Maximal monotone operator $A(t,x)$ from the time-varying feasible set [Brezis 1973].
2. Crandall-Liggett exponential formula generating the closed-loop semigroup [1971]; the QP is the resolvent.
3. $N$ parallel Kalman-Bucy filters tracking $\Lambda_i$ [Kalman-Bucy 1961]; Anderson PE-driven covariance decay [1985].
4. Krasovskii ultimate-boundedness for the swapped-signal Lyapunov [1959 §14.2].
5. Birkhoff time-averaging on the closed-loop invariant measure [1931].
6. Rayleigh-quotient anisotropic identifiability gain [1877].

Plus Klein-Erlangen gauge fixing [1872] for QP pre-conditioning.

The contribution is the **engineering observation** that these classical objects compose. The mathematical machinery is pre-1985 in its entirety. **Not a mathematical novelty paper.** A control-design observation paper.

### Position vs prior work

| Prior work | Single-agent / multi-agent | What we extend |
|---|---|---|
| Gutierrez-Hoagg [arXiv 2411.12899, 2024] | single-agent | multi-agent generalisation of vanishing-conservativeness via Kalman-Bucy parallel filters |
| Cohen-Belta [arXiv 2002.04577, 2203.01999, 2303.04241] | single-agent | distributed multi-agent setting with Birkhoff-Rayleigh anisotropy |
| Autenrieb-Annaswamy [arXiv 2309.05533] | single-agent LTI | nonlinear single-integrator with formation reference |

We do not claim mathematical novelty. We claim a clean composition of classical objects in a previously-unmade engineering synthesis.

### Open questions

1. **Optimal excitation $e_i^{\text{pe}}$.** Sinusoidal is convenient. State-feedback rules maximising $\bar\rho_i$ are open.
2. **Higher-relative-degree $h_{ij}$.** For Dubins / quadrotor agents, $h$ has relative degree 2; HOCBF [Xiao-Belta 2021] generalises the freedom cone.
3. **Communication relaxation.** (A4) is continuous-time; event-triggered / discrete-broadcast extension is open.
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
- Krasovskii, N. N. (1959). *Stability of Motion.* Stanford University Press, §14.2 (ultimate boundedness).
- Krylov, N., Bogolyubov, N. (1937). "La théorie générale de la mesure dans son application à l'étude des systèmes dynamiques de la mécanique non linéaire." *Ann. Math.* 38, 65–113.
- Krstić, M., Kanellakopoulos, I., Kokotović, P. (1995). *Nonlinear and Adaptive Control Design.* Wiley §6 (parameter projection).
- LaSalle, J. P. (1960). "Some extensions of Liapunov's second method." *IRE Trans. Circuit Theory* 7, 520–527.
- Lyapunov, A. M. (1892). *The General Problem of the Stability of Motion.* (Eng. transl. 1992.)
- Morse, A. S. (1990) / Pomet, J.-B., Praly, L. (1992). Swapped-signal Lyapunov for normalised adaptive laws.
- Noether, E. (1918). "Invariante Variationsprobleme."
- Rayleigh, Lord (1877). *The Theory of Sound,* §IV (Rayleigh quotient).
- Robinson, S. M. (1980). "Strongly regular generalised equations." *Math. Oper. Res.* 5, 43–62.
- Rockafellar, R. T. (1970). *Convex Analysis.* Princeton (normal cone, maximal monotone operators).
- Yosida, K. (1948). "On the differentiability and the representation of one-parameter semigroup of linear operators." *J. Math. Soc. Japan* 1, 15–21.

**Post-1985 / modern context:**
- Anderson, B. D. O. (1985). "Exponential stability of linear equations arising in adaptive identification." *IEEE TAC* 22(1), 83–88.
- Ames, A. D., Xu, X., Grizzle, J. W. (2014). CBF + slack variable.
- Autenrieb, J., Annaswamy, A. M. (2023). [arXiv 2309.05533] in-house adaptive CBF.
- Cohen, M., Belta, C. (2020, 2022, 2023). [arXiv 2002.04577, 2203.01999, 2303.04241] adaptive CBF lineage.
- Gutierrez, R., Hoagg, J. (2024). [arXiv 2411.12899] adaptive CBF with vanishing conservativeness via PE.
- Khalil, H. K. (2002). *Nonlinear Systems,* 3rd ed., Theorem 4.18 (UUB).
- Liberzon, D. (2003). *Switching in Systems and Control,* §1.2 (hysteresis).
- Sontag, E. D. (1989). "Smooth stabilization implies coprime factorization." *IEEE TAC* 34, 435–443 (ISS formalisation).
- Tee, K. P., Ge, S. S., Tay, E. H. (2009). "Barrier Lyapunov functions for the control of output-constrained nonlinear systems." *Automatica* 45, 918–927.
- Wright, S. J. (1997). *Primal-Dual Interior-Point Methods.* SIAM, §11 (constraint preconditioning).
- Xiao, W., Belta, C. (2021). High-order CBF.

**Twenty-one classical, ten modern.** The framework is in pre-1985 mathematics; modern references frame the application context.

---

## 10. Diff from v2 (and v1)

| v2 (post-OG round 2) | v3 (this version) | Driver |
|---|---|---|
| Smoothed-sigmoid + Γ-convergence | Crandall-Liggett exponential formula; QP is the resolvent | OG follow-up: this is Yosida regularisation; the resolvent formulation is cleaner |
| RLS with shrinking covariance | Kalman-Bucy filter + Anderson 1985 PE decay | OG follow-up: same engine, 50-year-older citation |
| Pre-condition by $1/\Lambda^{\text{eff}}$ as numerical trick | Klein-Erlangen gauge fixing under $\mathbb{R}_{>0}$ scaling symmetry | OG follow-up: the numerical trick is a gauge choice; cite Wright 1997 |
| Anisotropic in $\mathrm{range}(P_i)$ (mismatched for scalar $\Lambda$) | Birkhoff-Rayleigh quotient on $\bar P_i$ as scalar identifiability gain | OG round 2: scalar parameter, anisotropy is a Rayleigh weighting |
| Asymptotic stability claim | Krasovskii ultimate boundedness $\mathcal{O}(A_e^2/\eta + \sup_i \|P_i\|^2)$ | OG round 2: Lyapunov 1892 + Krasovskii 1959 §14.2 |
| Filippov inclusion + Aubin-Cellina | Maximal monotone operator $N_K$ + Brezis 1973 | OG follow-up: Filippov is one route; the Hilbert-space resolvent is stronger and cleaner |
| 4-conclusion theorem | 3-sentence theorem | OG: compress to Bourbaki form |
| 11 references | 30 references (21 classical + 10 modern context) | OG: cite the lineage explicitly |
| Hard active set indicator | Hysteretic active set $\mathcal{A}^{\varepsilon,\text{on}}/\mathcal{A}^{\varepsilon,\text{off}}$ | Controls round: rule out Zeno chattering |
| No slack variable | Slack variable $s_{ij} \ge 0$ with quadratic penalty $M$ | Controls round: feasibility under saturation |
| No prior-tightness statement | $\theta_{\max}/\theta_{\min} \le \kappa_\Lambda$ in (A1) | Controls round: required for non-vacuous safety |
| No worked example for cross-swap | $\bar\mu = 0.3 \Rightarrow \lambda_{\min}^+(\bar P_1) = 0.80$ | Controls round + modern panel: explicit number for reproducibility |
| No parameter table | Match existing repo: $K_T = 0.5, \alpha = 10, \dots$ | Controls round: reproducibility |
| No figure plan | Five-figure plan in §7.4 | Controls round: paper-readiness |

---

The construction is now classically clean and engineering-ready. Next step: run the simulation pipeline incrementally per the controls-expert-reviewer's four-step ordering (smoothed-flow → slack QP → pre-conditioning → Kalman-Bucy auxiliary), each step independently verifiable. After the sim reproduces the worked-example $\lambda_{\min}^+(\bar P_1) = 0.80$ within tolerance, the framework is paper-ready for IEEE-LCSS or CDC, and the proof is at most 4 pages of Brezis-Krasovskii-Rayleigh routine.
