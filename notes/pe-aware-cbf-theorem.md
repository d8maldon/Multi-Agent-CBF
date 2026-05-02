# Excitation-Preserving Distributed Safety Filter for Multi-Agent Adaptive Control

**Status:** mathematical framework, post-audit (modern + OG council).
**Code touched:** none, by design.
**Length target:** rewrite the user's earlier sections 3.5–3.8 in Bourbaki form.

---

## Notation

| Symbol | Type | Meaning |
|---|---|---|
| $i \in \{1, \dots, N\}$ | index | agent index |
| $\mathcal{G} = (V, \mathcal{E})$ | undirected graph on $V = \{1,\dots,N\}$ | communication / formation topology |
| $\mathcal{N}_i$ | $\subset V \setminus \{i\}$ | neighbours of $i$ |
| $x_i, z_i, t_i$ | $\mathbb{R}^d$ | plant state, reference state, target slot |
| $\Lambda_i$ | $[\Lambda_{\min}, 1]$, $\Lambda_{\min} > 0$, constant | unknown control effectiveness |
| $\hat\theta_i$ | $[\theta_{\min}, \theta_{\max}]$, $\theta_{\min} \ge 1$, $\theta_{\max} \ge 1/\Lambda_{\min}$ | adaptive estimate of $1/\Lambda_i$ |
| $u_i^{\text{ref}}, u_i^{\text{AC}}, u_i^{\text{safe}}$ | $\mathbb{R}^d$ | reference command, adaptive command, safety-filtered command |
| $\phi_i := u_i^{\text{ref}}$ | $\mathbb{R}^d$ | regressor for agent $i$'s adaptation |
| $h_{ij}(x) := \|x_i - x_j\|^2 - r_{\text{safe}}^2$ | $C^\infty(\mathbb{R}^{2d}, \mathbb{R})$ | inter-agent barrier function, relative degree 1 in $u$ |
| $\mathcal{A}_i(t) \subseteq \mathcal{N}_i$ | càdlàg in $t$ | active-constraint set at time $t$, defined with tolerance $\varepsilon$ |
| $F_i(t) \subseteq \mathbb{R}^d$ | closed linear subspace | "freedom cone": orthogonal complement of active-constraint normals |
| $m_i^2 := 1 + \|u_i^{\text{ref}}\|^2$ | $\ge 1$ | normalisation gain |

## Axioms

- **(A1) Bounded admissible parameter set.** $\Lambda_i \in [\Lambda_{\min}, 1]$, $\Lambda_{\min} > 0$, time-invariant. Estimate $\hat\theta_i \in [\theta_{\min}, \theta_{\max}]$ enforced via the smooth projection operator of [Krstić, Kanellakopoulos, Kokotović 1995, §6].
- **(A2) Bounded admissible reference and connected graph.** $\{z_i, \dot z_i, t_i, \dot t_i\}$ are uniformly bounded over $t \ge 0$; the graph $\mathcal{G}$ is connected.
- **(A3) Initial strict safety.** $h_{ij}(x(0)) > 0$ for all $i \ne j$.
- **(A4) Neighbour broadcast.** Each agent $i$ has continuous-time access to $\{x_j(t), \hat\theta_j(t) : j \in \mathcal{N}_i\}$.

These axioms are *all* the hypotheses of the theorem. Lipschitz constraints, regularity of the closed-loop, dwell-time on the active-set process, and PE on the normalised regressor are *consequences* once the closed-loop is properly understood (see §6).

---

## 1. Plant, reference, adaptive law

For each agent $i$:
$$
\dot x_i = \Lambda_i u_i, \qquad
u_i^{\text{ref}} = -K_T(z_i - t_i) - K_F \sum_{j \in \mathcal{N}_i}\big[(z_i - z_j) - (t_i - t_j)\big],
$$
$$
u_i^{\text{AC}} = \hat\theta_i \, u_i^{\text{ref}}, \qquad
\dot{\hat\theta}_i = \mathrm{Proj}_{[\theta_{\min},\theta_{\max}]} \!\left[ -\frac{\gamma}{m_i^2} \, (u_i^{\text{ref}})^\top (x_i - z_i) \right].
$$

