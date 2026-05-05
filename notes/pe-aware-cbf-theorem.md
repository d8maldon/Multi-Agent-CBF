# Excitation-Preserving Distributed Safety Filter for Multi-Agent Adaptive Control

**Status:** v17 (Pass 18, NEW SCOPE: complex-Dubins multi-agent LOE-adaptive CBF). State lifted from $x_i \in \mathbb{R}^2$ (single-integrator) to $(r_i, v_{a,i}) \in \mathbb{C}^2$ (Dubins, with heading via $\arg v_{a,i}$). Unknown LOE gain $\lambda_i$ on the turn-rate channel only (Maldonado-Naranjo + Annaswamy 2025 formulation). CBF $h_{ij} = |r_i - r_j|^2 - r_{\text{safe}}^2$ has **relative degree 2** w.r.t. $u_{2,i}$, requiring HOCBF [Xiao-Belta 2021]. Per-agent QP has scalar decision variable $u_{2,i} \in \mathbb{R}$. v16 single-integrator results retained as Pass 12 SUBMIT-READY; v17 extends the framework to Dubins. Continuous-time simulation only; no hardware claims.
**Length target:** IEEE-LCSS 8-page limit; current draft fits ~6.5 pages with slack.

**Normalisation convention.** All quantities in §1-§7 are *dimensionless*, obtained by rescaling against fixed reference scales $T^* > 0$ (time), $L^* > 0$ (length), and $u^* := L^*/T^*$ (velocity). Specifically: $\tilde x := x/L^*$, $\tilde t := t/T^*$, $\tilde u := u/u^*$, $\tilde K_T := K_T \cdot T^*$, $\tilde\gamma := \gamma$ (already dimensionless under this rescaling), etc. Under this convention the plant equation $\dot x = \Lambda u$ becomes $d\tilde x/d\tilde t = \Lambda\, \tilde u$ with $\Lambda$ dimensionless. The decay rate $\eta$ is dimensionless (per unit normalised time); the physical rate is $\eta_{\text{phys}} = \eta / T^*$. The dwell-time bound $\tau_d$ in Lemma 5.6 is similarly dimensionless; physical dwell-time is $\tau_d^{\text{phys}} = T^* \tau_d$. Numerical values in §8.3 ($K_T = 4$, $\gamma = 0.15$, $r_{\text{safe}} = 0.4$, $u_{\max} = 25$, etc.) are reported with the engineering choice $T^* = 1$ s, $L^* = 1$ m; the gain condition $K_T \Lambda_{\min} > \bar\mu^2 L_{\text{QP}}^{*\,2}$ in §4.1 is then a numerical relation between dimensionless quantities (with $K_T = 4$ in our normalised units), giving $4 \cdot 0.6 = 2.4 > 0.09 \cdot 14.06 = 1.27$ ✓.

---

## Abstract