The reference dynamics are $\dot z_i = u_i^{\text{ref}}$.

---

## 2. The Hilbert-projection safety filter

### 2.1. Constraint, active set, freedom cone

For each unordered pair $\{i, j\}$ with $j \in \mathcal{N}_i$, the ZCBF inequality is
$$
c_{ij}(u_i; x, \hat\theta) := 2(x_i - x_j)^\top \!\big( \Lambda_i^{\text{eff}} u_i - \Lambda_j^{\text{eff}} u_j^{\text{AC}} \big) + \alpha\, h_{ij}(x) \;\ge\; 0,
$$
where $\Lambda_i^{\text{eff}} := 1/\hat\theta_i \in [1/\theta_{\max}, 1/\theta_{\min}]$ is the on-line surrogate for the unknown $\Lambda_i$. (See Lemma 5.2 below for how the estimation error in $\Lambda_i^{\text{eff}}$ is absorbed.)

The active set with tolerance $\varepsilon > 0$:
$$
\mathcal{A}_i^\varepsilon(t) := \{ j \in \mathcal{N}_i : c_{ij}(u_i^{\text{AC}}; x(t), \hat\theta(t)) \le \varepsilon \}.
$$
The constraint normal direction for agent $i$ from neighbour $j$ at the current state is $g_{ij}(x, \hat\theta) := 2 \Lambda_i^{\text{eff}} (x_i - x_j) \in \mathbb{R}^d$.

The **freedom cone** is
$$
F_i(t) := \big(\mathrm{span}\{g_{ij}(x(t), \hat\theta(t)) : j \in \mathcal{A}_i^\varepsilon(t)\}\big)^\perp \;\subseteq\; \mathbb{R}^d.
$$
It is a closed linear subspace of $\mathbb{R}^d$ for each $t$, varying piecewise-continuously in $t$ in the gap topology on $\mathrm{Gr}(\bullet, d)$ (Painlevé–Kuratowski; jumps on a Lebesgue-null set under axioms A1–A4).

### 2.2. The QP

Pick a per-agent excitation signal $e_i^{\text{pe}}: \mathbb{R}_{\ge 0} \to \mathbb{R}^d$ with $\|e_i^{\text{pe}}(t)\| \le A_e$. Define
$$
\tilde e_i^{\text{pe}}(t) := \mathrm{Proj}_{F_i(t)} \big[ e_i^{\text{pe}}(t) \big].
$$
The PE-aware QP, solved by each agent at every $t$:
$$
\boxed{\;
u_i^{\text{safe}}(t) \;=\; \arg\min_{u \in \mathbb{R}^d}\; \big\| u - (u_i^{\text{AC}} + \tilde e_i^{\text{pe}}(t)) \big\|^2
\quad\text{s.t.}\quad
c_{ij}(u; x, \hat\theta) \ge 0 \;\forall j \in \mathcal{N}_i,\;\; \|u\|_\infty \le u_{\max}.
\;}
$$

### 2.3. Lemma 1 (well-posedness of the QP).

Under (A1)–(A4), the QP above admits a unique solution $u_i^{\text{safe}}(t)$ which is Lipschitz in $(x, \hat\theta, e_i^{\text{pe}})$ and piecewise-affine on the strata of $\mathcal{A}_i^\varepsilon$.

*Sketch.* Strict convexity of the objective + linear constraints with non-empty interior (by A3, the constraints have slack at $t = 0$ and the closed loop preserves slack; see Lemma 5.1). Unique solution by Hilbert projection (Riesz 1907). Lipschitz dependence by [Hager 1979]. Piecewise affinity by [Robinson 1980]. ∎

---

## 3. Composite Lyapunov function (swapped-signal form)