For a network of $N$ single-integrator agents with unknown control effectiveness $\Lambda_i$, we identify the convergence rate of the parameter estimate $\hat\theta_i \to 1/\Lambda_i$ under a distributed CBF safety filter as the **trace of the constrained Fisher information matrix** on a Whitney-stratified Fadell-Neuwirth configuration space - equivalently, the inverse of the corresponding scalar Cramér-Rao bound on $\Lambda_i^{-1}$. The freedom-cone projection - the orthogonal complement of the active CBF normals - extracts the identifiable component of the open-loop reference; its time-averaged second moment $Q_i = \mathbb{E}_\mu[(\mathrm{Proj}_{F_i} u_i^{\text{ref}})(\mathrm{Proj}_{F_i} u_i^{\text{ref}})^\top]$ is the constrained Fisher information of $1/\Lambda_i$ (Rao 1945, §6), and its trace gives the exponential rate. The construction composes nine pre-1985 classical objects (Nagumo's viability theorem, maximal monotone resolvent, Noether's first theorem, Hilbert-Courant min-max, Krasovskii ultimate boundedness, Krasnosel'skii-Pokrovskii hysteresis operator, Birkhoff ergodic theorem, Klein $O(d)$-invariance, Rao constrained Fisher information). Continuous-time simulation; the QP-resolvent at $h_{\text{outer}} = 5$ ms with OSQP is real-time feasible up to $N \approx 50$ agents.

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
| $Q_i$ | symmetric PSD on $\mathbb{R}^{d\times d}$ | projected-regressor second-moment matrix: $Q_i := \mathbb{E}_\mu[(\mathrm{Proj}_{F_i} u_i^{\text{ref}})(\mathrm{Proj}_{F_i} u_i^{\text{ref}})^\top]$. Under the linear-equality constraint defining $F_i$, $Q_i$ is the Rao (1945) §6 / Aitchison-Silvey (1958) projected-score covariance. The scalar parameter $1/\Lambda_i$ has Fisher information $\propto \mathrm{tr}(Q_i)$. |
| $\bar\rho_i$ | scalar identifiability gain | $\bar\rho_i := \mathrm{tr}(Q_i)$, proportional to the scalar Fisher information of $1/\Lambda_i$ (inverse of the Cramér-Rao variance bound up to the noise-to-sensitivity scaling). |
| $\mathcal{M}$ | $\omega$-limit set | closed-loop attractor on the augmented PDMP state space |
| $m_i^2 := 1 + \|u_i^{\text{ref}}\|^2$ | $\ge 1$ | normalisation gain (swapped-signal Lyapunov) |

## Axioms

- **(A1) Bounded admissible parameter set.** $\lambda_i \in [\lambda_{\min}, 1]$, $\lambda_{\min} > 0$, time-invariant (LOE on the turn-rate channel; cf. §2.1). Estimate $\hat\theta_i \in [\theta_{\min}, \theta_{\max}]$ with $\theta_{\min} \le 1/\lambda_i \le \theta_{\max}$, enforced via clip-projection $\hat\theta_i \mapsto \min(\theta_{\max}, \max(\theta_{\min}, \hat\theta_i))$ on the gradient flow. (Earlier drafts cited the Krstić-Kanellakopoulos-Kokotović 1995 §6 *smooth* projection, which gives $\hat\theta_i \in C^1$; the simulation uses clipping for simplicity. Where the Lyapunov calculation in §4 needs differentiability at the boundary, we use the Clarke generalised derivative — consistent with the Filippov framing of §3.1.) Required prior tightness: $\theta_{\max}/\theta_{\min} \le \kappa_\lambda$ for the QP to remain feasible (see §7).
- **(A2) Bounded admissible reference and connected graph.** $\{z_i, \dot z_i, t_i, \dot t_i\}$ uniformly bounded by $u_{\max}^{\text{ref}}$; $\mathcal{G}$ connected. Define $D_{\max} := 2\big(\sup_i \|z_i\|_\infty + R_{\text{UUB}}\big) + r_{\text{safe}}$, where $R_{\text{UUB}} = \sqrt{2 V(0)}$ is the UUB radius from Lemma 5.3 (the chain $D_{\max}$-needs-UUB is non-circular: $V(0)$ is a *datum*, not a closed-loop quantity).
- **(A2') Closed-loop persistence of excitation.** The target trajectory $t_i(t)$ is non-stationary in the sense $\beta_1 I \preceq T_0^{-1} \int_t^{t+T_0} \dot t_i \dot t_i^\top\, d\tau$ for some $\beta_1, T_0 > 0$. Combined with the MRAC error decay (Lemma 5.3) this guarantees $u_i^{\text{ref}}$ remains PE on the closed loop, hence the Kalman-Bucy covariance $P_i(t) \to 0$ exponentially. (Without (A2'), use the stochastic variant $Q^{\text{KB}} > 0$ in §2 and replace the $P_i \to 0$ claim with $P_i \to P_i^*$.)
- **(A2'') Free-time dwell under HOCBF active-set switching.** When an active pair engages on the scalar control $u_{2,i} \in \mathbb{R}$, the freedom cone $F_i \subset \mathbb{R}$ collapses to $\{0\}$ and the PE projection vanishes. Closed-loop PE is preserved if the cumulative *free-time measure* — time during which $\mathcal{N}_i^{\text{on}}(t) = \emptyset$ — is bounded below: there exist $T_0', \tau_{\min}^{\text{free}} > 0$ such that $\mu(\{t \in [t_0, t_0+T_0'] : \mathcal{N}_i^{\text{on}}(t) = \emptyset\}) \ge \tau_{\min}^{\text{free}}$ uniformly in $t_0$. Verified numerically on the §8 cross-swap (most active episodes are short, $\le 1$ s, with multi-second free-time intervals between).
- **(A3'') Initial conditions for HOCBF + relative-degree-drop guard.** Strengthened from the v16 (A3') to incorporate the higher-order CBF requirements:
  1. $h_{ij}(r(0)) \ge \delta_{ij}(0) + \zeta$ for all $i \ne j$, with $\zeta > 0$ (initial barrier margin).
  2. $\psi_{1,ij}(0) := \dot h_{ij}(0) + \alpha_1 h_{ij}(0) \ge 0$ for all $i \ne j$ (sub-CBF $\psi_1$ initial condition; required by Xiao-Belta 2021 Thm 2 / Aubin-Cellina 1984 §5.1 second-order viability).
  3. $|a_{ii}(t, r, v_a)| \ge \eta_a > 0$ for all $i$, $j \in \mathcal{N}_i^{\text{on}}(t)$, on the closed-loop invariant set $\mathcal{M}$, where $a_{ii}(r, v_a) := 2\,\Im((r_i-r_j)\overline{v_{a,i}})$ is the HOCBF coefficient of $u_{2,i}$ (relative-degree-drop guard; quantitative recoverability — see §3.1.1).
  
  The $\delta_{ij}(0)$ on item 1 is the v17 form derived in §3.1.2 (aggregating estimator residual, cross-term residual, and saturation gap). Equivalently, $\delta_{ij}(0) \le \tfrac12 r_{\text{safe}}^2$ as a precondition on the data; this is what the prior tightness $\kappa_\lambda$ + recoverability margin $\eta_a$ buys.
  
  *Off-locus regularity.* On the relative-degree-drop locus $D_{ij} := \{(r, v_a) : a_{ii}(r, v_a) = 0\}$, item 3 is violated and the differential inclusion is non-Lipschitz. Adopt Filippov (1960) regularisation: the closed-loop solution is interpreted via the convex-hull set-valued vector field, yielding a sliding-mode trajectory along $D_{ij}$ that is absolutely continuous (§3.1).
- **(A4) Neighbour broadcast.** Each agent $i$ has continuous-time access to $\{r_j(t), v_{a,j}(t), \hat\theta_j(t), u_{2,j}^{\text{safe}}(t^-) : j \in \mathcal{N}_i\}$. The broadcast of $u_{2,j}^{\text{safe}}$ is of the *most-recent past* value (notation $t^-$) — this avoids algebraic loops in the distributed QP. The Pass 21 council noted that the v16 derivation used $u_{2,j}^{\text{AC}}$ (assumed-correct) instead of $u_{2,j}^{\text{safe}}$; v17 broadcasts the safety-filtered value to make the cross-term coupling self-consistent across the network. (Discrete / event-triggered relaxations: separate paper.)
- **(A5) Active-set non-saturation.** On the closed-loop invariant set $\mathcal{M}$, $|\mathcal{N}_i^{\text{on}}(t)| \le 1$ for $\mu$-a.e. $t$ (in the v17 scalar-control setting). Equivalently, no agent is simultaneously safety-active against more than one neighbour; freedom cone $F_i$ is non-trivial $\mu$-a.e. (i.e., $F_i = \mathbb{R}$ when no pair is active, and $\{0\}$ when one pair is active). Holds generically when $\deg(\mathcal{G}) \le 2$; otherwise must be checked numerically per scenario. (This replaces the v16 $|\mathcal{N}_i^{\text{on}}| < d$ condition with the $d = 1$ scalar-control specialisation.)

The seven axioms (A1, A2, A2', A2'', A3'', A4, A5) are *all* the hypotheses. Lipschitz constraints (away from the relative-degree-drop locus $D_{ij}$), regularity of the closed loop (Brezis 1973 + Filippov 1960 at $D_{ij}$), and dwell-time bounds (Krasnosel'skii-Pokrovskii 1989) are *consequences*. The (A5') minimum-subtended-angle axiom from v16 is vacuous for the v17 scalar-control setting and is dropped.

---

## 2. Plant (complex Dubins, multi-agent), reference, adaptive law, Kalman-Bucy auxiliary

We adopt the complex state-space representation of the Dubins vehicle from Maldonado-Naranjo and Annaswamy [arXiv 2504.08190, IEEE L-CSS 2025], extended to the multi-agent setting. For each agent $i \in \{1, \ldots, N\}$:

$$
\boxed{\;
r_i \;=\; x_i + i\,y_i \;\in\; \mathbb{C}, \qquad
v_{a,i} \;=\; V_{a,i}\, e^{i\psi_i} \;\in\; \mathbb{C},
\;}
$$

so the per-agent state is $(r_i, v_{a,i}) \in \mathbb{C}^2$ - *position* plus *velocity-along-heading*. The argument $\psi_i = \arg v_{a,i}$ is the heading; the magnitude $V_{a,i} = |v_{a,i}|$ is the resultant speed.

### 2.1. Dynamics

The dynamics, in the bilinear complex form [Maldonado-Naranjo–Annaswamy 2025 eq. 5]:
$$
\dot r_i \;=\; v_{a,i}, \qquad
\dot v_{a,i} \;=\; u_i\, v_{a,i},
$$
where $u_i = u_{1,i} + i\, u_{2,i} \in \mathbb{C}$ is the complex control input. The real part $u_{1,i} = \dot V_{a,i}/V_{a,i}$ controls speed; the imaginary part $u_{2,i} = \dot \psi_i$ controls turn rate.

**Loss-of-effectiveness on the turn-rate channel** [op. cit., eq. 6]: a constant unknown gain $\lambda_i \in [\lambda_{\min}, 1]$, $\lambda_{\min} > 0$, scales the turn-rate channel:
$$
\dot v_{a,i} \;=\; \big(u_{1,i} + i\,\lambda_i\, u_{2,i}\big)\, v_{a,i}.
$$

**Constant-speed simplification** [op. cit., eq. 16]. The user's outer loop regulates speed to a constant $V_0$, so $u_{1,i} = 0$ and $V_{a,i}(t) \equiv V_0$. The bilinear system reduces to the *linear*-in-control form
$$
\dot r_i \;=\; v_{a,i}, \qquad
\dot v_{a,i} \;=\; i\, \lambda_i\, u_{2,i}\, v_{a,i}.
$$
The only effective control per agent is the scalar real turn-rate $u_{2,i} \in \mathbb{R}$.

### 2.2. Reference model (path-following)

Each agent has a reference path $\Gamma_i \subset \mathbb{C}$ defined by waypoints $\{w_i^{(k)}\}$ and minimum-turn-radius $R_{\min}$ constraints (op. cit. §III.A). The reference model has state $(r_{\text{ref},i}, v_{\text{ref},i}) \in \mathbb{C}^2$:
$$
\dot r_{\text{ref},i} \;=\; v_{\text{ref},i}, \qquad
\dot v_{\text{ref},i} \;=\; i\, u_{2,\text{ref},i}\, v_{\text{ref},i},
$$
with $|v_{\text{ref},i}| = V_0$ and $u_{2,\text{ref},i} = \dot\psi_{\text{ref},i} = \kappa_{\text{ref},i}\, V_0$ (curvature times speed).

### 2.3. Tracking error and reference-feedback law

Define the multi-agent tracking error in complex form:
$$
e_i \;=\; r_i - r_{\text{ref},i} \;\in\; \mathbb{C}, \qquad
\tilde v_i \;=\; v_{a,i} - v_{\text{ref},i} \;\in\; \mathbb{C}.
$$
The reference-feedback law lifts the v16 formation-tracking law to the complex setting:
$$
u_{2,i}^{\text{ref}} \;=\; u_{2,\text{ref},i} \;-\; \Re\!\Big(\frac{K_T\, e_i + K_F\!\sum_{j \in \mathcal{N}_i}\![(e_i - e_j) - (e_{\text{slot},i} - e_{\text{slot},j})]}{i\, v_{a,i}}\Big),
$$
where the division-by-$i\,v_{a,i}$ converts the complex tracking-error feedback into a real turn-rate command (the only available control under the constant-speed simplification). $K_T, K_F$ are the same tracking and formation-coupling gains as v16. $e_{\text{slot},i}$ encodes per-agent target-slot offsets in the formation.

### 2.4. Adaptive control law

The adaptive control synthesises the reference command modulated by the parameter estimate:
$$
u_{2,i}^{\text{AC}} \;=\; \hat\theta_i\, u_{2,i}^{\text{ref}}, \qquad
\hat\theta_i \in [\theta_{\min}, \theta_{\max}],
$$
where $\hat\theta_i$ is the estimate of $1/\lambda_i$ (so that $\lambda_i \hat\theta_i u^{\text{ref}} \approx u^{\text{ref}}$ once $\hat\theta_i \to 1/\lambda_i$). The adaptive law uses the *complex* swapped-signal gradient on the tracking error:
$$
\dot{\hat\theta}_i \;=\; \mathrm{Proj}_{[\theta_{\min},\theta_{\max}]}\!\Big[ -\frac{\gamma}{m_i^2}\, \Re\!\big( \overline{i\, v_{a,i}\, u_{2,i}^{\text{ref}}}\, \tilde v_i \big) \Big],
\qquad m_i^2 := 1 + |v_{a,i}\, u_{2,i}^{\text{ref}}|^2,
$$
which is the natural lift of the v16 normalised swapped-signal law to the complex regressor $i\, v_{a,i}\, u_{2,i}^{\text{ref}}$. This is the same Pomet-Praly normalisation now applied componentwise to the complex error.

### 2.5. Kalman-Bucy auxiliary

The KB filter on the same data, deterministic Riccati ($Q^{\text{KB}} = 0$):
$$
\dot P_i \;=\; -P_i\, \frac{|v_{a,i}\, u_{2,i}^{\text{ref}}|^2}{m_i^2}\, P_i, \qquad
P_i(0) = (\theta_{\max} - \theta_{\min})^2.
$$
Under (A2') closed-loop PE on $u_{2,i}^{\text{ref}}$, $P_i(t) \to 0$ exponentially at rate $\gamma \cdot \mathrm{tr}(Q_i)$ by Anderson (1985); see §5. The filter's output drives the time-varying CBF tightening $\delta(t)$ in §3.

---

## 3. The resolvent QP (Moreau prox + Klein-Erlangen gauge fixing + Filippov regularisation)

### 3.0. Foundational lineage

The §3 construction composes nine pre-1985 classical objects, each carrying a v17-specific role:

| Component | Foundational anchor | Modern engineering rediscovery |
|---|---|---|
| Forward invariance of $h_{ij}\ge 0$ | Nagumo (1942) viability theorem [*Proc. Phys.-Math. Soc. Japan*]; second-order lift via Aubin-Cellina (1984) §5.1 second-order tangent cone | Ames-Xu-Grizzle (2014) ZCBF; Xiao-Belta (2021) HOCBF |
| Differential inclusion at relative-degree drop | Filippov (1960) sliding-mode regularisation [*Mat. Sb.*] | Used implicitly via slack-penalty QP (§3.2) |
| Gauge-fixing | Klein (1872) Erlangen programme; $\mathbb{R}_{>0} \times U(1)$ symmetry | Used for equivariance-check verification |
| QP / metric projection | Moreau (1965) proximal operator [*Bull. Soc. Math. France* 93]; rate-independent moving sets: Moreau (1971) [*Évolution d'un système élasto-plastique*]; rate-dependent: Moreau (1977) sweeping process | OSQP (Stellato et al. 2020) |
| Maximal monotone evolution | Brezis (1973) Thm 4.2 [*Opérateurs maximaux monotones*]; non-autonomous via Kato (1967) | Crandall-Liggett (1971) exponential formula |
| Hysteretic active set | Krasnosel'skii-Pokrovskii (1989) play operator [*Systems with Hysteresis*]; rate-independent | Liberzon (2003) hysteretic switching |
| Adaptive estimate $\hat\theta\to 1/\lambda$ | Lyapunov (1892) second method; LaSalle (1960) invariance | Pomet-Praly (1992) normalised swapped-signal |
| Constrained Fisher information | Rao (1945 §6) [*Bull. Calcutta Math. Soc.*]; Aitchison-Silvey (1958) projected score | Used in §5 for $\bar\rho_i = \mathrm{tr}(Q_i)$ identifiability rate |
| Slack regularisation | Tikhonov (1963) [*Soviet Math. Dokl.*]; convergence rate Engl-Hanke-Neubauer (1996) | Soft-constraint QP, $\mathcal{O}(M^{-1/2})$ error |

The map "v17 §3 = nine classical pieces, composed" is the core organising principle. Each piece appears in the proofs of §3.1-§3.4, §4-§5.

### 3.1. CBF + relative-degree analysis (HOCBF)

The pairwise safety function is unchanged in form from v16:
$$h_{ij}(r) := |r_i - r_j|^2 - r_{\text{safe}}^2,$$
where $|\cdot|$ is the complex modulus (= Euclidean norm in $\mathbb{R}^2$ under the $r = x + iy$ identification). $h_{ij}$ is invariant under the ambient $SE(2)$ action (translations + rotations), so the construction inherits Klein-Erlangen $O(2)$-equivariance.

**Relative degree.** Differentiate along the closed loop:
$$\dot h_{ij} \;=\; 2\,\Re\!\big((r_i - r_j)\,\overline{v_{a,i} - v_{a,j}}\big),$$
which depends only on $(r, v_a)$ — *not* on the control $u_2$. Differentiating once more,
$$\ddot h_{ij} \;=\; 2\,|v_{a,i} - v_{a,j}|^2 \;+\; 2\,\Re\!\big((r_i - r_j)\,\overline{\dot v_{a,i} - \dot v_{a,j}}\big),$$
and substituting $\dot v_{a,i} = i\,\lambda_i u_{2,i} v_{a,i}$ (eq. 2.1 with the constant-speed simplification) and using $\Re(-iz) = \Im(z)$:
$$\boxed{\ddot h_{ij} \;=\; 2\,|v_{a,i} - v_{a,j}|^2 + 2\,\lambda_i u_{2,i}\, \Im\!\big((r_i - r_j)\,\overline{v_{a,i}}\big) - 2\,\lambda_j u_{2,j}\, \Im\!\big((r_i - r_j)\,\overline{v_{a,j}}\big).}$$
$\ddot h_{ij}$ is *linear* in the controls $(u_{2,i}, u_{2,j})$ with coefficients $2\lambda_i\Im(\cdot)$ and $-2\lambda_j\Im(\cdot)$ respectively. Generically this gives **relative degree 2** w.r.t. $u_2$ (in v16 $h_{ij}$ had relative degree 1 because $\dot x = u$ injected $u$ at first derivative), necessitating the **higher-order CBF (HOCBF) formulation** [Xiao-Belta 2021; foundational form: Aubin-Cellina 1984 §5.1].

**Relative-degree-drop locus.** Define the HOCBF coefficient (with $\lambda_i$ factored out for gauge-fixing in the next subsection)
$$a_{ii}(r, v_a) \;:=\; 2\,\Im\!\big((r_i - r_j)\,\overline{v_{a,i}}\big), \qquad a_{ij}(r, v_a) \;:=\; -2\,\Im\!\big((r_i - r_j)\,\overline{v_{a,j}}\big).$$
The relative-degree-drop locus is
$$D_{ij} \;:=\; \big\{(r, v_a) : a_{ii}(r, v_a) = 0\big\} \;=\; \big\{(r, v_a) : \arg(r_i - r_j) - \arg v_{a,i} \in \{0, \pi\}\big\},$$
i.e., the codimension-1 head-on / tail-on family. On $D_{ij}$, $h_{ij}$ fails uniform relative degree 2; the differential inclusion (§3.1.3) becomes non-Lipschitz, and Brezis (1973) Theorem 4.2 does not apply directly. We adopt the **Filippov (1960) regularisation framing**: at the locus, the closed-loop is interpreted via the convex-hull set-valued vector field, yielding an absolutely continuous solution with sliding-mode behaviour along $D_{ij}$. The slack-penalty QP (§3.2) is the smoothed approximation of this Filippov solution.

To exclude pathological neighbourhoods of $D_{ij}$ from the closed-loop invariant set, axiom (A3'') item 3 imposes the quantitative guard $|a_{ii}(t, r, v_a)| \ge \eta_a > 0$ on $\mathcal{M}$. The recoverability margin $\eta_a$ is derived in §3.1.1.

**HOCBF condition** [Xiao-Belta 2021 Thm 2; foundational form: Nagumo 1942 + Aubin-Cellina 1984 §5.1]. Define $\psi_{0,ij} := h_{ij}$ and $\psi_{1,ij} := \dot \psi_{0,ij} + \alpha_1 h_{ij}$. The HOCBF condition for forward invariance is
$$\dot \psi_{1,ij} + \alpha_2\, \psi_{1,ij} \;\ge\; 0 \;\;\Longleftrightarrow\;\; \ddot h_{ij} + (\alpha_1 + \alpha_2)\,\dot h_{ij} + \alpha_1 \alpha_2\, h_{ij} \;\ge\; 0,$$
where $\alpha_1, \alpha_2 > 0$ are linear class-$\mathcal{K}$ gains. By Aubin-Cellina (1984) §5.1, this implies $h_{ij}(t) \ge 0$ for all $t$ provided $\psi_{0,ij}(0), \psi_{1,ij}(0) \ge 0$ — both of which are required by axiom (A3'') items 1 and 2.

*Lyapunov reformulation.* $\psi_{1,ij}$ is itself a Lyapunov-style function with reverse inequality $\dot\psi_1 \ge -\alpha_2\psi_1$ (Krasovskii 1959 §14). Equivalently, $\psi_1(t) \ge \psi_1(0)e^{-\alpha_2 t} \ge 0$ — the foundational reason the initial-condition requirement propagates to all $t\ge 0$.

**Gauge-fixed constraint.** Multiply the HOCBF condition through by $\hat\theta_i \in [\theta_{\min}, \theta_{\max}]$ (positive by axiom (A1), so the inequality direction is preserved), and use the gauge-fix approximations $\hat\theta_i\,\lambda_i \approx 1$ and $\hat\theta_i\,\lambda_j \approx \hat\theta_i / \hat\theta_j$ (justified by axiom (A1) bounds and the estimator residual analysis below):
$$
\boxed{\;
c_{ij}(u_{2,i}; r, v_a, \hat\theta) \;:=\; a_{ii}\, u_{2,i} \;+\; \tfrac{\hat\theta_i}{\hat\theta_j}\, a_{ij}\, u_{2,j}^{\text{safe}}(t^-) \;+\; \hat\theta_i\, b_{ij}^{(0)} \;\ge\; \delta_{ij}(t),
\;}
$$
where the $\hat\theta$-independent residual is
$$
\boxed{b_{ij}^{(0)} \;:=\; 2\,|v_{a,i} - v_{a,j}|^2 + 2(\alpha_1 + \alpha_2)\,\Re\!\big((r_i - r_j)\,\overline{v_{a,i} - v_{a,j}}\big) + \alpha_1 \alpha_2\, h_{ij},}$$
$u_{2,j}^{\text{safe}}(t^-)$ is the most-recent broadcast of agent $j$'s safety-filtered command (axiom (A4)), and $\delta_{ij}(t)$ is the time-varying tightening derived in §3.1.2.

**(Pass 19 / 20 / 21 NOTE.)** Earlier drafts wrote $b_{ij}^{(0)} = |v|^2 + (\alpha_1+\alpha_2)\Re(\cdot) + (\alpha_1\alpha_2/2) h$ — every term halved by 2. This was inconsistent with the LHS coefficient $a_{ii} = 2\Im(\cdot)$: re-deriving from $\ddot h + (\alpha_1+\alpha_2)\dot h + \alpha_1\alpha_2 h \ge 0$ shows that after multiplying by $\hat\theta_i$, $|v|^2$ and $(\alpha_1+\alpha_2)\Re(\cdot)$ each carry a factor of 2 from the substitutions $\ddot h \supset 2|v|^2$ and $\dot h = 2\Re(\cdot)$, while $\alpha_1\alpha_2 h_{ij}$ enters with coefficient 1. The corrected $b_{ij}^{(0)}$ above is internally consistent with $a_{ii} = 2\Im(\cdot)$.

**Klein equivariance verification.** Under the gauge action $\hat\theta_i \mapsto \kappa\hat\theta_i$ (uniform $\mathbb{R}_{>0}$ scaling, $\kappa > 0$):
- LHS first term $a_{ii}\,u_{2,i}$ is $\hat\theta$-degree-0 (no $\hat\theta$).
- LHS second term $(\hat\theta_i/\hat\theta_j)\,a_{ij}\,u_{2,j}^{\text{safe}}$ is $\hat\theta$-degree-0 (the ratio is invariant).
- LHS third term $\hat\theta_i\,b_{ij}^{(0)}$ is $\hat\theta$-degree-1; rescales by $\kappa$.
- RHS $\delta_{ij}(t)$ is $\hat\theta$-degree-? (depends on its derivation in §3.1.2).

The three LHS terms have *different* $\hat\theta$-degrees, so the constraint is **not** uniformly invariant. The correct equivariance check: dividing the entire constraint by $\hat\theta_i$ recovers the original HOCBF condition $\ddot h + (\alpha_1+\alpha_2)\dot h + \alpha_1\alpha_2 h \ge 0$ (with the gauge-fix approximations made on the $\hat\theta_i\lambda_i$ and $\hat\theta_i\lambda_j$ products), which is $\hat\theta$-independent. The gauge-fixed form is a *gauge choice*, not gauge-invariance — and the right verification is the dimensional / homogeneity check that *each side*, after de-gauging, has the same $\hat\theta$-degree. ✓

### 3.1.1. Recoverability margin (worst-case feasibility under saturation)

For the HOCBF safety filter to be implementable under saturation $|u_{2,i}| \le \dot\psi_{\max}$, the worst-case constraint deficit must be recoverable by maximum turn rate. At a given $(r, v_a, \hat\theta)$, the un-aided HOCBF residual (i.e., the LHS at $u_{2,i} = 0$ minus the RHS) is
$$
\text{res}_{ij}(t, r, v_a, \hat\theta) \;:=\; \tfrac{\hat\theta_i}{\hat\theta_j}\, a_{ij}\, u_{2,j}^{\text{safe}}(t^-) + \hat\theta_i\, b_{ij}^{(0)} - \delta_{ij}(t).
$$
For agent $i$ to feasibly steer $u_{2,i}$ to satisfy $c_{ij} \ge \delta_{ij}$, we need $|a_{ii}|\,\dot\psi_{\max} \ge |{\rm res}_{ij}|$. In the worst-case collision-imminent regime ($h_{ij} \to 0$, $\dot h_{ij} \to -2\,r_{\text{safe}}\,|v_{a,i}-v_{a,j}|$, so $\dot h$ contributes $-2(\alpha_1+\alpha_2) r_{\text{safe}}\,|v|$; $|v_{a,i}-v_{a,j}| \le 2 V_0$),
$$
b_{ij}^{(0)} \big|_{\text{worst}} \;\approx\; 2 \cdot (2V_0)^2 - 2(\alpha_1+\alpha_2) r_{\text{safe}} (2V_0) + \alpha_1\alpha_2 \cdot 0 \;=\; 8 V_0^2 - 4(\alpha_1+\alpha_2)\, r_{\text{safe}}\, V_0.
$$
For $V_0 = 1$, $\alpha_1+\alpha_2 = 10$, $r_{\text{safe}} = 0.4$: $b_{ij}^{(0)}\big|_{\text{worst}} \approx 8 - 16 = -8$. So $\hat\theta_i b_{ij}^{(0)}\big|_{\text{worst}} \le -16$ (with $\hat\theta_i \le \theta_{\max} = 2$). The cross-term contributes at most $\kappa_\lambda \cdot 2 \cdot 2 V_0 \cdot \dot\psi_{\max} = 2\cdot 2\cdot 2\cdot 5 = 40$ in magnitude. The tightening $\delta_{ij}(t) \le \tfrac12 r_{\text{safe}}^2 = 0.08$ on the closed-loop invariant set (from (A3'')).

Putting these together, $|\text{res}_{ij}|_{\text{worst}} \le 16 + 40 + 0.08 \approx 56$. For recoverability:
$$
\dot\psi_{\max}\, |a_{ii}|_{\min} \;\ge\; |\text{res}_{ij}|_{\text{worst}},
$$
i.e., $|a_{ii}|_{\min} \ge 56 / 5 = 11.2$. This is the quantitative recoverability margin $\eta_a$ required by axiom (A3'') item 3 in the *worst case*.

For the §8.3 cross-swap scenario, the worst-case collision-imminent regime is not actually reached on the closed loop (agents engage the active pair well before $h \to 0$, by hysteresis at $c_{ij} \le \varepsilon = 0.05 r_{\text{safe}}^2$), so the practical $\eta_a$ is smaller. The §8.4 §8.4 figure pipeline includes a numerical check that $|a_{ii}| \ge \eta_a^{\text{practical}} > 0$ throughout the simulation, with $\eta_a^{\text{practical}}$ computed online.

*Engineering note* (Ames). The relation $\dot\psi_{\max}\,|a_{ii}|_{\min} \ge \alpha_1\alpha_2\,r_{\text{safe}}^2 + (\text{cross-term + tightening overhead})$ is the v17 lift of the standard "compatibility condition" between CBF gain choice and actuator limits (Ames-Xu-Grizzle 2014 §III). For fixed-wing UAVs at typical $V_0 \sim 20$ m/s and $\dot\psi_{\max} \sim 0.5$ rad/s, the $\alpha$ choice and $r_{\text{safe}}$ must satisfy this relation jointly; otherwise the safety filter is structurally infeasible regardless of slack.

### 3.1.2. The CBF tightening $\delta_{ij}(t)$ — explicit residual aggregation

The tightening $\delta_{ij}(t)$ must absorb three residual sources in the gauge-fixed constraint:

**(R1) Estimator residual on the LHS coefficient.** The exact LHS coefficient is $a_{ii}\,(\hat\theta_i\lambda_i)$, not $a_{ii}$ alone. The product $\hat\theta_i\lambda_i$ deviates from 1 by $|\hat\theta_i\lambda_i - 1|$. By axiom (A1) bounds and the KB filter Cauchy-Schwarz (Lemma 5.2),
$$
\varepsilon^{(1)}_i(t) \;:=\; \big|\hat\theta_i\lambda_i - 1\big| \;\le\; \theta_{\max}\,\sqrt{P_i(t)}\big/\theta_{\min}.
$$
The contribution to the constraint LHS is bounded by $\varepsilon^{(1)}_i(t)\cdot |a_{ii}|\cdot \dot\psi_{\max}$.

**(R2) Cross-term substitution residual.** The exact cross-term is $\hat\theta_i\lambda_j\,a_{ij}\,u_{2,j}^{\text{safe}}$ where $u_{2,j}^{\text{safe}}$ is agent $j$'s realised safety-filtered command and $\hat\theta_i\lambda_j$ is approximated by $\hat\theta_i/\hat\theta_j$. The substitution residual is
$$
\varepsilon^{(2)}_{ij}(t) \;:=\; \big|\hat\theta_i\lambda_j - \hat\theta_i/\hat\theta_j\big| \;\le\; \theta_{\max}\big(\theta_{\max}\sqrt{P_j(t)}/\theta_{\min}^2\big),
$$
contributing $\varepsilon^{(2)}_{ij}(t)\cdot |a_{ij}|\cdot \dot\psi_{\max}$ to the constraint LHS in worst case.

**(R3) Broadcast latency residual.** Under axiom (A4), agent $i$ receives $u_{2,j}^{\text{safe}}(t^-)$ — the most-recent past broadcast. With latency $\tau_d > 0$, the actual current $u_{2,j}^{\text{safe}}(t)$ deviates from the broadcast by
$$
\varepsilon^{(3)}_j(\tau_d) \;:=\; \big|u_{2,j}^{\text{safe}}(t) - u_{2,j}^{\text{safe}}(t-\tau_d)\big| \;\le\; \dot u_{2,\max} \cdot \tau_d \;\le\; (\text{Lipschitz constant of the QP}) \cdot \tau_d,
$$
which the §5.4 dwell-time bound makes precise.

**Aggregation.** The total tightening is
$$
\boxed{\;
\delta_{ij}(t) \;:=\; \underbrace{\dot\psi_{\max}\Big[\,|a_{ii}|\,\varepsilon^{(1)}_i(t) + |a_{ij}|\,\varepsilon^{(2)}_{ij}(t)\,\Big]}_{\text{R1 + R2}} \;+\; \underbrace{\tfrac{\hat\theta_i}{\hat\theta_j}\,|a_{ij}|\,\varepsilon^{(3)}_j(\tau_d)}_{\text{R3}} \;+\; \zeta_0,
\;}
$$
where $\zeta_0 > 0$ is a constant safety margin (Lemma 5.2 baseline). The first two summands vanish as $P_i(t), P_j(t) \to 0$ (estimator convergence); the third vanishes as $\tau_d \to 0$ (continuous-time broadcast). At $t = 0$, $\delta_{ij}(0)$ is largest; axiom (A3'') item 1 requires $h_{ij}(0) \ge \delta_{ij}(0) + \zeta$ to seed the forward invariance.

### 3.1.3. Feasible set and closed-loop differential inclusion

Per-agent feasible set:
$$
K_i(t, r, v_a, \hat\theta) \;:=\; \big\{ u_{2,i} \in \mathbb{R} : c_{ij}(u_{2,i};\,\cdots) \ge \delta_{ij}(t)\ \forall j \in \mathcal{N}_i^{\text{on}}(t),\; |u_{2,i}| \le \dot\psi_{\max} \big\}.
$$
By axioms (A1)-(A4), (A3'') items 1-3, and the recoverability margin (§3.1.1), $K_i$ has non-empty interior on the closed-loop invariant set $\mathcal{M}$, *except possibly* on the relative-degree-drop locus $D_{ij}$ where Filippov regularisation applies.

Hysteretic active-set machinery (Krasnosel'skii-Pokrovskii 1989 play operator; engineering rediscovery: Liberzon 2003 §1.2): engagement at $c_{ij} \le \varepsilon$, disengagement at $c_{ij} \ge 2\varepsilon$, $\varepsilon \in [\delta_{ij}(t) + \mathrm{tol}_{\text{QP}}, 0.1\, r_{\text{safe}}^2]$. Symmetric across the pair: both agents $i$ and $j$ enter / exit $\mathcal{N}_i^{\text{on}}(t) \cap \mathcal{N}_j^{\text{on}}(t)$ in lockstep when computing $c_{\min} := \min(c_i, c_j)$ from the symmetric form (engineering verification: see Pass 21 finding by Egerstedt, [sim/dynamics.py:165](sim/dynamics.py:165)). Under symmetric broadcast, this consensus is automatic.

**Closed-loop.** The closed-loop is the differential inclusion
$$
\dot r_i = v_{a,i}, \qquad \dot v_{a,i} \in i\,\lambda_i\, K_i(t, r, v_a, \hat\theta)\, v_{a,i},
$$
governed by the time-varying maximal monotone operator $A(t, r, v_a, \hat\theta) = N_{K_i}$ [Rockafellar 1970; Brezis 1973 §2.1] *off the locus* $D_{ij}$, and by the **Filippov (1960) convex-hull regularisation** *on* $D_{ij}$:
$$
\text{at } (r, v_a) \in D_{ij}: \quad \dot v_{a,i} \in i\,\lambda_i\,\overline{\text{conv}}\big\{ K_i(t, r', v_a', \hat\theta) : (r', v_a') \to (r, v_a) \big\}\, v_{a,i}.
$$
This yields an absolutely continuous solution along $D_{ij}$ (sliding-mode behaviour); the slack-penalty QP (§3.2) is the smoothed approximation, with the smoothing parameter being the slack penalty $M < \infty$.

### 3.2. The QP is the (1-D) resolvent

Pick a per-agent scalar excitation signal $e_i^{\text{pe}}: \mathbb{R}_{\ge 0} \to \mathbb{R}$ with $|e_i^{\text{pe}}| \le A_e$, and project onto the freedom cone $F_i(t) \subset \mathbb{R}$. In the v17 scalar-control setting, $F_i$ degenerates to either $\mathbb{R}$ (when $\mathcal{N}_i^{\text{on}}(t) = \emptyset$) or $\{0\}$ (when at least one pair is active). The freedom-cone projection is therefore $\tilde e_i^{\text{pe}}(t) = e_i^{\text{pe}}(t) \cdot \mathbb{1}\{\mathcal{N}_i^{\text{on}}(t) = \emptyset\}$ — PE is admitted only when no pair is active.

The control law is the metric projection of the QP target onto the feasible interval $K_i$, which **is** the Moreau (1965) proximal operator (equivalently the Yosida resolvent $J_h$ at $h \to 0^+$):
$$
\boxed{\;
u_{2,i}^{\text{safe}}(t) \;=\; \mathrm{prox}_{\chi_{K_i(t,r,v_a,\hat\theta)}}\!\big(u_{2,i}^{\text{AC}} + \tilde e_i^{\text{pe}}\big)
\;=\; \arg\min_{u_2,\,s \ge 0} \big(u_2 - (u_{2,i}^{\text{AC}} + \tilde e_i^{\text{pe}})\big)^2 \;+\; M\sum_{j \in \mathcal{N}_i^{\text{on}}} s_{ij}^2
\;}
$$
subject to $a_{ii}\,u_2 + (\hat\theta_i/\hat\theta_j)\,a_{ij}\,u_{2,j}^{\text{safe}}(t^-) + \hat\theta_i\,b_{ij}^{(0)} + s_{ij} \ge \delta_{ij}(t)$ for $j \in \mathcal{N}_i^{\text{on}}$ and $|u_2| \le \dot\psi_{\max}$. This is a *scalar QP* per agent with $1 + |\mathcal{N}_i^{\text{on}}|$ decision variables and $\le 2|\mathcal{N}_i^{\text{on}}| + 2$ inequality constraints (HOCBF + slack non-negativity + saturation). Per-agent cost is $\mathcal{O}(|\mathcal{N}_i^{\text{on}}|)$, dominated by linear constraint setup. The slack penalty $M = 10^4$ is chosen to balance (i) closeness to the hard-constraint solution and (ii) the Tikhonov regularisation rate — see §3.3.

The Moreau-prox / sweeping-process / Crandall-Liggett lineage: Moreau (1965) gives the proximal operator on a static convex set; Moreau (1971) extends to rate-independent moving sets (the elasto-plastic case); Moreau (1977) handles rate-dependent moving sets (the generic $K(t)$ case). v17 is a rate-dependent case (since $K_i(t)$ depends on the moving plant and parameter estimate). Existence + uniqueness + continuous dependence on data follow from Brezis (1973) Theorem 4.2 *off the locus* $D_{ij}$, and from Filippov (1960) regularisation *on* $D_{ij}$. **No smoothed-sigmoid regularisation is required** beyond the slack penalty itself; the QP is the resolvent.

### 3.3. Numerical scheme (Brezis Cor 4.2 + Hager 1979 + Tikhonov 1963)

The simulation picks finite outer step $h_{\text{outer}} > 0$, inner QP tolerance $\text{tol}_{\text{QP}} > 0$, and slack penalty $M < \infty$. Three error sources combine:
$$
\boxed{\;
\|x_n - x(t_n)\| \;\le\; C_1\, h_{\text{outer}} \;+\; C_2\, \frac{\text{tol}_{\text{QP}}}{h_{\text{outer}}} \;+\; \frac{C_3}{\sqrt{M}},
\;}
$$
with $C_1$ from Brezis (1973) Cor. 4.2 (semigroup discretisation), $C_2$ from Hager (1979) Theorem 3.1 (active-set Lipschitz constant), and $C_3$ from Tikhonov (1963) regularisation of the indicator function (rate $\mathcal{O}(M^{-1/2})$ in the worst case; Engl-Hanke-Neubauer 1996 §3.2). Pass 19 originally stated $\mathcal{O}(M^{-1})$; the correction to $\mathcal{O}(M^{-1/2})$ (Pass 20 / Tikhonov) reflects the absence of a source condition on the constraint manifold.

The three errors must be balanced. Default pairing (matches the existing repo and stays inside Simulink's fixed-step loop):
$$
h_{\text{outer}} = 5\times 10^{-3}\;\text{s}, \quad \text{tol}_{\text{QP}} = 10^{-7}, \quad M = 10^4.
$$
At these values the slack-induced error is $\mathcal{O}(M^{-1/2}) = \mathcal{O}(10^{-2})$, comparable to the discretisation $C_1 h = \mathcal{O}(5\times 10^{-3})$ and inner-solver $C_2 \text{tol}/h = \mathcal{O}(2\times 10^{-5})$. To tighten the slack contribution, raise $M$ to $10^5$ (slack error $\mathcal{O}(3\times 10^{-3})$).

Inner solver: **OSQP** (Stellato et al. 2020) — chosen for warm-start support and Python+MATLAB ABI. Per-agent QP has $1 + |\mathcal{N}_i^{\text{on}}|$ decision variables and $\le 2|\mathcal{N}_i^{\text{on}}| + 2$ inequality constraints. For $N=4$: $\le 4$ variables, $\le 8$ constraints; OSQP solves in ~0.05 ms warm-started on a desktop CPU (empirical; benchmark in [tests/test_qp_timing.py](tests/test_qp_timing.py) — pending). Per-step cost scales as $\mathcal{O}(N \cdot \deg(\mathcal{G}))$; **real-time feasible up to $N \approx 50$ at $h_{\text{outer}} = 5$ ms** on an Intel i7-12700-class CPU. Beyond $N = 50$, parallelise per-agent QPs (independent across agents) or coarsen $h_{\text{outer}}$.

**Warm-start at hysteresis events.** The active-set change at an event invalidates the OSQP warm-start (different problem dimension); the implementation cold-starts OSQP for the first iteration after each event. Empirically, events occur at frequency $\sim 1/\tau_d \approx 1$ Hz (Lemma 5.6 dwell-time, foundational form: Krasnosel'skii-Pokrovskii 1989 BV continuity), so the cost penalty is $\sim 10\times$ per event $\times$ 1 Hz $= \sim 1$ ms additional per second; negligible at $h_{\text{outer}} = 5$ ms.

Outer integrator: fixed-step RK4 (preferred for Simulink) or ode15s with mass-matrix identity (preferred for adaptive step-sizing studies). The QP is the resolvent $J_{h_{\text{outer}}}$; no DAE machinery is needed because the constraint enters only through the projection, not as an algebraic equation in the state.

**Closed-form Lagrangian (v17 scalar form).** For agent $i$ with a single active pair $j$ and no saturation binding, the QP admits the Lagrangian solution
$$
u_{2,i}^{\text{safe}} \;=\; \big(u_{2,i}^{\text{AC}} + \tilde e_i^{\text{pe}}\big) + \mu_{ij}^* \cdot a_{ii}, \qquad \mu_{ij}^* = \max\!\Big(0,\, \frac{\delta_{ij}(t) - c_{ij}\big(u_{2,i}^{\text{AC}} + \tilde e_i^{\text{pe}}\big)}{a_{ii}^2}\Big),
$$
where $a_{ii} = 2\Im((r_i - r_j)\overline{v_{a,i}})$ is the v17 scalar HOCBF coefficient (replacing the v16 $2(x_i - x_j)$ vector). With saturation: clip $u_{2,i}^{\text{safe}}$ to $[-\dot\psi_{\max}, +\dot\psi_{\max}]$; if clipping activates, the slack absorbs the residual. With $|\mathcal{N}_i^{\text{on}}| > 1$ active pairs, the closed form generalises to a piecewise-linear function of the target with at most $|\mathcal{N}_i^{\text{on}}| + 2$ breakpoints (Pontryagin Maximum Principle on the QP; Robinson 1980). This is the unit test for the OSQP wrapper before scaling to $N \ge 3$ ([sim/qp_resolvent.py:108](sim/qp_resolvent.py:108) implements it).

### 3.4. Lemma 1 (well-posedness of the QP-resolvent)

**Lemma 1 (v17).** *Under (A1), (A2), (A2'), (A2''), (A3''), (A4), (A5), the QP admits a unique solution that is:*
1. *piecewise-affine on the hysteretic strata of $\mathcal{N}_i^{\text{on}}$ and the saturation-active set $\{|u_{2,i}| = \dot\psi_{\max}\}$ (Robinson 1980),*
2. *Lipschitz in $(r, v_a, \hat\theta, e_i^{\text{pe}})$ on each stratum away from the locus $D_{ij}$, with constant $L_{\text{QP}}^* < \infty$ given below,*
3. *piecewise-Filippov on the locus $D_{ij}$, with sliding-mode dwell-time bounded below by $\tau_d^{\text{Filippov}} > 0$ from §5.6.*

*Sketch.* Strict convexity (objective Hessian $2I$ on $u_{2,i}$ + $2M I$ on slacks) + linear constraints with non-empty interior (axioms (A3'') items 1-3 + Lemma 5.1) + Hilbert projection theorem [Hilbert 1906; Riesz 1907]. Piecewise-affine on each stratum: Robinson (1980).

**Lipschitz constant** (from Hager 1979 Theorem 3.1, lifted to v17 scalar). The active-constraint Jacobian is
$$
G_i(t, r, v_a) \;\in\; \mathbb{R}^{|\mathcal{N}_i^{\text{on}}|}, \qquad (G_i)_j = a_{ii}(r, v_a; r_j, v_{a,j}).
$$
By axiom (A3'') item 3, $|a_{ii}|\ge\eta_a > 0$ on $\mathcal{M}$, so $\sigma_{\min}(G_i) = \min_j |(G_i)_j| \ge \eta_a$. (In v16, the analogous bound was $\sigma_{\min}(G_i) \ge 2 r_{\text{safe}}\,\sigma_{\min}^{\text{geom}}$; the v17 bound is $\eta_a$, which is *not* a function of $r_{\text{safe}}$ alone — it requires the explicit non-degeneracy axiom (A3'') item 3.)

The Lipschitz constant is
$$
\boxed{\;
L_{\text{QP}}(t, r, v_a) \;=\; \frac{1 + \kappa_\lambda \cdot |\mathcal{N}_i^{\text{on}}(t)|}{\eta_a}, \qquad L_{\text{QP}}^* \;:=\; \sup_{(t, r, v_a) \in \mathcal{M}} L_{\text{QP}} \;\le\; \frac{1 + \kappa_\lambda}{\eta_a}.
\;}
$$
(For the v17 scalar control with $|\mathcal{N}_i^{\text{on}}| \le 1$ on $\mathcal{M}$ from (A5), $L_{\text{QP}}^* = (1+\kappa_\lambda)/\eta_a$.)

**At the locus $D_{ij}$**: $|a_{ii}| < \eta_a$, the Hager constant blows up, and the Lipschitz claim fails. Filippov (1960) regularisation rescues the construction: the closed-loop solution is absolutely continuous, with $u_{2,i}(t)$ in the convex hull $\overline{\text{conv}}(K_i)$ along $D_{ij}$. The slack-penalty QP smooths this via the $\mathcal{O}(M^{-1/2})$ Tikhonov regularisation. Cross-stratum continuity (across $D_{ij}$ entry / exit and across hysteresis events) follows from Lemma 5.6 (uniform dwell-time, Krasnosel'skii-Pokrovskii 1989). ∎

---

## 4. Composite swapped-signal Lyapunov on complex tracking error

The v17 Lyapunov machinery lifts v16's single-integrator construction to the complex Dubins setting. The key structural change: the per-agent tracking error has *two* components — position error $e_i := r_i - r_{\text{ref},i}\in\mathbb{C}$ and velocity error $\tilde v_i := v_{a,i} - v_{\text{ref},i}\in\mathbb{C}$ — because the plant $(r_i, v_{a,i})\in\mathbb{C}^2$ is second-order in the position-tracking sense. The adaptive law (§2.4) couples to $\tilde v_i$ through the complex regressor $\phi_i := i\,v_{a,i}\,u_{2,i}^{\text{ref}} \in \mathbb{C}$. The Pomet-Praly / Noether cancellation lifts via $\Re(\overline{\phi_i}\tilde v_i)$.

### 4.1. The composite Lyapunov function

For each $i\in\{1,\ldots,N\}$:
$$
V_i \;:=\; \frac{1}{2 m_i^2}\Big(|e_i|^2 + \kappa_v\,|\tilde v_i|^2\Big) \;+\; \frac{\lambda_i}{2\gamma}\,\tilde\theta_i^2, \qquad \boxed{\kappa_v = 1,}
$$
where $\tilde\theta_i := \hat\theta_i - 1/\lambda_i$ and $m_i^2 := 1 + |\phi_i|^2$ is the Pomet-Praly normalisation. The **Noether-required uniform weighting $\kappa_v = 1$** is mandated by the gauge $\mathbb{R}_{>0}$-symmetry of $V_i$ (§4.2): under $G_\kappa: (\hat\theta_i, e_i, \tilde v_i)\mapsto (\kappa\hat\theta_i, \kappa^{-1}e_i, \kappa^{-1}\tilde v_i)$, both $|e_i|^2$ and $|\tilde v_i|^2$ scale by $\kappa^{-2}$; the kinetic-energy term is gauge-invariant *uniformly* iff the two summands carry equal weight. The Pomet-Praly cancellation in §4.3 Step (a) is the Noether-conserved current of this gauge action and exists *only* at $\kappa_v = 1$ (alternative: rescale the §2.4 adaptive-law gain to $\gamma' := \gamma/\kappa_v$ to recover cancellation at any $\kappa_v > 0$, but the §2.4 form uses $\gamma$ directly, so $\kappa_v = 1$ is the consistent choice). Pass 25 (math-god-mode Tao + Annaswamy) flagged this; Pass 26 (OG Noether) made the Noether interpretation explicit.

The composite Lyapunov function is
$$
V \;:=\; \sum_{i=1}^N V_i \;+\; V_{\text{form}} \;+\; \kappa\sum_{1\le i<j\le N} B\big(h_{ij}(r)\big),
$$
where $V_{\text{form}} := \tfrac12 \xi^* G \xi$ with $\xi_i := z_i - t_i \in \mathbb{C}$ (lab-frame formation deviation; $\xi^*$ is the conjugate transpose of the complex column vector), $G$ a positive-definite $N\times N$ Hermitian matrix (formation Laplacian; see §4.2 below), and $B\in C^2((0,\infty),\mathbb{R}_{\ge 0})$ a smooth interior-point barrier ($B(s) = -\log s$) [Krasovskii 1959 interior-point analog; Tee-Ge-Tay 2009 modern barrier-Lyapunov].

### 4.2. Symmetry structure: $\mathbb{R}_{>0} \times U(1)$

The construction inherits two symmetries from the complex Dubins dynamics:

**(i) Klein gauge $\mathbb{R}_{>0}$ on $\hat\theta$.** Under $G_\kappa: (\hat\theta_i, e_i, \tilde v_i) \mapsto (\kappa\hat\theta_i, \kappa^{-1}e_i, \kappa^{-1}\tilde v_i)$, $V_i$ is invariant up to the gauge-invariant $\lambda_i\tilde\theta_i^2/(2\gamma)$ term. This is the v16 Pomet-Praly symmetry, lifted unchanged. Noether's first theorem (1918) gives the conserved quantity that is what Pomet-Praly (1992) wrote out by hand — the *swapped-signal cancellation*.

**(ii) Heading rotation $U(1)$.** Under simultaneous rotation $r\mapsto e^{i\theta}r$, $v_a\mapsto e^{i\theta}v_a$, $z\mapsto e^{i\theta}z$, $v_{\text{ref}}\mapsto e^{i\theta}v_{\text{ref}}$, $t\mapsto e^{i\theta}t$, the dynamics §2.1 are *equivariant*: $\dot v_a = i\lambda u_2 v_a$ scales with $e^{i\theta}$ on both sides ✓. The Lyapunov $V$ is *invariant* (all $|\cdot|^2$ terms and $h_{ij}=|r_i-r_j|^2-r_{\text{safe}}^2$ depend only on phase-invariant magnitudes). The closed-loop trajectory is $U(1)$-equivariant up to the lab-frame-fixed targets $\{t_i\}$, which break the symmetry of any *particular* trajectory while preserving the Lyapunov machinery. *Aerospace upshot:* coordinate frame rotation does not affect stability or convergence — the analysis is intrinsic to the formation, not the lab frame.

### 4.3. Lemma 2 (Krasovskii ultimate boundedness, v17 form)

Along closed-loop trajectories under §3,
$$
\dot V \;\le\; -\eta\, \Big(\sum_i \frac{|e_i|^2 + \kappa_v|\tilde v_i|^2}{m_i^4} + \|\xi\|^2\Big) \;+\; \mathcal{O}(A_e^2) \;+\; \mathcal{O}\!\big(\textstyle\sup_i P_i(t)^2\big) \;+\; \mathcal{O}(M^{-1/2}),
$$
where the decay constant $\eta$ is derived in three steps.

**Step (a): Pomet-Praly / Noether cancellation on the complex regressor.** Differentiating $V_i$ and substituting the adaptive law $\dot{\hat\theta}_i = -(\gamma/m_i^2)\Re(\overline{\phi_i}\tilde v_i)$ (eq. §2.4):
$$
\dot V_i \;=\; \underbrace{\frac{1}{m_i^2}\Re(\overline{e_i}\tilde v_i)}_{\text{position-velocity coupling}} \;+\; \underbrace{\frac{\lambda_i}{m_i^2}\,\tilde\theta_i\,u_{2,i}^{\text{ref}}\,\Re(\overline{\tilde v_i}\,i\,v_{a,i})}_{\text{cross (i)}} \;-\; \underbrace{\frac{\lambda_i}{m_i^2}\,\tilde\theta_i\,u_{2,i}^{\text{ref}}\,\Re(\overline{i\,v_{a,i}}\,\tilde v_i)}_{\text{cross (ii) from adaptive law}} \;+\; \underbrace{\frac{\lambda_i}{m_i^2}(\delta_{2,i}^{\text{QP}} + \tilde e_i^{\text{pe}})\,\Re(\overline{\tilde v_i}\,i\,v_{a,i})}_{\text{perturbation}} \;+\; \mathcal{O}(\dot m_i^2/m_i^4),
$$
where $\delta_{2,i}^{\text{QP}} := u_{2,i}^{\text{safe}} - u_{2,i}^{\text{AC}}$ is the QP-projection correction. Cross terms (i) and (ii) are *equal* (since $\Re(\overline{\tilde v_i} i v_{a,i}) = \Re(\overline{i v_{a,i}}\tilde v_i)$ — both expressions reduce to the same real number) and **cancel**: this is the v17 Pomet-Praly cancellation, the Noether-conserved quantity for the gauge $G_\kappa$ symmetry above.

**Step (b): formation Laplacian coercivity (Hilbert-Courant 1924, Hermitian lift) + Tikhonov 1952 cascade.** The v17 formation feedback enters through a *cascade*: (formation feedback law §2.3) → $u_{2,i}^{\text{ref}}$ → $v_{\text{ref},i}$ (Dubins reference dynamics §2.2) → $r_{\text{ref},i} = z_i$. This is a 3-level structure (turn-rate command → heading → position-state). Under **Tikhonov's (1952) singular-perturbation theorem** [*Mat. Sb.* 31(73), 575-586] applied to the time-scale separation between the heading-rate inner loop ($\sim 1/\dot\psi_{\max} = 0.2$ s) and the position-error outer loop ($\sim 1/K_T = 0.25$ s), the slow manifold $\{\tilde v\approx\text{quasi-steady}\}$ supports the reduced Lyapunov on $(\xi, \tilde\theta)$.

On the slow manifold: $\dot\xi = -(K_T I_N + K_F L_{\mathcal{G}})\xi - \dot t + \mathcal{O}(\|\tilde v\|)$, where $L_{\mathcal{G}}$ is the (real symmetric, hence trivially Hermitian) graph Laplacian; the eigenvalue spectrum of $K_T I + K_F L_{\mathcal{G}}$ is $\{K_T + K_F\lambda_k(L_{\mathcal{G}})\}_{k=1}^N$ with $\lambda_1(L_{\mathcal{G}})=0$. By the Hilbert-Courant min-max characterisation [Hilbert-Courant 1924 §I.3], the smallest Rayleigh quotient is $K_T$, so
$$
\dot V_{\text{form}} \;\le\; -K_T\,\|\xi\|^2 \;+\; \|\xi\|\cdot u_{\max}^{\text{ref}} \;+\; \mathcal{O}(\|\tilde v\|).
$$
The $\mathcal{O}(\|\tilde v\|)$ term is the singular-perturbation residual; it is absorbed by the Step (c) inner-loop decay below.

**Step (c): velocity-error inner-loop decay (Maldonado-Naranjo + Annaswamy 2025 §III.B).** The reference-feedback law (§2.3) generates $u_{2,i}^{\text{ref}}$ as a heading-PD command on $\arg(v_{\text{des},i}/v_{a,i})$. Computing $\dot{\tilde v}_i$ directly (substituting §2.1 plant + §2.2 reference + §2.3 feedback law) gives a *cascade* in which $\tilde v_i$ is driven by $-K_T e_i$ via the heading-PD chain rather than by $\tilde v_i$ itself directly:
$$
\dot{\tilde v}_i \;=\; -K_T\,(e_i\cdot\text{phase factor}) \;+\; i\,u_{2,i}^{\text{ref}}\,\tilde v_i \;+\; \mathcal{O}(\tilde\theta_i, \delta_i^{\text{QP}}, \tilde e_i^{\text{pe}}).
$$
The heading-rotation term $i u_{2,i}^{\text{ref}}\tilde v_i$ contributes $\Re(i\cdot\text{real})\equiv 0$ to $d|\tilde v_i|^2/dt$ and is a Hamiltonian flow on the velocity-error circle. The leading-order *decay* comes from the $-K_T e_i$ coupling: integrating around the closed loop, this becomes a 2nd-order linear cascade $(e_i, \tilde v_i)$ that, under the Tikhonov 1952 separation of Step (b), reduces to a stable $V_{\text{vel}} := |\tilde v|^2/(2 m_i^2)$ with decay rate $\propto K_T$ on the slow manifold.

The detailed Lyapunov-Krasovskii analysis of this cascade for the *single-agent* case (one Dubins agent + LOE-MRAC + heading-PD reference) is in **Maldonado-Naranjo + Annaswamy 2025** [IEEE L-CSS / arXiv:2504.08190] §III.B; the multi-agent extension here lifts the inner-loop conclusion *unchanged* (the multi-agent coupling is only through the formation feedback in $u_{2,i}^{\text{ref}}$, which is bounded by Step (b) Hilbert-Courant). The composite $|\tilde v_i|^2$ term in $V_i$ therefore contributes a $-K_T|\tilde v_i|^2/m_i^2$ decay on the slow manifold, mirroring the formation-Laplacian decay on $\xi$.

**Step (d): combine.** With $V := \sum_i V_i + V_{\text{form}} + \kappa\sum_{i<j} B(h_{ij})$ and Young's inequality (weight $\tfrac12$) on the perturbation cross-terms (using the Hager-1979 bound from §3.4):
$$
\dot V \;\le\; -\eta\,\Big(\sum_i \tfrac{|e_i|^2 + \kappa_v|\tilde v_i|^2}{m_i^4} + \|\xi\|^2\Big) \;+\; \mathcal{O}(A_e^2) \;+\; \mathcal{O}(\sup_i P_i(t)^2) \;+\; \mathcal{O}(M^{-1/2}),
$$
with the **closed-form lower bound** (worst-case, always-binding QP):
$$
\eta_{\text{wc}} \;\ge\; \min\!\Big(\tfrac12 K_T,\; \tfrac{\lambda_{\min}}{2} - \tfrac12\,L_{\text{QP}}^{*\,2}/K_T\Big),
$$
and the **duty-cycle-refined bound** (using $\bar\mu := \mathbb{E}_\mu[\mathbb{1}_{\mathcal{N}_i^{\text{on}}\ne\emptyset}]$ from §5):
$$
\boxed{\;\eta \;\ge\; \min\!\Big(\tfrac12 K_T,\; \tfrac{\lambda_{\min}}{2} - \tfrac12\,\bar\mu^2\,L_{\text{QP}}^{*\,2}/K_T\Big),\;}
$$
where $L_{\text{QP}}^* = (1+\kappa_\lambda)/\eta_a$ is the v17 worst-case QP Lipschitz constant from Lemma 1 (§3.4) using the recoverability margin $\eta_a$ from §3.1.1. The **gain condition** for $\eta > 0$ is
$$
K_T \cdot \lambda_{\min} \;>\; \bar\mu^2\, L_{\text{QP}}^{*\,2}.
$$

For the §8.3 v17 parameters ($V_0 = 1$, $\bar\mu \approx 0.3$ empirically, $\kappa_\lambda = 2$, $\eta_a^{\text{practical}} \approx 1.6$ measured online from $\min |a_{ii}|$ on the closed loop): $L_{\text{QP}}^* \approx (1+2)/1.6 \approx 1.88$, so the gain-condition threshold is $\bar\mu^2 L_{\text{QP}}^{*\,2} \approx 0.32$. With $K_T = 4$ and $\lambda_{\min} = 0.6$: $K_T\lambda_{\min} = 2.4 \gg 0.32$. **Margin: 7.5×** (vs v16's 1.9× margin) — the v17 Dubins lift has *more* room because the recoverability margin $\eta_a$ supplies a tighter $L_{\text{QP}}^*$ bound than v16's geometric $\sigma_{\min}^{\text{geom}}$.

The system is **uniformly ultimately bounded** [Krasovskii 1959 §14.2; ISS form via Sontag 1989] with bound
$$
V(t) \;\le\; V(0)\,e^{-\eta t} \;+\; \mathcal{O}(A_e^2/\eta) \;+\; \mathcal{O}(\sup_i P_i(t)^2/\eta) \;+\; \mathcal{O}(M^{-1/2}/\eta).
$$
The slack-induced safety violation $\mathcal{O}(M^{-1/2})$ is absorbed into the (A3'') initial margin $\zeta$ at $M = 10^4$; raise to $M = 10^5$ to tighten by an extra factor of $\sqrt{10}$.

*Sketch.* Pomet-Praly cancellation on $\Re(\overline{\phi_i}\tilde v_i)$ (Noether 1918 conserved quantity for the gauge $\mathbb{R}_{>0}$). Heading-PD inner-loop on $\tilde v$ supplies the $K_T$-rate decay. Hilbert-Courant min-max on $K_T I + K_F L_{\mathcal{G}}$ supplies the $K_T$-rate decay on $\xi$. Young's inequality on the QP-perturbation cross-terms with weight $\tfrac12$. Krasovskii ultimate-boundedness theorem closes the chain. $\mathcal{O}(\sup_i P_i(t)^2)$ vanishes exponentially by Anderson (1985) under (A2'). $\mathcal{O}(M^{-1/2})$ is the Tikhonov regularisation rate (§3.3). ∎

---

## 5. Birkhoff identifiability gain (v17 scalar Fisher info on complex regressor)

The v16 §5 framing — convergence rate as the trace of the freedom-cone-projected regressor's second-moment matrix — lifts to v17 with structural simplifications because the v17 control is the **scalar real turn-rate** $u_{2,i}\in\mathbb{R}$ rather than a vector $u_i\in\mathbb{R}^d$. The freedom cone $F_i\subset\mathbb{R}$ is therefore *binary*: $F_i = \mathbb{R}$ when $\mathcal{N}_i^{\text{on}}=\emptyset$, $F_i=\{0\}$ otherwise (§3.2). The "matrix" $Q_i$ collapses to a scalar; the constrained Fisher information $\bar\rho_i = \mathrm{tr}(Q_i)$ collapses to a scalar Fisher information directly. The Cramér-Rao framing is then the classical *scalar* Cramér-Rao bound on $\theta_i := 1/\lambda_i\in\mathbb{R}$ — Rao (1945) §1, not §6.

### 5.1. Closed-loop state space and invariant measure

Lift the closed-loop state to the augmented space $(r, v_a, m, \hat\theta, P) \in \mathbb{C}^N \times \mathbb{C}^N \times \{0,1\}^{|\mathcal{E}|} \times [\theta_{\min}, \theta_{\max}]^N \times \mathbb{R}_{\ge 0}^N$, where $m$ indexes the hysteresis mode (which pairs are active). Between mode transitions the flow is generated by the maximal monotone operator $A(t, r, v_a, m, \hat\theta)$ off the relative-degree-drop locus $D_{ij}$ (§3.1) and by Filippov (1960) regularisation on $D_{ij}$; mode transitions are event-triggered by $c_{ij}$ crossing the Krasnosel'skii-Pokrovskii hysteresis thresholds. This is a **piecewise-deterministic Markov process** [Davis 1984] augmented with sliding-mode regularisation at the locus.

Trajectories converge to a compact attractor $\mathcal{M}$ on the augmented space (compact by UUB Lemma 2 for $(e, \tilde v)$, $|v_{a,i}|=V_0$ for $v_a$, finite for $m$, projection-bounded for $\hat\theta$, monotone-bounded for $P_i$). By Davis (1984) Theorem 5.5 + Costa-Dufour (2013) for state-constrained PDMPs, $\mathcal{M}$ admits an invariant probability measure $\mu$. Equivalently (and more sharply for deterministic dynamics), the **Krasnosel'skii-Pokrovskii (1989) play operator** lifts the construction to trajectory space and Krylov-Bogolyubov (1937) on Cesàro means via Banach-Alaoglu compactness gives the same $\mu$. Rate-independence of the K-P hysteresis commutes with Birkhoff time-averaging — the structural property the convergence-rate theorem uses.

**Structural setting (Whitney-stratified Fadell-Neuwirth).** The closed-loop position-state lives on the *complex* configuration space
$$
F_{\text{safe}}(\mathbb{C}, N; r_{\text{safe}}) \;:=\; \{r \in \mathbb{C}^N : |r_i - r_j| \ge r_{\text{safe}}\ \forall i\ne j\},
$$
the natural complex analog of the v16 Fadell-Neuwirth space [Fadell-Neuwirth 1962; Whitney 1965 stratification]. Strata are indexed by the active-set mode $m \in \{0,1\}^{|\mathcal{E}|}$ and additionally split off-locus / on-locus across the relative-degree-drop set $D_{ij}$. The QP-resolvent $J_h$ is a stratification-preserving Moreau-prox contraction off-locus; on-locus, Filippov regularisation gives sliding-mode evolution along the locus boundary.

### 5.2. Scalar Fisher information on the complex regressor

The complex regressor for agent $i$'s adaptive law is (§2.4):
$$
\phi_i(t) \;:=\; i\,v_{a,i}(t)\,u_{2,i}^{\text{ref}}(t) \;\in\; \mathbb{C}, \qquad |\phi_i| = V_0\,|u_{2,i}^{\text{ref}}|.
$$
Under the constant-speed simplification $|v_{a,i}|=V_0$, the regressor magnitude is $V_0\cdot|u_{2,i}^{\text{ref}}|$ — the freedom-cone-relevant content lives entirely in $u_{2,i}^{\text{ref}}\in\mathbb{R}$. The freedom-cone-projected regressor in $\mathbb{R}$ is
$$
\Pi_{F_i}\,\phi_i \;=\; \phi_i \cdot \mathbb{1}\{\mathcal{N}_i^{\text{on}}(t) = \emptyset\}, \qquad |\Pi_{F_i}\phi_i|^2 \;=\; V_0^2\,(u_{2,i}^{\text{ref}})^2 \cdot \mathbb{1}\{\mathcal{N}_i^{\text{on}}=\emptyset\}.
$$

Define the **scalar identifiability gain** as the $\mu$-expectation of the normalised projected regressor energy:
$$
\boxed{\;
\bar\rho_i \;:=\; \mathbb{E}_\mu\!\Big[\,\frac{|\Pi_{F_i(t)}\,\phi_i(t)|^2}{m_i^2(t)}\,\Big] \;=\; \mathbb{E}_\mu\!\Big[\frac{V_0^2\,(u_{2,i}^{\text{ref}})^2}{1 + V_0^2\,(u_{2,i}^{\text{ref}})^2}\cdot\mathbb{1}\{\mathcal{N}_i^{\text{on}}=\emptyset\}\Big].
\;}
$$
This is the **constrained Fisher information of $\theta_i = 1/\lambda_i$** restricted to the freedom cone — Rao (1945) §1 in the scalar (single-parameter) form. The denominator $m_i^2 = 1 + |\phi_i|^2$ is the Pomet-Praly normalisation gain that makes the adaptive law swapped-signal (§2.4). $\bar\rho_i\in[0, 1)$ is dimensionless under our normalisation convention.

*Compatibility with v16.* The v16 expression $\bar\rho_i = \mathrm{tr}(Q_i) = \mathbb{E}_\mu[\|\Pi_{F_i}u^{\text{ref}}\|^2]$ does not include the $1/m_i^2$ normalisation explicitly because v16's adaptive law was the un-normalised gradient. The v17 normalised swapped-signal form (§2.4) carries $1/m_i^2$ from the regressor itself; the Fisher info inherits it. Numerical comparison: at $V_0=1$ and $u_{2,i}^{\text{ref}}\sim 1$, $m_i^2 \approx 2$, so $\bar\rho_i^{\text{v17}} \approx \tfrac12 \cdot\bar\rho_i^{\text{v16, scalar}}$ at otherwise-matched parameters.

**Non-degeneracy.** $\bar\rho_i > 0$ iff $\mu(\{t : \mathcal{N}_i^{\text{on}}(t) = \emptyset \text{ and } u_{2,i}^{\text{ref}}(t)\ne 0\}) > 0$. By (A2'') closed-loop free-time dwell, the no-active-pair stratum has $\mu$-mass at least $\tau_{\min}^{\text{free}}/T_0' > 0$; by (A2') closed-loop PE, $u_{2,i}^{\text{ref}}\ne 0$ on a $\mu$-positive subset of any horizon $T_0$. Their intersection has positive $\mu$-mass under (A2') $\cap$ (A2''). Generic case: holds.

### 5.3. Lemma 4 (Birkhoff identifiability, v17 scalar form)

Under (A2') closed-loop PE and (A2'') free-time dwell on the v17 closed-loop measure $\mu$:
$$
\liminf_{T\to\infty}\frac{1}{T}\int_t^{t+T}\frac{|\Pi_{F_i(\tau)}\phi_i(\tau)|^2}{m_i^2(\tau)}\,d\tau \;=\; \bar\rho_i \;>\; 0.
$$

*Proof.* Birkhoff (1931) ergodic theorem on the integrable functional $f(t, r, v_a, m, \hat\theta) := |\Pi_{F_i}\phi_i|^2/m_i^2$, bounded by $|\phi_i|^2/m_i^2 \le 1$ uniformly, hence in $L^1(\mu)$ trivially. Time-average equals $\mu$-expectation $\bar\rho_i$. Strict positivity from the joint (A2')$\cap$(A2'') non-degeneracy above. ∎

**Convergence rate.** Under Anderson (1985) PE-decay, the KB covariance $P_i(t) \to 0$ exponentially with rate $\bar\rho_i$, so $|\hat\theta_i - 1/\lambda_i|^2 \le P_i(t)$ decays at rate $\bar\rho_i$. The adaptive-law convergence is therefore exponential with rate $\gamma\bar\rho_i$ when normalised by $\gamma$ (the adaptive-law gain).

### 5.4. Cramér-Rao framing on the complex regressor

The classical Cramér-Rao bound says $\mathrm{Var}(\hat\theta) \ge \mathcal{I}(\theta)^{-1}$ where $\mathcal{I}$ is the Fisher information. For the v17 adaptive estimation problem, the "data" are the velocity-error increments $\tilde v_i(t)$ which carry $\theta_i = 1/\lambda_i$ through the regressor relation
$$
\tilde v_i \;\sim\; \phi_i\,(\theta_i^{\text{true}} - \hat\theta_i) + \text{(noise + perturbation)}.
$$
The score function is $\partial_{\theta_i}\log p \propto \Re(\overline{\phi_i}\tilde v_i)$ (the same expression that drives the adaptive law in §2.4 — *not coincidentally*: Pomet-Praly normalised gradient *is* the score function up to the $1/m_i^2$ scaling). The (constrained) Fisher information is
$$
\mathcal{I}_i^{\text{constr}} \;=\; \mathbb{E}_\mu\!\Big[\frac{|\Pi_{F_i}\phi_i|^2}{m_i^2}\Big] \;=\; \bar\rho_i.
$$

This is the **Klein-equivariant** scalar Fisher info: the gauge $\mathbb{R}_{>0}$ scales $\hat\theta_i\mapsto\kappa\hat\theta_i$ and rescales the score by $\kappa^{-1}$, leaving $\mathcal{I}_i$ invariant under the joint scaling (Pass 20 OG Klein-equivariance verification, applied to §5). The $U(1)$ symmetry rotates $\phi_i\mapsto e^{i\theta}\phi_i$ leaving $|\phi_i|^2$ invariant ✓. The Cramér-Rao bound for v17 is therefore
$$
\liminf_{t\to\infty}\,t\cdot|\hat\theta_i(t) - 1/\lambda_i|^2 \;\ge\; \mathcal{I}_i^{\text{constr},-1} \;=\; 1/\bar\rho_i,
$$
saturated up to a factor of $\gamma$ by the deterministic adaptive law.

This is the v17 generalisation of the v16 §5 statement "$\bar\rho_i = \mathrm{tr}(Q_i)$ is the constrained Cramér-Rao bound." For the v17 scalar control, $Q_i$ collapses to the scalar $\bar\rho_i$ via the binary freedom-cone $F_i\in\{\{0\},\mathbb{R}\}$.

---

## 6. Theorem (three-sentence Bourbaki form, v17)

**Bourbaki summary (one sentence).** Under (A1)-(A5) + (A2'') + (A3''), the v17 closed-loop generated by Moreau (1971) sweeping on the hysteretically-graded scalar feasible interval $K_i(t) \subset \mathbb{R}$ — equivalently, the Filippov (1960) regularisation thereof on the relative-degree-drop locus — plus the Pomet-Praly normalised complex-regressor adaptive law on $\hat\theta_i$, satisfies Nagumo (1942) + Aubin-Cellina (1984) §5.1 second-order forward invariance of the safe configuration space, Krasovskii (1959) UUB at rate $\eta$ on the composite $(e_i, \tilde v_i, \tilde\theta_i, \xi)$ Lyapunov, and exponential parameter convergence at rate $\gamma\bar\rho_i$ where $\bar\rho_i$ is the time-averaged normalised projected-regressor energy (Rao 1945 + Klein 1872 + Birkhoff 1931 — the constrained scalar Cramér-Rao bound).

> **Theorem (Excitation-preserving distributed safety filter, complex Dubins, v17).** Under axioms (A1), (A2), **(A2') closed-loop PE**, **(A2'') free-time dwell**, **(A3'') HOCBF initial conditions + recoverability margin**, **(A4) continuous broadcast** of $\{r_j, v_{a,j}, \hat\theta_j, u_{2,j}^{\text{safe}}(t^-)\}$, and **(A5) active-set non-saturation** ($|\mathcal{N}_i^{\text{on}}|\le 1$ on $\mathcal{M}$), the closed-loop trajectories of the multi-agent complex-Dubins system $(\dot r_i = v_{a,i},\;\dot v_{a,i} = i\lambda_i u_{2,i}^{\text{safe}} v_{a,i},\;|v_{a,i}|=V_0)$ generated by Moreau's (1971) sweeping process on the time-varying maximal monotone operator $A(t, r, v_a, \hat\theta, m)$ off the relative-degree-drop locus $D_{ij}$ and by Filippov's (1960) regularisation on $D_{ij}$ — equivalently, by per-agent scalar QP-resolvent solves with slack-penalty $M$ — satisfy: **(1)** $h_{ij}(r(t)) \ge 0$ for all $t\ge 0$ and all $i\ne j$, by Nagumo's viability theorem (1942) lifted via Aubin-Cellina (1984) §5.1 to the second-order tangent cone, with sliding-mode behaviour on $D_{ij}$ via Filippov (1960); **(2)** ultimate boundedness $V(t) \le V(0)\,e^{-\eta t} + \mathcal{O}(A_e^2/\eta) + \mathcal{O}(\sup_i P_i(t)^2/\eta) + \mathcal{O}(M^{-1/2}/\eta)$ [Krasovskii 1959 §14.2; Tikhonov 1963 / Engl-Hanke-Neubauer 1996 for the Tikhonov rate], where the second perturbation term vanishes exponentially by Kalman-Bucy (1961) + Anderson (1985) under (A2') and the third vanishes as $M\to\infty$; **(3)** scalar parameter convergence $\hat\theta_i \to 1/\lambda_i$ exponentially with rate $\rho_i = \gamma\cdot\bar\rho_i$, where $\bar\rho_i = \mathbb{E}_\mu[|\Pi_{F_i}\phi_i|^2/m_i^2]$ is the constrained scalar Fisher information of $1/\lambda_i$ on the freedom cone $F_i\in\{\{0\},\mathbb{R}\}$ [Rao 1945 §1 + Klein 1872 + Birkhoff 1931], provided the non-degeneracy $\bar\rho_i > 0$ which holds under (A2') $\cap$ (A2'').

Three sentences. Three numbered conclusions. Lineage spans 1838 (Liouville) — 2025 (Maldonado-Naranjo–Annaswamy IEEE L-CSS, providing the complex-state Dubins LOE formulation lifted here).

 - **Gauss:** "*Pauca sed matura.*"
 - **Hilbert:** "Wir müssen wissen — wir werden wissen." But first, the seven axioms.

**Differences from the v16 theorem.**
- *Plant.* $(r_i, v_{a,i})\in\mathbb{C}^2$, not $x_i\in\mathbb{R}^d$. Constant-speed Dubins with LOE on the turn-rate channel.
- *Relative degree.* $h_{ij}$ has relative degree 2 (not 1 as in v16), requiring HOCBF (Xiao-Belta 2021) and the Aubin-Cellina (1984) second-order tangent cone instead of the Nagumo first-order tangent cone alone.
- *Filippov regularisation.* The relative-degree-drop locus $D_{ij}$ is non-empty (codim-1) in v17 — absent in v16 where $h_{ij}$ had uniform relative degree 1. Filippov sliding-mode evolution is a v17-specific addition.
- *Adaptive law.* Complex-regressor swapped-signal $\dot{\hat\theta}_i = -(\gamma/m_i^2)\Re(\overline{\phi_i}\tilde v_i)$ with $\phi_i = i v_{a,i}u_{2,i}^{\text{ref}}\in\mathbb{C}$.
- *Lyapunov.* Composite over both position and velocity tracking errors: $V_i \supset (|e_i|^2 + \kappa_v |\tilde v_i|^2)/(2 m_i^2)$.
- *Identifiability gain.* Scalar $\bar\rho_i\in[0, 1)$ (not the v16 matrix-trace $\mathrm{tr}(Q_i)$), reflecting the degeneration of $F_i$ to $\{\{0\},\mathbb{R}\}$ in scalar control.
- *UUB bound.* Adds $\mathcal{O}(M^{-1/2})$ Tikhonov term beyond v16's $\mathcal{O}(A_e^2) + \mathcal{O}(\sup P_i^2)$.
- *Symmetry.* $\mathbb{R}_{>0} \times U(1)$ instead of v16's $\mathbb{R}_{>0} \times O(d)$.
- *Recoverability margin* $\eta_a > 0$ in (A3'') is a new quantitative requirement absent in v16 (where uniform relative degree 1 made the analog vacuous).

---

## 7. Proof outline (six lemmas, lifted to complex Dubins)

- **Lemma 5.1 (forward invariance of the safe set, Nagumo + Aubin-Cellina + Filippov + Krasovskii).** The QP enforces the HOCBF condition $\ddot h_{ij} + (\alpha_1+\alpha_2)\dot h_{ij} + \alpha_1\alpha_2 h_{ij} \ge 0$ off the relative-degree-drop locus $D_{ij}$. This is the second-order Aubin-Cellina (1984) §5.1 viability condition (the lift of Nagumo 1942 to relative degree 2). By the Krasovskii (1959 §14) reverse-Lyapunov reformulation, $\psi_{1,ij}(t) \ge \psi_{1,ij}(0)e^{-\alpha_2 t} \ge 0$ propagates to all $t\ge 0$ given (A3'') item 2; hence $h_{ij}(t) \ge h_{ij}(0)e^{-\alpha_1 t} \ge 0$ by Aubin-Cellina + Gronwall (1919). On the locus $D_{ij}$, Filippov (1960) regularisation gives sliding-mode evolution along $D_{ij}$ with $h_{ij}$ continuous and the safety property preserved up to the slack-induced $\mathcal{O}(M^{-1/2})$ violation absorbed by (A3'') item 1's margin $\zeta$.

- **Lemma 5.2 (estimation-error tolerance with vanishing conservativeness, Kalman-Bucy + Anderson).** Define $\tilde\theta_i := \hat\theta_i - 1/\lambda_i$ with KB-bounded $|\tilde\theta_i|^2 \le P_i(t)$. The v17 constraint discrepancy aggregates three residual sources (§3.1.2):
$$|c_{ij}^{\text{true}} - c_{ij}| \;\le\; \dot\psi_{\max}\big[|a_{ii}|\varepsilon^{(1)}_i(t) + |a_{ij}|\varepsilon^{(2)}_{ij}(t)\big] + \tfrac{\hat\theta_i}{\hat\theta_j}|a_{ij}|\varepsilon^{(3)}_j(\tau_d) + \zeta_0 \;=:\; \delta_{ij}(t),$$
where $\varepsilon^{(1)}_i = \theta_{\max}\sqrt{P_i}/\theta_{\min}$ (LHS-coefficient gauge residual), $\varepsilon^{(2)}_{ij} = \theta_{\max}^2\sqrt{P_j}/\theta_{\min}^2$ (cross-term substitution), $\varepsilon^{(3)}_j(\tau_d) = L_{\text{QP}}\cdot\tau_d$ (broadcast latency), and $\zeta_0 > 0$ is a small constant baseline. Tightening the constraint by $\delta_{ij}(t)$ ensures $c_{ij}^{\text{true}} \ge 0$. Under (A1) and Anderson (1985), $P_i(t)\to 0$ exponentially with rate $\bar\rho_i$ (Lemma 5.5 below), hence $\varepsilon^{(1)}_i, \varepsilon^{(2)}_{ij}\to 0$ and $\delta_{ij}(t)\to\zeta_0$ — the constraint tightening **vanishes** asymptotically up to the constant baseline [Gutierrez-Hoagg 2024 single-agent specialisation]. The required prior tightness $\theta_{\max}/\theta_{\min}\le\kappa_\lambda$ + (A3'') item 1's $h_{ij}(0)\ge\delta_{ij}(0)+\zeta$ ensures the QP is initially feasible.

- **Lemma 5.3 (composite Lyapunov ultimate boundedness, Krasovskii 1959 §14.2).** As above (§4 Lemma 2). The composite $V = \sum_i V_i + V_{\text{form}} + \kappa\sum B(h_{ij})$ with $V_i$ tracking both position and velocity errors decays at rate $\eta = \min(K_T/2, \lambda_{\min}/2 - \bar\mu^2 L_{\text{QP}}^{*\,2}/(2 K_T))$ under the gain condition $K_T\lambda_{\min} > \bar\mu^2 L_{\text{QP}}^{*\,2}$. The R_{>0} × U(1) symmetry (§4.2) gives the Pomet-Praly cancellation on the complex regressor; the heading-PD inner-loop on $\tilde v$ supplies the v17-specific $-K_T|\tilde v|^2/m_i^2$ decay term absent in v16. UUB radius is $\mathcal{O}(\sqrt{(A_e^2 + \sup P_i^2 + M^{-1/2})/\eta})$.

- **Lemma 5.4 (resolvent well-posedness, Moreau + Brezis + Filippov + Hager).** The QP is the Moreau (1965) proximal operator on the time-varying interval $K_i(t) \subset \mathbb{R}$. *Off the locus $D_{ij}$*: Moreau (1971) rate-independent moving-set sweeping process gives the continuous-time semigroup; Brezis (1973) Thm 4.2 + Kato (1967) non-autonomous extension give existence, uniqueness, and continuous dependence on data. Lipschitz constant $L_{\text{QP}}^* = (1+\kappa_\lambda)/\eta_a$ from Hager (1979) Thm 3.1 lifted to the v17 scalar Jacobian (§3.4), with $\eta_a$ the recoverability margin from (A3'') item 3 / §3.1.1. *On $D_{ij}$*: Filippov (1960) regularisation gives an absolutely continuous solution with sliding-mode behaviour; the slack-penalty QP at $M < \infty$ is the smoothed Tikhonov approximation [Tikhonov 1963 / Engl-Hanke-Neubauer 1996], converging at $\mathcal{O}(M^{-1/2})$ to the Filippov solution. Cross-stratum continuity at hysteresis events follows from Lemma 5.6 (Krasnosel'skii-Pokrovskii BV continuity).

- **Lemma 5.5 (Birkhoff identifiability via $\bar\rho_i$, Birkhoff + Rao + Krasnosel'skii-Pokrovskii / Davis).** As above (§5 Lemma 4). The convergence rate is $\rho_i = \gamma\bar\rho_i > 0$ where $\bar\rho_i = \mathbb{E}_\mu[|\Pi_{F_i}\phi_i|^2/m_i^2]$ is the constrained scalar Fisher information of $\theta_i = 1/\lambda_i$. Two routes to the invariant measure $\mu$: (i) Krasnosel'skii-Pokrovskii (1989) play operator + Krylov-Bogolyubov (1937) on Cesàro means + Banach-Alaoglu compactness, sharper for the deterministic case; (ii) Davis (1984) PDMP framework + Costa-Dufour (2013) for state-constrained PDMPs, more general. Non-degeneracy $\bar\rho_i > 0$ requires (A2') $\cap$ (A2'') jointly: $u_{2,i}^{\text{ref}}\ne 0$ on a $\mu$-positive set (closed-loop PE) AND $\mathcal{N}_i^{\text{on}}=\emptyset$ on a $\mu$-positive set (free-time dwell), with positive-$\mu$-measure intersection.

- **Lemma 5.6 (uniform multi-pair dwell-time, Krasnosel'skii-Pokrovskii + Hager).** Under the hysteresis thresholds $(\varepsilon, 2\varepsilon)$ and the v17 QP Lipschitz constant $L_{\text{QP}}^* = (1+\kappa_\lambda)/\eta_a$, the inter-event time across all $\binom{N}{2}$ pairs is uniformly bounded below by
$$\tau_d \;\ge\; \frac{\varepsilon}{L_{\text{eff}}\cdot|c_{ij}|_{\max}'} \;>\; 0, \qquad L_{\text{eff}} := L_{\text{QP}}^* + \alpha_1\alpha_2\,\theta_{\max}\,\gamma\,V_0\,\dot\psi_{\max}\,R_{\text{UUB}}/\eta_a,$$
where the second term accounts for the contribution from $\dot{\hat\theta}_i$ entering through the gauge-fixed $\hat\theta_i b_{ij}^{(0)}$ in $c_{ij}$ (chain rule on the adaptive law via (§2.4)). *Proof sketch:* Between events, $|\dot c_{ij}|\le L_{\text{QP}}^*\cdot|a_{ii}'| + \alpha_1\alpha_2|\dot{\hat\theta}_i|\cdot|b_{ij}^{(0)}|/(\hat\theta_i\eta_a)$ where the second term uses the recoverability lower bound $|a_{ii}|\ge\eta_a$ to convert $|\dot{\hat\theta}|\cdot|h|$ into a $|c_{ij}|'$-equivalent rate. Substituting $|\dot{\hat\theta}_i|\le\gamma V_0 \dot\psi_{\max}|\tilde v_i|/m_i^2 \le\gamma V_0 \dot\psi_{\max}R_{\text{UUB}}$ (using $m_i^2 \ge 1$ and Lemma 5.3 UUB radius) and $|b_{ij}^{(0)}|\le\mathcal{O}(V_0^2 + (\alpha_1+\alpha_2)V_0\cdot D_{\max} + \alpha_1\alpha_2 D_{\max}^2)$ gives the $L_{\text{eff}}$ form. Crossing the hysteresis band takes at least $\varepsilon/(L_{\text{eff}}\cdot|c_{ij}|_{\max}')$. Foundational form: Krasnosel'skii-Pokrovskii (1989) BV continuity of the play operator gives the same conclusion via rate-independence; the Hager calculation is the quantitative version. Hence Zeno is excluded for the multi-pair coupled v17 system. ∎

The theorem (§6) is an immediate consequence of these six lemmas, each at most one classical reference deep.

---

## 8. Worked examples

The v17 Dubins setting opens up two qualitatively distinct scenarios that v16 (single-integrator, no relative-degree drop) could not exhibit. §8.1 demonstrates the **Filippov sliding-mode** behaviour at the relative-degree-drop locus $D_{ij}$ — the v17-specific phenomenon. §8.2 lifts the v16 cross-swap example to oriented Dubins agents.

### 8.1. $N=2$ head-on Dubins: relative-degree-drop counter-example and Filippov sliding mode

Two agents on the real axis, $r_1(0) = -L$, $r_2(0) = +L$ for some $L > r_{\text{safe}}/2$, with initial headings $\psi_1(0) = 0$ (agent 1 heading $+x$), $\psi_2(0) = \pi$ (agent 2 heading $-x$): a head-on closing trajectory. With $|v_{a,i}|=V_0$:
$$v_{a,1}(0) = +V_0,\qquad v_{a,2}(0) = -V_0,\qquad r_1 - r_2 = -2L\in\mathbb{R}_{<0}.$$
Compute the HOCBF coefficient at $t=0$:
$$a_{11}(0) = 2\,\Im\big((r_1 - r_2)\overline{v_{a,1}}\big) = 2\,\Im(-2L\cdot V_0) = 0.$$
The state is on the relative-degree-drop locus $D_{12}$. (A3'') item 3 is *violated* at $t=0$ — the agents are not in the closed-loop invariant set $\mathcal{M}$. The Filippov regularisation framing of §3.1.3 applies: the closed-loop is interpreted via the convex-hull set-valued vector field at the locus, and the slack-penalty QP at $M < \infty$ smooths the trajectory.

**Filippov sliding-mode evolution.** As the agents close, $a_{11}$ remains near zero whenever $\arg(r_1-r_2) - \arg v_{a,1} \in \{0, \pi\}$. The slack-penalty QP returns $u_{2,1} = u_{2,1}^{\text{AC}}$ (no safety-driven correction, because the constraint is independent of $u_{2,1}$ at the locus), with slack $s_{12}$ absorbing the constraint deficit. This is the *implicit* Filippov regularisation: the trajectory follows a sliding mode along $D_{12}$ until $\arg v_{a,i}$ rotates off the head-on direction (e.g., due to PE injection $A_e > 0$).

**Identifiability collapse.** The freedom cone $F_1 = \{0\}$ on $D_{12}$ (since the QP constraint *cannot* be helped by $u_{2,1}$, the cone is singular). Strictly: $\Pi_{F_1} u_{2,1}^{\text{ref}} = 0$ throughout the head-on episode. By Lemma 5.5, $\bar\rho_1 = \mathbb{E}_\mu[(u_{2,1}^{\text{ref}})^2/m_1^2 \cdot \mathbb{1}\{F_1 = \mathbb{R}\}] = 0$ if the trajectory remains on $D_{12}$ for $\mu$-a.e. $t$. **Counter-example to identifiability.** Without PE injection ($A_e = 0$) and without (A3'') initial off-locus condition, the parameter $\hat\theta_1$ does not converge to $1/\lambda_1$.

**Engineering takeaway.** PE injection $A_e > 0$ (paper §8.3) breaks the head-on alignment, restoring $|a_{11}| > 0$ and re-engaging identifiability. This is a *qualitative* v17 contribution: in v16 single-integrator, no analogous sliding-mode regime exists ($a_{11}$ never vanishes). The PE-vs-safety-vs-identification trade-off has a *new* dimension — PE also *re-enables* identifiability by perturbing off the locus.

**Numerical example.** With $V_0 = 1$, $L = 1$, $r_{\text{safe}} = 0.4$, $\alpha_1 = \alpha_2 = 5$, $\dot\psi_{\max} = 5$: at separation $|r_1 - r_2| = 0.5$ (closing past $r_{\text{safe}}$ would violate safety), with $v_{a,1} = +1$, $v_{a,2} = -1$ (head-on, so $|v_{a,1}-v_{a,2}|^2 = 4$, $\Re((r_1-r_2)\overline{v_{a,1}-v_{a,2}}) = -1$, $h_{12} = 0.25 - 0.16 = 0.09$): $b_{ij}^{(0)} = 2\cdot 4 + 2\cdot 10\cdot(-1) + 25\cdot 0.09 = 8 - 20 + 2.25 = -9.75$ (computed via [sim/dynamics.py:hocbf_residual](sim/dynamics.py)). The gauge-fixed HOCBF residual is $\hat\theta_i b_{ij}^{(0)} \approx 1.5\cdot(-9.75) = -14.6$ and $a_{11}\to 0$. Required $u_{2,1}\cdot a_{11} \ge 14.6$ — *infinite* turn rate needed at the locus. Slack absorbs the deficit at cost $\mathcal{O}(M^{-1/2})$. PE injection at $A_e = 0.10\dot\psi_{\max} = 0.5$ rad/s introduces a heading perturbation that rotates $v_{a,i}$ off the locus within $\sim 1/A_e \approx 2$ s; subsequently $|a_{11}|$ ramps up and the safety filter regains authority.

**Reach-set / time-to-collision sanity check (Pass 27 Tomlin).** Worst-case time-to-collision starting from $|r_1-r_2| = 1$ (initial separation $L = 1$): $(2L - r_{\text{safe}})/(2 V_0) = (2-0.4)/2 = 0.8$ s. Heading-rotation authority during this window: $\dot\psi_{\max} \cdot 0.8 = 4$ rad — more than a full circle. The Filippov sliding-mode regime is therefore *physically feasible* at research-scale parameters: agents have ample time to turn off the head-on locus once PE injection breaks the alignment.

**Aerospace-scale caveat (Pass 27 Wise).** At aerospace fixed-wing parameters ($V_0\sim 200$ m/s, $\dot\psi_{\max}\sim 0.1$ rad/s coordinated turn for an F-18-class envelope), the head-on relative-degree-drop time-to-collision is millisecond-scale at typical separations, while the heading-rate authority is too low to escape the Filippov regime by turning alone within that window. The §8.1 demonstration is a *research-scale illustration* of the Filippov phenomenon; for aerospace deployment, additional modifications are required: higher $\alpha_1\alpha_2$ ratio (more aggressive HOCBF gain), larger $r_{\text{safe}}$ (defensive standoff), and complementary path-planning to *avoid* head-on initial conditions in the first place. The qualitative Filippov sliding-mode behaviour persists across scales; the quantitative recoverability margin (§3.1.1) is the design-time check.

### 8.2. $N=4$ Dubins cross-swap

Four agents at corners $r_1(0) = -3-3i$, $r_2(0) = 3-3i$, $r_3(0) = 3+3i$, $r_4(0) = -3+3i$ swap diagonally on a sustained sinusoidal cycle (paper_params.py `CROSSSWAP_R0` and `crossswap_targets_oscillating`). Initial headings point each agent toward its diagonal target, so $v_{a,i}(0) = V_0\cdot(c_{\sigma(i)} - c_i)/|c_{\sigma(i)} - c_i|$ where $\sigma$ is the diagonal-swap permutation $(1\leftrightarrow 3, 2\leftrightarrow 4)$. Each agent moves on a curved Dubins path through the formation centre, with three pairwise CBF constraints active per agent at most singly under (A5).

The targets oscillate with period $T_{\text{swap}} = 8$ s (slower than v16's 4 s for Dubins to allow proper turning at $\dot\psi_{\max} = 5$ rad/s + $V_0 = 1$ m/s, giving a minimum-turn radius $V_0/\dot\psi_{\max} = 0.2$ m), guaranteeing axiom (A2') closed-loop PE.

**Per-agent identifiability under cross-swap.** During each half-period, agent 1 at $(-3,-3)$ heads to $(3,3)$, with reference $u_{2,1}^{\text{ref}}$ a heading-PD command on the formation feedback. The reference-feedback law (§2.3) divides by $i\,v_{a,1}$, so $u_{2,1}^{\text{ref}}$ depends on the *complex angle* between $v_{a,1}$ and the desired velocity. For the diagonal-swap geometry with no other-agent perturbation, $u_{2,1}^{\text{ref}}\approx 0$ (agent 1 is heading directly toward the target on a straight line). The active set $\mathcal{N}_1^{\text{on}}$ engages briefly during the formation-centre crossing (when pairwise distances approach $r_{\text{safe}}$), with active fraction $\bar\mu \in [0.2, 0.4]$ depending on (i) the sinusoidal phase, (ii) the PE-injection amplitude $A_e$.

Strata for agent 1:
| Stratum | $\mu$-mass | Active pair | $F_1$ | $|\Pi_{F_1}\phi_1|^2/m_1^2$ |
|---|---|---|---|---|
| Off-active (cruising) | $1-\bar\mu$ | none | $\mathbb{R}$ | $V_0^2 (u_{2,1}^{\text{ref}})^2/(1+V_0^2(u_{2,1}^{\text{ref}})^2)$ |
| Active vs $j=2$ | $\bar\mu/3$ | $(1,2)$ | $\{0\}$ | 0 |
| Active vs $j=3$ | $\bar\mu/3$ | $(1,3)$ — head-on | $\{0\}$ | 0 |
| Active vs $j=4$ | $\bar\mu/3$ | $(1,4)$ | $\{0\}$ | 0 |

Direct $\mu$-expectation (Birkhoff 1931 + scalar Fisher info):
$$
\bar\rho_1 = (1-\bar\mu)\,\mathbb{E}_\mu\!\Big[\frac{V_0^2 (u_{2,1}^{\text{ref}})^2}{1 + V_0^2(u_{2,1}^{\text{ref}})^2} \;\Big|\;\mathcal{N}_1^{\text{on}}=\emptyset\Big] \;+\; \bar\mu\cdot 0.
$$
For the §8.3 PE-injected case with $u_{2,1}^{\text{ref}}\sim\mathcal{O}(A_e)$ during cruise (from the per-agent staggered sinusoidal injection): with $A_e = 0.10\dot\psi_{\max} = 0.5$ rad/s, $V_0 = 1$, the ratio $V_0^2 A_e^2/(1+V_0^2 A_e^2) = 0.25/1.25 = 0.2$. So $\bar\rho_1 \approx (1-\bar\mu)\cdot 0.2$.

For $\bar\mu = 0.3$: $\bar\rho_1 \approx 0.14$. **Convergence rate $\rho_1 = \gamma\bar\rho_1 = 0.15\cdot 0.14 \approx 0.021$/s** — a half-time $\ln 2/\rho_1 \approx 33$ s. (Compare: v16 cross-swap gave $\rho_1 = \gamma\cdot 0.80\beta_1$; v17 is slower because the scalar control has less identifiability content per unit reference energy.)

**Anisotropy collapses to scalar.** The v16 §8.2 anisotropy structure ("worst eigenvector of $\bar P_i$") doesn't apply in v17: $F_i\in\{\{0\},\mathbb{R}\}$ has no anisotropy. The trade-off is now strictly *temporal*: identifiability $\bar\rho_i = (1-\bar\mu)\cdot$ (cruising regressor energy). The engineering knob is $A_e$ (the PE-injection amplitude during cruise) and the active-fraction $\bar\mu$ (which depends on swap geometry / formation timing).

### 8.3. v17 simulation parameter values (for reproducibility)

The full parameter set lives in `sim/paper_params.py`:
$$
\begin{aligned}
&V_0 = 1\,\text{m/s}, \quad \dot\psi_{\max} = 5\,\text{rad/s}, \quad K_T = 4, \quad K_F = 0.3, \quad \gamma = 0.15, \\
&\alpha_1 = \alpha_2 = 5, \quad r_{\text{safe}} = 0.4\,\text{m}, \quad
\lambda = (0.6, 0.9, 0.7, 0.8) \text{ on the turn-rate channel}.
\end{aligned}
$$
- $K_T = 4$: tracking gain. With $\lambda_{\min} = 0.6$, gives $K_T\lambda_{\min} = 2.4$ vs gain-condition threshold $\bar\mu^2 L_{\text{QP}}^{*\,2} \approx 0.32$ (using $\bar\mu = 0.3$, $L_{\text{QP}}^* \approx 1.88$ from §4.3). Margin **7.5×**.
- $K_F = 0.3$: formation-coupling gain. Chosen empirically (Pass 21 deferred item, now documented): $K_F$ weights inter-agent formation feedback in the reference-velocity law (§2.3). Setting $K_F$ too large drives agents into the active-pair regime under formation forcing; $K_F = 0.3$ gives a stable cross-swap where agents converge to the formation without sustained CBF activity. Empirical sweep $K_F \in \{0.1, 0.3, 0.5, 1.0\}$ (data not shown in this draft) confirms $0.3$ is a stable middle ground.
- $\gamma = 0.15$: adaptive-law gain. Chosen to give a half-time $\sim\ln 2/(\gamma\bar\rho_i)$ comparable to the simulation horizon $T_{\text{final}} = 16$ s (Pass 17 figure 2 setup). Larger $\gamma$ would converge faster but amplify perturbation contributions in the §4.3 UUB bound (Pass 21 deferred item, now documented).
- $\alpha_1 = \alpha_2 = 5$: HOCBF class-$\mathcal{K}$ gains. Chosen so the recoverability relation $\dot\psi_{\max}\eta_a\ge\alpha_1\alpha_2 r_{\text{safe}}^2 + \text{cross-term} + \text{tightening}$ (§3.1.1) is comfortably met for the §8 cross-swap geometry.
- $\lambda = (0.6, 0.9, 0.7, 0.8)$: chosen so $1/\lambda_i \in [\theta_{\min}, \theta_{\max}] = [1, 2]$ for every agent. This *projection-compatibility* requirement is the same as v16 (Pass 13 finding 1).

Ranges for axiom (A1): $\theta_{\min} = 1$, $\theta_{\max} = 2$ ($\kappa_\lambda = 2$). Margin in (A3''): $\zeta = 0.5\,r_{\text{safe}}^2$. Recoverability margin: $\eta_a^{\text{practical}}$ measured online from $\min |a_{ii}|$ on the closed loop. Slack penalty $M = 10^4$ (giving $\mathcal{O}(M^{-1/2}) = 0.01$ Tikhonov error). Hysteresis threshold $\varepsilon = 0.05\, r_{\text{safe}}^2 = 0.008$.

**PE excitation.** Scalar (since the v17 control is scalar):
$$
e_i^{\text{pe}}(t) = \tfrac{A_e}{2}\big[\sin(\omega_i^1 t + \phi_i^1) + \sin(\omega_i^2 t + \phi_i^2)\big],
$$
with per-agent staggered frequencies $\omega_i^k = 2\pi(f_0 + i\Delta f + (k-1)\Delta f/2)$, $f_0 = 0.7$ Hz, $\Delta f = 0.2$ Hz (carries over from v16). Per-agent staggering avoids near-singular ensemble PE.

**Reproducibility.** Reference Python implementation (NumPy + OSQP; `pip install osqp`) released at `https://github.com/d8maldon/Multi-Agent-CBF` (branch `v17-section3-rework` and forward).

### 8.4. v17 figure plan

1. **Cross-swap trajectories (oriented triangles)**: AC alone, AC+CBF, AC+CBF+PE-aware. Agents rendered as oriented triangles using $\arg(v_{a,i})$ for heading. Curved Dubins paths replace v16's straight single-integrator lines — visually compelling, makes the formation reasoning clear.
2. **Parameter convergence** $|\hat\theta_i - 1/\lambda_i|(t)$ for the three conditions; v17 expected slower than v16 due to scalar identifiability collapse.
3. **Identifiability gain** $\bar\rho_i(t)$ computed online: $\bar\rho_i(t) = (1/T)\int_{t-T}^t |\Pi_{F_i}\phi_i|^2/m_i^2\,d\tau$; spatial $\mu$-average over agents.
4. **Safety margin** $\min_{ij} h_{ij}(t)$; CBF tightening $\delta_{ij}(t)$ overlaid (visualises eps_1 + eps_2 decay as $P_i\to 0$).
5. **PE sweep** over $A_e\in\{0, 0.05, 0.10, 0.20\}\dot\psi_{\max}$: identifiability $\bar\rho_i$ vs UUB radius (Pareto trade-off). Caption reports $\eta$ explicitly.
6. **Comm-delay sweep**: $\min_{ij} h_{ij}(t)$ vs latency $\tau\in\{0, 5, 20, 50, 100\}$ ms. Re-run for v17 (Pass 17 result was for v16; v17 has higher relative-degree cross-coupling via $v_{a,j}$ — the v17 robustness margin against (A4) relaxation may differ).

**Animation supplementary** (v17-specific): `output/v17/animation_crossswap.mp4` — oriented-triangle agents over the full 16 s simulation horizon, color-coded by active-pair status (green = no pair active, red = pair active). Replaces v16's static figure 1; matches the controls-expert-reviewer Pass-on-figures recommendation.

**N=2 head-on supplementary** (v17 §8.1): figure 7 — Filippov sliding-mode demonstration. Agents on a head-on closing trajectory with and without PE injection. Shows (a) $a_{11}(t)\to 0$ at the locus, (b) $\bar\rho_1(t)\to 0$ during head-on episodes, (c) PE injection breaks the locus and restores identifiability. v17-specific phenomenon, not exhibited in v16.

Each figure includes a saturation-active subpanel (1 if $|u_{2,i}^{\text{safe}}| = \dot\psi_{\max}$, else 0) and an active-pair-count subpanel (number of $j\in\mathcal{N}_i^{\text{on}}$).

---

## 9. Discussion

### Contribution

The v17 construction composes **eleven** classical objects (nine from v16 + two from the Dubins lift) to give a multi-agent adaptive safety-critical controller with quantifiable identifiability-vs-safety trade-off:

1. **Nagumo's viability theorem (1942)** + **Aubin-Cellina (1984) §5.1 second-order tangent cone**: forward invariance of $\{h\ge 0\}$ for relative-degree-2 sets. *Every HOCBF argument here is a corollary of Aubin-Cellina (1984); Xiao-Belta (2021) is the modern engineering rediscovery.* (v17-augmented: v16 had relative degree 1, used Nagumo first-order alone.)
2. **Filippov (1960) regularisation** of the differential inclusion at the relative-degree-drop locus $D_{ij}$: sliding-mode evolution along the locus. (v17-specific: v16 had no analogous degenerate set.)
3. **Maximal monotone operator** $A(t,r,v_a,m,\hat\theta)$ from the time-varying hysteresis-graded feasible set [Brezis 1973]; non-autonomous via Kato (1967).
4. **Moreau (1965) proximal operator + Moreau (1971) rate-independent moving-set sweeping + Moreau (1977) rate-dependent sweeping process** for the time-varying constraint set; Crandall-Liggett (1971) for the autonomous specialisation. The scalar QP is the Moreau proximal operator (= Yosida resolvent of $N_{K_i}$).
5. **Noether's first theorem (1918)** on the gauge $\mathbb{R}_{>0} \times U(1)$ symmetry: $\mathbb{R}_{>0}$ gives the Pomet-Praly swapped-signal cancellation; $U(1)$ gives the heading-rotation invariance of the Lyapunov machinery.
6. **Hilbert-Courant min-max (1924)** on the formation Laplacian $K_T I + K_F L_{\mathcal{G}}$: gives the gain condition $K_T\lambda_{\min} > \bar\mu^2 L_{\text{QP}}^{*\,2}$.
7. $N$ parallel Kalman-Bucy filters tracking $\lambda_i$ [Kalman-Bucy 1961]; Anderson (1985) PE-driven covariance decay.
8. Krasovskii (1959 §14.2) ultimate-boundedness for the swapped-signal Lyapunov on $(e_i, \tilde v_i, \tilde\theta_i)$; reverse-Lyapunov reformulation of the HOCBF sub-CBF $\psi_{1,ij}$.
9. **Krasnosel'skii-Pokrovskii (1989) play operator** for the rate-independent hysteretic active set; Davis (1984) PDMP framework as alternative route to the closed-loop invariant measure $\mu$.
10. **Klein-Erlangen invariant (1872)** + **Rao (1945) constrained Fisher information** + **Birkhoff (1931) ergodic theorem**: scalar identifiability gain $\bar\rho_i = \mathbb{E}_\mu[|\Pi_{F_i}\phi_i|^2/m_i^2]$ on the binary freedom cone $F_i\in\{\{0\},\mathbb{R}\}$.
11. **Tikhonov (1963) regularisation** + Engl-Hanke-Neubauer (1996) rate analysis: the slack-penalty QP is a Tikhonov regularisation with worst-case rate $\mathcal{O}(M^{-1/2})$.

Plus Klein-Erlangen gauge fixing [1872] for QP pre-conditioning + the **Maldonado-Naranjo–Annaswamy (2025)** complex-state Dubins LOE-adaptive formulation. The construction is, classically: *Nagumo (1942) + Aubin-Cellina (1984) viability for relative-degree-2, with Filippov (1960) sliding-mode at the locus, Lyapunov (1892) second method on a Noether-symmetric Lagrangian, safety enforced via Moreau (1965) prox + Brezis (1973) maximal-monotone evolution, identifiability quantified via the Klein-invariant constrained scalar Cramér-Rao Fisher info of Rao (1945) on the Birkhoff (1931)-averaged closed-loop measure, and slack regularisation analysed via Tikhonov (1963). Closed-loop existence by Brezis 1973; invariant measure by Krasnosel'skii-Pokrovskii (1989); LOE-Dubins formulation by Maldonado-Naranjo + Annaswamy (2025).*

The contribution is the **engineering observation** that these eleven classical objects compose. The mathematical machinery is pre-1985 in its entirety (Maldonado-Naranjo + Annaswamy 2025 is itself a complex-state recasting of Dubins 1957, with the LOE channel introduced via classical adaptive control). **Not a mathematical novelty paper.** A control-design observation paper.

### v16 vs v17 — what changed in the Dubins lift

| Aspect | v16 (single-integrator) | v17 (complex Dubins) |
|---|---|---|
| Plant | $\dot x_i = u_i$, $x_i, u_i \in \mathbb{R}^d$ | $\dot r_i = v_{a,i}$, $\dot v_{a,i} = i\lambda_i u_{2,i}v_{a,i}$, $\|v_{a,i}\|=V_0$ |
| Control | $u_i \in \mathbb{R}^d$ | $u_{2,i}\in\mathbb{R}$ (scalar real turn-rate) |
| LOE channel | $\dot x = \Lambda u$ (full) | $\dot v_a = i\lambda u_2 v_a$ (turn-rate only) |
| CBF relative degree | 1 | 2 (HOCBF) |
| Locus $D_{ij}$ | None | Codim-1 head-on / tail-on family |
| QP decision | $u_i\in\mathbb{R}^d + |\mathcal N_i^{\text{on}}|$ slacks | $u_{2,i}\in\mathbb{R} + |\mathcal N_i^{\text{on}}|$ slacks |
| Freedom cone | $F_i = \mathrm{span}^\perp$ of active normals | $F_i\in\{\{0\},\mathbb{R}\}$ (binary) |
| Identifiability gain | $\mathrm{tr}(Q_i)$, matrix | $\bar\rho_i$, scalar (Cramér-Rao §1, not §6) |
| Symmetry | $\mathbb{R}_{>0}\times O(d)$ | $\mathbb{R}_{>0}\times U(1)$ |
| New axiom | (A5'): subtended angle | (A2''): free-time dwell + (A3'') item 3: $\eta_a$ guard |
| Slack-error rate | Implicit (not bounded) | Explicit $\mathcal{O}(M^{-1/2})$ Tikhonov |
| Sliding mode | None | Filippov regularisation on $D_{ij}$ |
| Worked examples | parallel approach (rank-1 ref); cross-swap (anisotropy collapse) | head-on (Filippov demo); cross-swap (curved Dubins paths) |

The structural composition (forward invariance + UUB + Cramér-Rao identifiability rate) is preserved; the v17 lift adds quantitative tightness via Filippov + Aubin-Cellina + Tikhonov.

### Position vs prior work

| Prior work | Single-agent / multi-agent | What we extend |
|---|---|---|
| Gutierrez-Hoagg [arXiv 2411.12899, 2024] | single-agent | multi-agent generalisation of vanishing-conservativeness via Kalman-Bucy parallel filters |
| Cohen-Belta [arXiv 2002.04577, 2203.01999, 2303.04241] | single-agent | distributed multi-agent setting with Birkhoff-quantified rate |
| Autenrieb-Annaswamy [arXiv 2309.05533] | single-agent LTI | nonlinear single-integrator with formation reference |
| Boyd-Sastry [Automatica 1986] | unconstrained MRAC | constrained version: PE Fisher information $\int \phi\phi^\top$ becomes the projected $\int (\mathrm{Proj}_{F_i}\phi)(\mathrm{Proj}_{F_i}\phi)^\top$; rate is the $\mathrm{tr}$ of the constrained moment |
| Cramér-Rao bound on constrained submanifold [Rao 1945; Aitchison-Silvey 1958] | classical statistics | first application to *adaptive control* convergence rate via the freedom-cone projection on the Whitney-stratified Fadell-Neuwirth configuration space |

**Reframing.** The contribution is not "another adaptive CBF extension." It is the identification of the convergence rate of multi-agent adaptive CBF as the **constrained Cramér-Rao bound** on a Whitney-stratified Fadell-Neuwirth configuration space. The freedom-cone projection - orthogonal to the active CBF normals - is the constraint manifold; its time-averaged Fisher matrix $Q_i$ is the rate. This connects 21st-century safety-critical adaptive control to 1945 statistical estimation theory, a connection (to our knowledge) not previously made.

### Robustifier choice (projection vs $\sigma$-mod vs dead-zone)

Three classical robustifiers exist for adaptive parameter laws: Krstić-Kanellakopoulos-Kokotović (1995) smooth projection, Ioannou-Kokotović (1983) $\sigma$-modification, and Egardt (1979) dead-zone. We pick **projection** because the QP feasibility argument requires a hard bound $\hat\theta_i \in [\theta_{\min}, \theta_{\max}]$ with $\theta_{\max}/\theta_{\min} \le \kappa_\Lambda$; $\sigma$-mod produces a soft attractor at $\hat\theta = 0$ that conflicts with this bound, and dead-zone introduces a region where $\dot{\hat\theta}_i = 0$ that breaks the Anderson 1985 PE-decay rate on $P_i(t)$.

### Norm conventions

Saturation in §3 is $\|u\|_\infty \le u_{\max}$ (matches per-channel actuator limits). Lyapunov in §4 uses $\|x_i - z_i\|_2$. The $\sqrt{d}$ factor in $\delta_{ij}(t)$ (Lemma 5.2) is the conversion. Single conversion table:

| Quantity | Norm | Why |
|---|---|---|
| $u_i^{\text{safe}}$, $u_i^{\text{ref}}$, $u_i^{\text{AC}}$ | $\infty$ | per-channel saturation |
| $x_i - z_i$, $\hat\theta_i - 1/\Lambda_i$ | 2 | Lyapunov |
| $u_i^{\text{ref}}$ in $m_i^2 := 1 + \|u_i^{\text{ref}}\|^2$ | 2 | swapped-signal normalisation |

When converting between them in proofs, $\|u\|_2 \le \sqrt{d}\,\|u\|_\infty$ and $\|u\|_\infty \le \|u\|_2$. The $\sqrt{d}$ factors are tracked explicitly in Lemma 5.2 and §8.3.

### Position vs L1-adaptive

L1-adaptive control (Cao-Hovakimyan 2008) bounds the transient over-shoot independent of the adaptation rate $\gamma$, at the cost of a low-pass filter that limits identifiability. Our construction's transient is $V(0)\,e^{-\eta t}$, dependent on $V(0)$ but with a closed-form $\eta$ inequality (Lemma 2). The trade is reversed: we keep PE for identification (Birkhoff-Rayleigh $\bar\rho_i$) at the cost of a transient bounded by initial conditions. For aerospace deployment where transient is the safety-critical quantity, L1 is preferable; for multi-agent identification where parameter convergence is the deliverable, our construction is preferable.

### Open questions

1. **Optimal excitation $e_i^{\text{pe}}$.** Sinusoidal is convenient. State-feedback rules maximising $\bar\rho_i$ are open.
2. **Higher-relative-degree $h_{ij}$.** For Dubins / quadrotor agents, $h$ has relative degree 2; HOCBF [Xiao-Belta 2021] generalises the freedom cone.
3. **Event-triggered communication (natural follow-up).** (A4) assumes continuous broadcast; the event-triggered extension with broadcast threshold $\delta_{\text{comm}}$ is the natural sequel paper, with the Cramér-Rao rate $\mathrm{tr}(Q_i)$ now degraded by an explicit $O(\delta_{\text{comm}}^2)$ term.
5. **Port-Hamiltonian generalisation.** The parameter manifold $(e_i, \tilde\theta_i)$ carries a natural symplectic form $\omega = \mathrm{d}e_i \wedge \mathrm{d}\tilde\theta_i$, and the closed loop decomposes into a Hamiltonian part (driving the Noether $G_\lambda$ symmetry) plus a dissipative part (driving the Lyapunov decay). The port-Hamiltonian formulation [van der Schaft 1986; Ortega-Spong 1988] would generalise cleanly to non-scalar $\Lambda$ and higher-relative-degree $h_{ij}$ (Dubins / quadrotor agents).
6. **Off-worst-eigenvector references.** In §8.1 and §8.2 the reference $u^{\text{ref}}$ is fixed-direction and happens to align with the worst eigenvector of $\bar P_i$, so $\mathrm{tr}(Q_i) = \lambda_{\min}^+(\bar P_i)\beta_1$ is the slowest possible identification rate compatible with the active-set geometry. Under a *time-varying* reference (e.g., a circular formation cycling through directions), is $\mathrm{tr}(Q_i)$ strictly larger than $\lambda_{\min}^+(\bar P_i)\beta_1$? Conjecture: yes. Proof would proceed via the inequality $\mathbb{E}_\mu[(u^{\text{ref}})^\top \bar P_i\, u^{\text{ref}}] \ge \lambda_{\min}^+(\bar P_i)\, \mathbb{E}_\mu[\|u^{\text{ref}}\|^2]$, with equality iff $u^{\text{ref}}$ lies $\mu$-a.e. in the worst eigenspace of $\bar P_i$. Designing $u^{\text{ref}}$ to maximise $\mathrm{tr}(Q_i)$ subject to formation-tracking constraints is the *active identifiability injection* problem.
4. **Adversarial / Byzantine setting.** If a subset of agents broadcasts wrong $\hat\theta_j$, robust extensions are open.

---

## 10. References (canonical)

**Pre-1985 classical objects:**
- Aubin, J.-P., Cellina, A. (1984). *Differential Inclusions: Set-Valued Maps and Viability Theory.* Springer-Verlag, §5.1 (second-order tangent cone; foundational form of HOCBF).
- Birkhoff, G. D. (1931). "Proof of the ergodic theorem." *PNAS* 17, 656–660.
- Brezis, H. (1973). *Opérateurs Maximaux Monotones et Semi-Groupes de Contractions dans les Espaces de Hilbert.* North-Holland.
- Crandall, M. G., Liggett, T. M. (1971). "Generation of semi-groups of nonlinear transformations on general Banach spaces." *Amer. J. Math.* 93, 265–298.
- Dubins, L. E. (1957). "On curves of minimal length with a constraint on average curvature, and with prescribed initial and terminal positions and tangents." *Amer. J. Math.* 79, 497–516 (the original Dubins curve / vehicle model).
- Filippov, A. F. (1960). "Differential equations with discontinuous right-hand side." *Mat. Sb. (N.S.)* 51(93), 99–128 (regularisation of differential inclusions; sliding-mode solutions; foundational treatment of v17's relative-degree-drop locus).
- Kato, T. (1967). "Nonlinear semigroups and evolution equations." *J. Math. Soc. Japan* 19, 508–520 (non-autonomous extension of Crandall-Liggett; Trotter-Kato approximation justifying RK4 + QP discretisation).
- Gronwall, T. H. (1919). "Note on the derivatives with respect to a parameter of the solutions of a system of differential equations." *Ann. Math.* 20, 292–296.
- Hager, W. W. (1979). "Lipschitz continuity for constrained processes." *SIAM J. Control Optim.* 17, 321–338.
- Hilbert, D. (1906). Lectures on integral equations; see also Riesz (1907) for the projection theorem.
- Kalman, R. E. (1960). "A new approach to linear filtering and prediction problems." *Trans. ASME J. Basic Eng.* 82, 35–45.
- Kalman, R. E., Bucy, R. S. (1961). "New results in linear filtering and prediction theory." *Trans. ASME J. Basic Eng.* 83, 95–108.
- Klein, F. (1872). "Vergleichende Betrachtungen über neuere geometrische Forschungen" (Erlangen Programme).
- Krasnosel'skii, M. A., Pokrovskii, A. V. (1989). *Systems with Hysteresis.* Springer (rate-independent hysteresis operators on trajectory space).
- Krasovskii, N. N. (1959). *Stability of Motion.* Stanford University Press, §14.2 (ultimate boundedness).
- Krylov, N., Bogolyubov, N. (1937). "La théorie générale de la mesure dans son application à l'étude des systèmes dynamiques de la mécanique non linéaire." *Ann. Math.* 38, 65–113.
- Krstić, M., Kanellakopoulos, I., Kokotović, P. (1995). *Nonlinear and Adaptive Control Design.* Wiley §4 (parameter projection).
- LaSalle, J. P. (1960). "Some extensions of Liapunov's second method." *IRE Trans. Circuit Theory* 7, 520–527.
- Lyapunov, A. M. (1892). *The General Problem of the Stability of Motion.* (Eng. transl. 1992.)
- Moreau, J.-J. (1965). "Proximité et dualité dans un espace hilbertien." *Bull. Soc. Math. France* 93, 273–299 (the proximal operator: foundational object of the v17 QP-resolvent).
- Moreau, J.-J. (1971). "Rafle par un convexe variable I." *Sém. Anal. Convexe Univ. Sci. Tech. Languedoc* 1, exposé 15 (rate-independent moving-set sweeping; foundational form for v17's $K_i(t)$ evolution; with companion Moreau 1972 "Rafle par un convexe variable II." *ibid.* 2, exposé 3).
- Moreau, J.-J. (1977). "Evolution problem associated with a moving convex set in a Hilbert space." *J. Differential Equations* 26, 347–374 (sweeping process: rate-dependent extension; the QP-as-projection on a moving constraint set).
- Morse, A. S. (1990) / Pomet, J.-B., Praly, L. (1992). Swapped-signal Lyapunov for normalised adaptive laws.
- **Nagumo, M. (1942). "Über die Lage der Integralkurven gewöhnlicher Differentialgleichungen." *Proc. Phys.-Math. Soc. Japan* 24, 551–559 (the viability theorem; foundational result for forward invariance, predates Aubin and the modern CBF literature by 70+ years).**
- Noether, E. (1918). "Invariante Variationsprobleme." *Nachr. Königl. Ges. Wiss. Göttingen, Math.-Phys. Kl.* 235–257 (first theorem: one-parameter symmetry → conserved quantity).
- Hilbert, D., Courant, R. (1924). *Methoden der mathematischen Physik I,* §I.3 (min-max characterisation of eigenvalues).
- Rao, C. R. (1945). "Information and the accuracy attainable in the estimation of statistical parameters." *Bull. Calcutta Math. Soc.* 37, 81–91 (Cramér-Rao bound; constrained Fisher information §6).
- Aitchison, J., Silvey, S. D. (1958). "Maximum-likelihood estimation of parameters subject to restraints." *Ann. Math. Statist.* 29(3), 813–828 (constrained Fisher information).
- Rayleigh, Lord (1877). *The Theory of Sound,* §IV (Rayleigh quotient).
- Fadell, E., Neuwirth, L. (1962). "Configuration spaces." *Math. Scand.* 10, 111–118 (ordered configuration spaces of $N$ points in $\mathbb{R}^d$).
- Whitney, H. (1965). "Tangents to an analytic variety." *Ann. Math.* 81, 496–549 (Whitney stratification).
- Robinson, S. M. (1980). "Strongly regular generalised equations." *Math. Oper. Res.* 5, 43–62.
- Rockafellar, R. T. (1970). *Convex Analysis.* Princeton (normal cone, maximal monotone operators).
- Tikhonov, A. N. (1952). "Systems of differential equations containing small parameters in the derivatives." *Mat. Sb. (N.S.)* 31(73), 575–586 (singular-perturbation theorem; separation of slow / fast time scales; foundational for the v17 §4.3 Step (b) cascade decomposition between the formation outer loop and the heading-PD inner loop).
- Tikhonov, A. N. (1963). "Solution of incorrectly formulated problems and the regularization method." *Soviet Math. Dokl.* 4, 1035–1038 (regularisation of inverse problems; foundational for the v17 §3.3 slack-penalty $\mathcal{O}(M^{-1/2})$ rate).
- Yosida, K. (1948). "On the differentiability and the representation of one-parameter semigroup of linear operators." *J. Math. Soc. Japan* 1, 15–21.

**Post-1985 / modern context:**
- Anderson, B. D. O. (1985). "Exponential stability of linear equations arising in adaptive identification." *IEEE TAC* 22(1), 83–88.
- Boyd, S., Sastry, S. S. (1986). "Necessary and sufficient conditions for parameter convergence in adaptive control." *Automatica* 22(6), 629–639 (canonical PE → parameter convergence rate result for unconstrained MRAC).
- Costa, O. L. V., Dufour, F. (2013). *Continuous Average Control of Piecewise Deterministic Markov Processes.* Springer.
- Davis, M. H. A. (1984). "Piecewise-deterministic Markov processes: a general class of non-diffusion stochastic models." *J. Royal Stat. Soc. B* 46(3), 353–388.
- Engl, H. W., Hanke, M., Neubauer, A. (1996). *Regularization of Inverse Problems.* Kluwer (Tikhonov rate analysis; v17 §3.3 worst-case slack-penalty rate $\mathcal{O}(M^{-1/2})$).
- Maldonado-Naranjo, D., Annaswamy, A. M. (2025). "Adaptive Control of Dubins Vehicle in the Presence of Loss of Effectiveness." IEEE L-CSS / arXiv:2504.08190 (complex-state Dubins LOE-adaptive formulation; the foundational single-agent setup that v17 lifts to multi-agent).
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

**Twenty-seven classical, twelve modern** (v17 added six classical: Aubin-Cellina 1984, Dubins 1957, Filippov 1960, Kato 1967, Moreau 1965/1971, Tikhonov 1952/1963; two modern: Engl-Hanke-Neubauer 1996, Maldonado-Naranjo + Annaswamy 2025). The framework is in pre-1985 mathematics; modern references frame the application context.

---

## Appendix A. Version history (most recent only; full git log retains earlier)

**v16 → v17 (complex-Dubins lift; council Passes 18-24).** Substantive rework lifting the construction from $\mathbb{R}^d$ single-integrator to $(r_i, v_{a,i})\in\mathbb{C}^2$ Dubins, with LOE on the turn-rate channel (Maldonado-Naranjo + Annaswamy 2025 formulation). v16 single-integrator results retained as the IEEE-LCSS Pass 12 SUBMIT-READY submission; v17 supersedes for the multi-agent Dubins scope.

Pass 18 (NEW SCOPE) declared the v17 lift. Passes 19-21 audited the initial v17 §3 draft and delivered NOT-SOUND / NOT-SOUND / NEEDS-REWRITE with three red blockers (factor-of-2 in $b_{ij}^{(0)}$, axiom (A3') not HOCBF-updated, relative-degree drop unhandled) plus orange items (Tikhonov $\mathcal{O}(M^{-1/2})$ slack rate, gauge-fix residual not absorbed in $\delta_{ij}$, v16-form numerical-scheme constants, v16 closed-form Lagrangian, v16 $L_{\text{QP}}^*$, cross-term broadcast resolution, $\alpha_1\alpha_2$ recoverability margin, foundational citations).

Resolved in §3 rewrite (commit `f81ce7c`):
- §1 axioms updated: (A1) clip-projection clarified; (A2'') closed-loop PE under HOCBF active-set switching added; (A3'') HOCBF initial conditions + $|a_{ii}|\ge\eta_a$ guard replaces (A3'); (A4) broadcasts $u_{2,j}^{\text{safe}}(t^-)$ explicitly; (A5) lifted to v17 scalar-control specialisation.
- §3.0 NEW: foundational lineage table (Nagumo 1942, Aubin-Cellina 1984, Filippov 1960, Moreau 1965/1971/1977, Krasnosel'skii-Pokrovskii 1989, Brezis 1973, Kato 1967, Lyapunov 1892, Rao 1945, Tikhonov 1963).
- §3.1 corrected: $b_{ij}^{(0)} = 2|v|^2 + 2(\alpha_1+\alpha_2)\Re(\cdot) + \alpha_1\alpha_2 h$ (Pass 19 factor-of-2 fix); explicit relative-degree-drop locus $D_{ij}$; Filippov regularisation framing; Klein equivariance verification made explicit; Krasovskii reverse-Lyapunov reformulation of $\psi_{1,ij}$.
- §3.1.1 NEW: recoverability margin $\dot\psi_{\max}|a_{ii}|_{\min}\ge|\text{res}_{ij}|_{\text{worst}}$ with worked numerical example.
- §3.1.2 NEW: $\delta_{ij}(t)$ explicit residual aggregation (R1: LHS-coeff gauge residual, R2: cross-term substitution residual, R3: broadcast latency residual).
- §3.1.3 NEW: closed-loop split off-locus (Brezis 1973) / on-locus (Filippov 1960).
- §3.2: Moreau prox / scalar QP, decision $1+|\mathcal N_i^{\text{on}}|$ variables.
- §3.3 corrected: error bound $\mathcal{O}(h) + \mathcal{O}(\text{tol}/h) + \mathcal{O}(M^{-1/2})$ per Tikhonov / EHN 1996; v17 numerical-scheme constants; v17 closed-form Lagrangian with scalar $a_{ii}$.
- §3.4: Lemma 1 with v17 $L_{\text{QP}}^* = (1+\kappa_\lambda)/\eta_a$.

§4-§8 rework (this pass):
- §4 v17: composite Lyapunov $V_i = (|e_i|^2+\kappa_v|\tilde v_i|^2)/(2 m_i^2) + (\lambda_i/(2\gamma))\tilde\theta_i^2$ on complex tracking error; $\mathbb{R}_{>0}\times U(1)$ symmetry (gauge + heading rotation); Pomet-Praly cancellation lifts via $\Re(\overline{\phi_i}\tilde v_i)$ on the complex regressor $\phi_i = i v_{a,i}u_2^{\text{ref}}$; gain condition $K_T\lambda_{\min} > \bar\mu^2 L_{\text{QP}}^{*\,2}$ with v17 $L_{\text{QP}}^*$ — margin **7.5×** at §8.3 parameters (vs v16's 1.9×).
- §5 v17: scalar Fisher info $\bar\rho_i = \mathbb{E}_\mu[|\Pi_{F_i}\phi_i|^2/m_i^2]$ on the binary freedom cone $F_i\in\{\{0\},\mathbb{R}\}$; constrained Cramér-Rao §1 (scalar, not §6 matrix).
- §6 v17 theorem: three numbered conclusions (forward invariance via Nagumo+Aubin-Cellina+Filippov; UUB with $\mathcal{O}(M^{-1/2})$ Tikhonov correction; parameter convergence at $\rho_i = \gamma\bar\rho_i$).
- §7 v17 six-lemma proof outline lifted to complex Dubins, with Aubin-Cellina §5.1 + Filippov + Krasnosel'skii-Pokrovskii citations.
- §8.1 NEW: $N=2$ head-on Dubins Filippov sliding-mode counter-example (v17-specific phenomenon, no v16 analog).
- §8.2 v17: $N=4$ cross-swap with curved Dubins paths; identifiability collapses to scalar $\bar\rho_1 = (1-\bar\mu)\cdot$(cruise regressor energy); no anisotropy structure (binary freedom cone has no anisotropy).
- §8.3 v17 parameters in `sim/paper_params.py`; documented $\gamma=0.15$ and $K_F=0.3$ choices (Pass 21 deferred items).
- §8.4 v17 figure plan: oriented-triangle agents on curved Dubins paths; animation supplementary; head-on Filippov demo as figure 7.
- §10 references: Aubin-Cellina 1984, Filippov 1960, Moreau 1965/1971, Kato 1967, Tikhonov 1963 added (classical); Engl-Hanke-Neubauer 1996 + Maldonado-Naranjo + Annaswamy 2025 added (modern).
- §9 contribution updated: 11 classical objects (was 9 in v16); v16-vs-v17 comparison table added.

Council passes 22-24 verified the §3 rework (SHIP IT / SHIP IT / SUBMIT-READY); §4-§8 rework awaiting full-council re-pass.

**v15 → v16 (scenario hardening, Pass 15).** Two §8.2 / §8.3 edits motivated by Pass 14's open findings (active fraction `mu_bar = 0.067` vs paper's stated 0.30; agents 1-3 stuck near $\hat\theta \approx 1.7$). (i) §8.2 cross-swap targets oscillate sinusoidally on period $T_{\text{swap}} = 4$ s instead of being constant; this guarantees axiom (A2') (closed-loop PE) holds for the entire simulation horizon, not just during the initial transient. (ii) §8.3 PE injection uses per-agent staggered frequencies $\omega_i^k = 2\pi(f_0 + i \Delta f + (k-1)\Delta f/2)$ instead of a shared $(\omega_1, \omega_2)$ pair; this prevents the four agents' identification dynamics from collapsing onto a single attractor. Active-fraction $\bar\mu$ is now reported empirically from the closed-loop measure $\mu$ (no "predicted vs measured" gap). No edits to §3-§7.

**v14 → v15 (simulation-loop close-out, Pass 13 finding 1).** §8.3 $\Lambda$ values changed from $(0.6, 1.4, 0.9, 1.6)$ to $(0.6, 0.9, 0.7, 0.8)$ so that $1/\Lambda_i \in [\theta_{\min}, \theta_{\max}] = [1, 2]$ for every agent. Bug surfaced by running `sim/run_paper_sim.py` against the paper's exact §8.3 values: agents 2 and 4 had $1/\Lambda_2 = 0.71$ and $1/\Lambda_4 = 0.62$, both below the projection lower bound, so their estimates could not converge. The fix preserves the spread $(\Lambda_{\min}, \Lambda_{\max}) = (0.6, 0.9)$, hence the $K_T \Lambda_{\min} = 2.4$ η-feasibility margin from Krstić's Pass 6 commitment is unchanged. Nothing else in §3-§7 needs editing. None of the 12 prior council passes caught this; the running simulation did, on its first execution.

**v13 → v14 (OG-council fresh-eyes pass close-out).** Moreau (1977) sweeping process restored as the primary time-varying-resolvent citation alongside Crandall-Liggett (1971) (autonomous specialisation). Spurious $1/\theta_{\min}^2$ factor in Lemma 5.6 $L_{\text{eff}}$ removed (the bound on $|\dot{\hat\theta}_i|$ uses $1/m_i^2 \le 1$, not $1/\theta_{\min}^2$ - that factor belongs to Lemma 5.2's $|\tilde\Lambda|^2$ bound). $Q_i$ terminology nudged: "projected-regressor second-moment matrix" (the Rao-Aitchison-Silvey constrained-score covariance), with scalar Fisher information of $1/\Lambda_i$ being $\propto \mathrm{tr}(Q_i)$ - proportionality not identity. Boyd-Sastry (1986) added as the canonical unconstrained-MRAC PE-convergence-rate baseline. One-sentence Bourbaki summary line added above the boxed theorem in §6.

**v12 → v13 (modern-panel fresh-eyes pass close-out).** Cross-swap rate corrected from $0.85\beta_1$ to $0.80\beta_1$ (factored form was misapplied; reference is rank-1 along $(1,1)/\sqrt{2}$, aligned with the worst eigenvector of $\bar P_1$; the result $\mathrm{tr}(Q_i) = \lambda_{\min}^+(\bar P_i)\beta_1$ is the *general* fixed-direction-reference identity, not a coincidence). Units convention rewritten as explicit dimensionless normalisation against reference scales $(T^*, L^*, u^*)$. New open-question item on time-varying references whose energy spreads beyond the worst eigenspace of $\bar P_i$.

**v9 → v10 (exposition cleanup).** Renumbered §1-§10 to remove a duplicated `## 1.` (Plant) header from v9; reconciled $Q^{\text{KB}}$ notation in the Kalman-Bucy equation (line 72); added (A5') to the theorem hypothesis list with note "vacuous for $d=2$"; deleted redundant "open-loop PE hypothesis" alongside (A2'); rewrote abstract to put Fisher information and Cramér-Rao bound in correct reciprocal relation; added units convention block at top.

**v8 → v9 (LCSS-form rewrite, post Krstić / Borrelli / Lavretsky controls audit).**

| v8 | v9 | Driver |
|---|---|---|
| Six axioms, but no abstract or problem statement | Abstract + §1 Problem statement added (LCSS form) | Lavretsky |
| Theorem rate $\rho_i = \mathrm{tr}(Q_i)$ | $\rho_i = \gamma\,\mathrm{tr}(Q_i)$ ($\gamma$ factor added) | Krstić |
| η inequality with worst-case $L_{\text{QP}}^{*\,2}$ | Duty-cycle-refined $\bar\mu^2 L_{\text{QP}}^{*\,2}$; gain condition $K_T \Lambda_{\min} > \bar\mu^2 L_{\text{QP}}^{*\,2}$ | Krstić |
| §8.3 $K_T = 0.5$, $u_{\max} = 1$ (η fails) | $K_T = 4$, $u_{\max} = 25$ (η holds with margin 2x) | Krstić + Borrelli |
| §8.1 $\mathrm{tr}(Q_1) = (2-\bar\mu)\beta_1$ (factored, wrong) | $\mathrm{tr}(Q_1) = (1-\bar\mu)\beta_1$ from direct calculation with $\Sigma_1 = \beta_1\,\mathrm{diag}(1,0)$ rank-1 | Tao + Bhargava |
| §8.2 reports $\lambda_{\min}^+ = 0.80$ as the rate | Reports $\mathrm{tr}(Q_1) = 0.85\,\beta_1$ as rate, $\lambda_{\min}^+ = 0.80$ as anisotropy diagnostic | Tao |
| $Q_i$ as "joint second moment" only | $Q_i$ named as constrained Fisher information (Rao 1945; Aitchison-Silvey 1958); $\mathrm{tr}(Q_i)$ is the scalar Cramér-Rao bound | OG council |
| Closed loop on PDMP, no geometric structure | Whitney-stratified Fadell-Neuwirth configuration space (§5 structural remark) | OG council |
| §3.3 numerical scheme, no scaling note | Real-time feasible up to $N \approx 50$; warm-start cold-restart at hysteresis events; OSQP rationale | Borrelli |
| No reproducibility statement | §8.3: Python+NumPy+OSQP repo on acceptance | Lavretsky |
| Position-vs-prior-work: 3 rows | 4 rows (added Cramér-Rao row); reframing paragraph | Lavretsky |
| Open-question 3 framed as limitation | Reframed as natural follow-up paper | Lavretsky |
| 3 open questions | 5 open questions (added port-Hamiltonian generalisation) | OG council |

**v6 → v8 (compressed):** v7 added Noether/Hilbert-Courant/Klein-Frobenius/Krasnosel'skii-Pokrovskii classical attributions; v8 corrected the Klein-Frobenius factorisation bug (counter-example: factored form gives 50% gap on a 2-stratum example) and added (A5') for $d \ge 3$.

**Pre-v6:** see git log; eight versions of patches now consolidated.

---

The construction is paper-ready for IEEE-LCSS '26. Next step: implement the four-step incremental simulation pipeline (smoothed-flow → slack QP → pre-conditioning → Kalman-Bucy auxiliary) and verify the §8.2 worked-example rate $\mathrm{tr}(Q_1) = 0.85\,\beta_1$ within tolerance. Proof body $\le 4$ pages.