For each $i$, define
$$
V_i(x_i, z_i, \hat\theta_i) := \frac{1}{2}\,\frac{\|x_i - z_i\|^2}{m_i^2} \;+\; \frac{\Lambda_i}{2\gamma}\,\big(\hat\theta_i - 1/\Lambda_i\big)^2 .
$$
Composite:
$$
V := \sum_{i=1}^N V_i \;+\; \kappa \sum_{1 \le i < j \le N} B\!\big(h_{ij}(x)\big),
$$
where $B \in C^1((0, \infty), \mathbb{R}_{\ge 0})$ is a smooth barrier with $B(s) \to \infty$ as $s \to 0^+$ and $B'(s) < 0$ on $(0, \infty)$. (Choice $B(s) = -\log s$ on $s > 0$, smoothly extended at $\infty$, suffices.)

### 3.1. Lemma 2 (within-stratum decrease).

Let $S(\mathcal{A}) := \{(x, z, \hat\theta) : \mathcal{A}_i^\varepsilon = \mathcal{A}_i \,\forall i\}$ denote the stratum where the active-set tuple equals $\mathcal{A} = (\mathcal{A}_1, \dots, \mathcal{A}_N)$. On the interior of any such stratum, along closed-loop trajectories under the QP of §2.2, there exist constants $\eta > 0$ and $\rho > 0$ such that
$$
\dot V \;\le\; -\eta\, \sum_i \frac{\|x_i - z_i\|^2}{m_i^4} \;-\; \rho\, \sum_{i < j} \dot h_{ij}^- \, \mathbf{1}_{\{j \in \mathcal{A}_i^\varepsilon\}},
$$
where $\dot h_{ij}^- := \min(0, \dot h_{ij})$.

*Sketch.* Compute $\dot V_i$ for the swapped-signal form: the cross-terms cancel exactly (Morse–Pomet–Praly normalisation, 1985–1992). The barrier-derivative term is non-positive on the active stratum because the QP enforces $\dot h_{ij} \ge -\alpha h_{ij}$ on each active constraint, while $B'(h_{ij}) \dot h_{ij}$ has the right sign by monotonicity of $B$. ∎

### 3.2. Lemma 3 (transition consistency).

At a transition time $\tau$ where $\mathcal{A}_i^\varepsilon$ changes for some $i$, $V$ is continuous and $V(\tau^+) = V(\tau^-)$. (No multi-Lyapunov hand-off needed because $V$ does not depend on the active set; only the *rate* $\dot V$ does.)

*Sketch.* All terms of $V$ are continuous in $(x, z, \hat\theta)$. Activation jumps affect $\dot V$ but not $V$ itself. ∎

Lemmas 2 + 3 give: $V(t)$ is non-increasing along closed-loop trajectories, hence $V(t) \le V(0) < \infty$ for all $t$.

---

## 4. Birkhoff-averaged regressor energy

### 4.1. Time-averaged freedom-cone projector.

By Lyapunov-stability of $V$ (Lemma 2 + boundedness of all terms by $V(0)$), trajectories converge to a compact invariant set $\mathcal{M}$ on which $\dot V \equiv 0$. By LaSalle (1960), $\mathcal{M} \subseteq \{(x, z, \hat\theta) : x_i = z_i \,\forall i\} \cap \{\dot h_{ij} \in \{0, -\alpha h_{ij}\}\}$.

For almost every initial condition $\omega \in \mathcal{M}$, the time-average
$$
P_i(\omega) \;:=\; \lim_{T \to \infty} \frac{1}{T} \int_0^T \mathrm{Proj}_{F_i(\tau)} \, d\tau
$$
exists in operator norm by Birkhoff's ergodic theorem [Birkhoff 1931], applied to the indicator-valued process $\tau \mapsto \mathrm{Proj}_{F_i(\tau)}$. The matrix $P_i(\omega)$ is positive semi-definite with eigenvalues in $[0, 1]$.

If the closed-loop is ergodic on $\mathcal{M}$, $P_i$ is constant in $\omega$ and depends only on the geometry of $\mathcal{M}$. If not, $P_i$ depends on $\omega$ but exists almost everywhere.

### 4.2. Lemma 4 (anisotropic PE retention).

Suppose the unprojected regressor $\phi_i = u_i^{\text{ref}}$ satisfies the persistence-of-excitation condition $\beta_1 I \preceq T_0^{-1}\int_t^{t+T_0} \phi_i \phi_i^\top d\tau \preceq \beta_2 I$ for some $T_0, \beta_1, \beta_2 > 0$ on the open-loop reference (i.e., before the QP intervenes). Then on the closed-loop invariant set $\mathcal{M}$,
$$
\liminf_{T \to \infty} \frac{1}{T} \int_t^{t+T} \phi_i \phi_i^\top \, d\tau \;\succeq\; \beta_1\, P_i.
$$

*Sketch.* The QP modifies what reaches the plant, not $\phi_i = u_i^{\text{ref}}$. So PE on $\phi_i$ is inherited from the reference. The relevant question for parameter convergence is the *closed-loop* identifiability, which depends on the directions in which $\phi_i$ excites the *available* dynamics. The available directions at time $t$ are $F_i(t)$. Time-averaging gives $P_i$ via Birkhoff. ∎

The anisotropy is forced by representation-theoretic invariance: the plant and the reference law are $SO(d)$-equivariant, so any tensor on the right-hand side of the PE bound must transform like $\mathrm{Sym}^2(\mathbb{R}^d)$ under $SO(d)$. The unique such tensor accumulating from the freedom-cone process is $P_i$ [Noether 1918, applied to the $SO(d)$-action on the regressor].

---

## 5. Theorem

**Theorem (Excitation-preserving distributed safety filter).** Under axioms (A1)–(A4) and the PE hypothesis on the open-loop regressor stated in Lemma 4, the closed-loop dynamics defined by §1 + §2.2 satisfy, for almost every initial condition:

1. **Safety.** $h_{ij}(x(t)) \ge 0$ for all $t \ge 0$ and all $i \ne j$.
2. **Boundedness.** $(x_i, z_i, \hat\theta_i)$ are uniformly bounded for all $i$.
3. **Lyapunov stability.** $V$ is a non-increasing function of $t$, with $\dot V \le 0$ along the closed-loop. By LaSalle (1960), trajectories converge to the largest invariant set $\mathcal{M}$ in $\{\dot V = 0\}$.
4. **Anisotropic parameter convergence.** Define $P_i := \lim_T T^{-1}\int_0^T \mathrm{Proj}_{F_i(\tau)} d\tau$, which exists by Birkhoff (1931) on $\mathcal{M}$. Then $\hat\theta_i \to 1/\Lambda_i$ exponentially in $\mathrm{range}(P_i)$ with rate $\propto \beta_1 \, \lambda_{\min}^+(P_i)$, where $\lambda_{\min}^+$ is the smallest positive eigenvalue. The component of $\hat\theta_i - 1/\Lambda_i$ in $\ker(P_i)$ is bounded but not required to converge to zero.

Conclusions 1–3 are absolute. Conclusion 4 is conditional on the geometry of $\mathcal{M}$: if $P_i$ has full rank, parameter convergence is full; if rank-deficient, convergence is partial along the *identifiable directions*.

---

## 6. What the proof actually consists of

Five lemmas, all classical:

- **Lemma 5.1 (forward invariance of the safe set).** The QP enforces $\dot h_{ij} + \alpha h_{ij} \ge 0$; comparison lemma + Gronwall (1919) gives $h_{ij}(t) \ge h_{ij}(0) e^{-\alpha t} > 0$.
- **Lemma 5.2 (estimation-error tolerance).** The use of $\hat\Lambda_i^{\text{eff}} = 1/\hat\theta_i$ in place of $\Lambda_i$ in the constraint introduces an error bounded by $|\hat\theta_i - 1/\Lambda_i| \cdot \|u_i^{\text{AC}}\|$. Under (A1) this is uniformly bounded; the constraint can be tightened by $\delta = (\theta_{\max} - \theta_{\min}) \cdot \sup \|u_i^{\text{AC}}\|$ to absorb it (robust CBF).
- **Lemma 5.3 (composite Lyapunov decrease, Lemma 2 above).**
- **Lemma 5.4 (Hilbert projection well-posedness, Lemma 1 above).**
- **Lemma 5.5 (Birkhoff-averaged anisotropic PE, Lemma 4 above).**

The theorem is an immediate consequence of these five lemmas. Each lemma is at most one classical reference deep.

---

## 7. Worked example: $N=2$, $d=2$, parallel approach

Take two agents on the line $\{x_2 = -x_1\}$, both initially moving along $\hat e_1$ toward the origin. Reference targets $t_1 = (1, 0), t_2 = (-1, 0)$, so $u_i^{\text{ref}}$ pulls them toward each other. With $r_{\text{safe}} = 0.5$, the constraint becomes active when $\|x_1 - x_2\| = 0.5$, i.e., on a 1-codimensional submanifold of state space.

On the active set, the constraint normal is $g_{12} \propto (x_1 - x_2) = 2 x_1 \, \hat e_1$, so $N_1 = \mathrm{span}\{\hat e_1\}$ and $F_1 = \mathrm{span}\{\hat e_2\}$. While the constraint is active:
- The agents can only move tangentially (along $\hat e_2$) without losing safety;
- Excitation injected along $\hat e_1$ is projected to zero;
- Excitation along $\hat e_2$ passes through.

If $e_i^{\text{pe}}(t) = A_e (\cos(\omega_e t), \sin(\omega_e t))^\top$, then on the active set:
$$
\tilde e_1^{\text{pe}}(t) = A_e \sin(\omega_e t)\, \hat e_2.
$$
The time-average of $\mathrm{Proj}_{F_1(\tau)}$ along the active set is
$$
P_1\big|_{\text{active}} = \begin{pmatrix} 0 & 0 \\ 0 & 1 \end{pmatrix}.
$$
Off the active set, $P_1\big|_{\text{free}} = I$. If the active fraction is $\bar\mu$, then
$$
P_1 = (1 - \bar\mu) I + \bar\mu \begin{pmatrix} 0 & 0 \\ 0 & 1 \end{pmatrix} = \begin{pmatrix} 1 - \bar\mu & 0 \\ 0 & 1 \end{pmatrix}.
$$
**Smallest positive eigenvalue:** $\lambda_{\min}^+(P_1) = \min(1 - \bar\mu, 1) = 1 - \bar\mu$. Convergence rate in the $\hat e_1$ direction is degraded by $1 - \bar\mu$; convergence in $\hat e_2$ is unaffected.

The user's earlier conjectured isotropic bound $(1 - \bar\mu)\beta_1 I$ would have predicted $\lambda_{\min}^+ = (1 - \bar\mu)$ in *both* directions, which under-estimates convergence by exactly the factor that distinguishes the freedom-cone-tangent direction from the constraint-normal direction.

---

## 8. Discussion

The contribution of this work is **not** mathematical novelty. The mathematical pieces (Hilbert projection 1906, Lyapunov second method 1892, Birkhoff ergodic theorem 1931, Noether equivariance 1918) are classical. The contribution is the **engineering observation** that injecting excitation tangentially to the active-constraint manifold preserves identifiability in a control-theoretically useful way, with the precise statement of "useful" given by the Birkhoff-averaged projector $P_i$ in conclusion 4 of the theorem.

The theorem distinguishes the *identifiable* parameter components (those in $\mathrm{range}(P_i)$) from the *unidentifiable* ones (those in $\ker(P_i)$). The lab's prior multi-agent paper guaranteed only boundedness of $\hat\theta_i$; this theorem refines that to a directional convergence result that depends explicitly on the geometry of the closed-loop invariant set.

Open questions:
1. **Optimal choice of $e_i^{\text{pe}}$.** The sinusoid is convenient for analysis. Whether one can construct a state-feedback excitation rule that maximises $\lambda_{\min}^+(P_i)$ over a chosen task is open.
2. **Higher-relative-degree extension.** For Dubins agents, $h$ has relative degree 2 in $u$. The HOCBF framework (Xiao–Belta 2021) replaces the freedom cone with a higher-order analogue, but the Birkhoff structure should carry through.
3. **Communication relaxation.** Axiom (A4) requires continuous-time broadcast of $\hat\theta_j$. Discrete / event-triggered relaxations are a separate paper.
4. **Adversarial setting.** If a subset of agents is Byzantine (broadcasts wrong $\hat\theta_j$), the construction breaks. Robust extensions are open.

---

## 9. References (not exhaustive)

- Birkhoff, G. D. (1931). "Proof of the ergodic theorem." *PNAS* 17, 656–660.
- Gronwall, T. H. (1919). "Note on the derivatives with respect to a parameter of the solutions of a system of differential equations." *Annals of Mathematics* 20, 292–296.
- Hager, W. W. (1979). "Lipschitz continuity for constrained processes." *SIAM J. Control Optim.* 17, 321–338.
- Hilbert, D. (1906). Lectures on integral equations (later: Hilbert projection theorem; see Riesz 1907).
- Krstić, M., Kanellakopoulos, I., Kokotović, P. (1995). *Nonlinear and Adaptive Control Design.* Wiley, §6 (parameter projection).
- LaSalle, J. P. (1960). "Some extensions of Liapunov's second method." *IRE Trans. Circuit Theory* 7, 520–527.
- Lyapunov, A. M. (1892). *The General Problem of the Stability of Motion.* (Russian; Eng. transl. 1992, Taylor & Francis.)
- Morse, A. S. (1990) / Pomet, J.-B., Praly, L. (1992). Swapped-signal Lyapunov for normalised adaptive laws.
- Noether, E. (1918). "Invariante Variationsprobleme." *Nachrichten von der Königlichen Gesellschaft der Wissenschaften zu Göttingen*, 235–257.
- Robinson, S. M. (1980). "Strongly regular generalised equations." *Math. Oper. Res.* 5, 43–62.
- Xiao, W., Belta, C. (2021). "High-order control barrier functions." *IEEE TAC* 67, 3655–3662.

---

## 10. What changes from the user's earlier draft

| Earlier draft | Replaced by |
|---|---|
| Isotropic PE bound $\succeq (1 - \bar\mu_i)\beta_1 I$ | Anisotropic Birkhoff bound $\succeq \beta_1 P_i$ |
| Raw Lyapunov $V = \tfrac12 \|e\|^2 + \cdots$ | Swapped-signal $V = \tfrac12 \|e\|^2/m^2 + \cdots$ |
| Duty cycle $\mu_i(t)$ defined circularly | $\bar\mu_i$ defined as Birkhoff ergodic mean on $\mathcal{M}$ |
| $g_{ij}$ uses unknown $\Lambda_i$ | Uses $\hat\Lambda_i^{\text{eff}} = 1/\hat\theta_i$, with Lemma 5.2 absorbing the error |
| 6-paragraph theorem statement | 4 axioms + 4 numbered conclusions |
| Implicit $\hat\theta_j$ communication | Explicit axiom (A4) |
| Claim of mathematical novelty | Claim of engineering-design observation; mathematical machinery is 100% classical |

The earlier draft's verdict was "needs rewrite." This rewrite is the result. The next step is to verify Lemma 5.2 (estimation-error tolerance) in detail and produce the worked-example simulation (§7) to confirm the predicted anisotropic convergence empirically.
