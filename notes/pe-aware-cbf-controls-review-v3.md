# Controls-Expert Review of v3 (post-Bourbaki rewrite)

**Document under review:** `notes/pe-aware-cbf-theorem.md` (v3, commit `e4e3e37`).
**Focus:** engineering implementability, numerical conditioning, realistic checks, IEEE-LCSS / CDC submission readiness.
**Panel (this round):** Tomlin, Lavretsky, Wise.

---

## Review - Claire Tomlin

### Overall Assessment
The Bourbaki rewrite is a step forward: the closed loop is now framed as a maximal-monotone differential inclusion with the QP as the Yosida resolvent, which gives forward-invariance under hysteretic switching for free. But submission-readiness is held back by under-specified discrete logic at the active-set boundary, an unproven dwell-time claim, and a theorem statement that hides the most fragile hypothesis (initial feasibility of the QP after tightening) inside a parenthetical in §6.

### Findings

#### 🔴 BLOCKER - Initial QP feasibility is asserted, not proven
**Location:** §6 Lemma 5.2, last sentence; (A3); §7.3.
**Issue:** The text claims "the required prior tightness $\theta_{\max}/\theta_{\min} \le \kappa_\Lambda$ ensures $\delta_{ij}(0) < r_{\text{safe}}^2 \cdot$ (numerical factor) so the QP is initially feasible," and §7.3 picks $\kappa_\Lambda = 2$ giving $\delta_{ij}(0) < r_{\text{safe}}^2/4$ "for typical $D_{\max} \approx 6$." But (A3) only assumes $h_{ij}(x(0)) > 0$, not $h_{ij}(x(0)) \ge $ (the numerical factor) $\cdot \delta_{ij}(0)/r_{\text{safe}}^2$. A reviewer can construct $x(0)$ with $h_{ij}(x(0)) = \varepsilon_0$ arbitrarily small, satisfying (A3), yet making the slack $s_{ij}(0)$ unboundedly active and breaking the asserted "$M \to \infty$ recovers hard-constrained solution where feasible" clause.
**Fix:** Replace (A3) with **(A3')** $h_{ij}(x(0)) \ge \delta_{ij}(0) + \zeta$ for some margin $\zeta > 0$, *and* state the inequality $\delta_{ij}(0) \le \tfrac12 r_{\text{safe}}^2$ explicitly as a precondition on the data, not as a derived fact. Then Lemma 5.2 can claim $h_{ij}(t) \ge \zeta\,e^{-\alpha t}$ as a corollary.

#### 🟠 MAJOR - Hysteresis-implies-no-Zeno is cited, not proved for this system
**Location:** §2.1, "Hysteresis rules out Zeno chattering [Liberzon 2003 §1.2]".
**Issue:** Liberzon §1.2 covers hysteresis on a *single* switching surface in a *single* state. Here we have $\binom{N}{2}$ pairs, each with its own hysteretic active set, and the engagement event of pair $(i,j)$ can trigger an immediate disengagement of pair $(i,k)$ via the QP's redistribution of $u_i$. Multi-surface hysteresis with cross-coupling needs a dwell-time bound that depends on the QP's Lipschitz constant, the maximum constraint-gradient inner product, and the threshold $\varepsilon$. Without this, a CDC reviewer will reject "no Zeno" as folklore.
**Fix:** Add a **Lemma 5.6 (uniform dwell-time bound)** stating that under the hysteresis thresholds $(\varepsilon, 2\varepsilon)$, the inter-event time is bounded below by $\tau_d \ge \varepsilon / (L_u \cdot \max_j \|2(x_i - x_j)\|)$, where $L_u$ is the Lipschitz constant of $u_i^{\text{safe}}$ from Lemma 1. The proof is two lines from Hager (1979).

#### 🟠 MAJOR - The three-sentence theorem omits the broadcast-delay assumption
**Location:** §5 Theorem statement; (A4).
**Issue:** (A4) assumes *continuous-time* broadcast of $\{x_j, \hat\theta_j\}$. The theorem statement says "Under axioms (A1)-(A4)" without flagging that conclusion (1) (safety) breaks under any positive transport delay, because the QP solves with $x_j(t - \tau)$ instead of $x_j(t)$, and the constraint becomes $c_{ij}^{\text{delayed}} \ge \delta_{ij}(t)$ which is not a valid CBF tightening of the *true* constraint. The §8 "Open questions" item 3 acknowledges this only as future work, but the theorem as written would be safety-misleading if quoted without (A4) attached.
**Fix:** Move (A4) into the theorem hypothesis line explicitly: "Under (A1)-(A3) and **continuous-time neighbour broadcast (A4)**, ..." A reviewer will either accept it as a clearly-stated limitation or demand a robust extension; either is fine, but it must not hide.

#### 🟡 MINOR - Hysteresis threshold $\varepsilon$ is not sized
**Location:** §2.1.
**Issue:** "$\varepsilon \ge \delta_{ij}(t) + $ solver tolerance" is a lower bound but no upper bound; pick $\varepsilon$ too large and the active set engages before any safety risk and the QP unnecessarily restricts excitation.
**Fix:** Recommend $\varepsilon \in [\delta_{ij}(t) + \text{tol},\, 0.1 \cdot r_{\text{safe}}^2]$ as a concrete tuning range; flag as a hyperparameter in §7.3.

#### 🟡 MINOR - Forward-invariance constant $\alpha$ is conflated with the CBF class-$\mathcal{K}$ slope
**Location:** §2.1 vs §6 Lemma 5.1.
**Issue:** $\alpha = 10$ in §7.3 is the linear class-$\mathcal{K}$ gain in the ZCBF condition $\dot h + \alpha h \ge 0$, but the symbol $\alpha$ is not introduced in §2.1 where the constraint $c_{ij}$ is written. The reader who jumps from §2 to §7 has to deduce that $\alpha h_{ij}(x)$ is the standard ZCBF additive term.
**Fix:** Sentence under (68): "where $\alpha > 0$ is the linear class-$\mathcal{K}$ gain of the ZCBF (Ames-Xu-Grizzle 2014 eq. 14)."

#### 🔵 INFO - Reachability connection
**Suggestion:** Conclusion (1) is forward-invariance, not reachability. A nice add for the discussion is: the maximal monotone semigroup defines a Hamilton-Jacobi value $V_{\text{reach}}(x) = \inf_{u \in K(t,x)} \|x - x^*\|^2$ whose sub-level sets are the safe set, and the QP solves the time-discrete HJB with $h$ as the time step. Cite Mitchell-Bayen-Tomlin (2005) for the bridge. Optional and adds nothing to the proof but helps a reachability-trained reviewer see why the construction is sound.

### Summary of Key Actions
- Replace (A3) with (A3') including margin $\zeta$.
- Add Lemma 5.6 dwell-time bound for multi-surface hysteresis.
- Promote (A4) into the theorem statement explicitly.
- Bound $\varepsilon$ from above and tabulate as a hyperparameter.
- Clarify that $\alpha$ is the ZCBF class-$\mathcal{K}$ gain.

---

## Review - Eugene Lavretsky

### Overall Assessment
The adaptive-CBF composition is principled and the Krasovskii ultimate-boundedness statement is correct in spirit, but the robustness margin claims are softer than they read. The Kalman-Bucy auxiliary is a nice addition for monitoring, however the *coupling* between the QP-induced perturbation and the swapped-signal Lyapunov decay rate is not bounded explicitly. For an LCSS submission this is acceptable; for a CDC robustness reviewer, expect questions about the implicit constants.

### Findings

#### 🔴 BLOCKER - Lemma 2's $\eta > 0$ is asserted, not constructed
**Location:** §3.1 Lemma 2, "for some $\eta > 0$ depending on $\Lambda_{\min}, \theta_{\max}, K_T, K_F$".
**Issue:** The decay constant $\eta$ controls the entire ultimate-boundedness statement and the $\mathcal{O}(A_e^2/\eta)$ steady-state error. Without a closed-form expression (or at least an inequality) relating $\eta$ to the four parameters, the user cannot tune the system. A robustness reviewer will demand $\eta \ge \Lambda_{\min}\cdot K_T - C(\theta_{\max}, K_F, \kappa_\Lambda)$ for an explicit $C$. The current text gives nothing.
**Fix:** Add to Lemma 2: $\eta \ge \Lambda_{\min} K_T - 2 K_F \cdot \deg(\mathcal{G}) \cdot \theta_{\max}^2/\theta_{\min}^2$, and state the precondition $K_T > 2 (K_F/\Lambda_{\min}) \cdot \deg(\mathcal{G}) \cdot \kappa_\Lambda^2$ for $\eta > 0$. (Verify the algebra during proof drafting; the form is the right shape.)

#### 🟠 MAJOR - "$Q \ge 0$ a small regularisation" is under-specified
**Location:** §1, Kalman-Bucy filter equation.
**Issue:** With $Q = 0$ the Riccati covariance shrinks to zero (good for asymptotics) but loses observability if PE drops out for any finite interval, since $P_i = 0$ becomes an absorbing state. With $Q > 0$ the steady-state covariance is $P_i^* = \sqrt{Q \cdot m_i^2 / \|u_i^{\text{ref}}\|^2}$ (scalar Riccati), bounded away from zero, which means $\delta_{ij}(t)$ does *not* vanish to zero - it floors at $\delta_{ij}^* > 0$, making conclusion (2) of the theorem $\mathcal{O}(\sup_i \|P_i\|^2) \to \mathcal{O}(P_i^{*2}) \ne 0$. The text says it vanishes; with $Q > 0$ it doesn't.
**Fix:** Either (a) set $Q = 0$ and add a "PE never drops" hypothesis (matches Anderson 1985), or (b) keep $Q > 0$ and rewrite conclusion (2) as $V(t) \le V(0)\,e^{-\eta t} + \mathcal{O}(A_e^2/\eta + Q)$. Pick one; the current text wants both.

#### 🟠 MAJOR - The QP-projection perturbation $\delta_i^{\text{QP}}$ is named but not bounded
**Location:** §3.1 sketch, "the QP-projection correction $\delta_i^{\text{QP}}$ ... contribute bounded perturbation terms".
**Issue:** Robust-adaptive convention requires an explicit bound $\|\delta_i^{\text{QP}}\| \le \beta(P_i, A_e, \theta_{\max})$ before invoking Young's inequality. Otherwise "bounded" is decoration. The Hager 1979 Lipschitz-of-QP-solution theorem gives this for free, but it must be cited *here*, not at Lemma 1.
**Fix:** Sketch sentence: "By Lemma 1 (Hager 1979), $\|\delta_i^{\text{QP}}\| \le L_{\text{QP}} \cdot (\|x_i - z_i\|/m_i + \delta_{ij}(t))$ with $L_{\text{QP}} = \kappa_\Lambda \cdot \deg(\mathcal{G})$. Young's inequality with weight $\eta/2$ then absorbs the $\|x_i - z_i\|$ term into the $-\eta\,\|x_i-z_i\|^2/m_i^4$ decay, leaving the $\delta_{ij}(t)^2$ residual which feeds the $\mathcal{O}(\sup_i \|P_i\|^2)$ term."

#### 🟡 MINOR - The "$\sigma$-modification" / dead-zone option is missing
**Location:** §1, parameter projection.
**Issue:** Krstić-Kanellakopoulos-Kokotović projection is one of three classical robustifiers; $\sigma$-modification (Ioannou-Kokotović 1983) and dead-zone (Egardt 1979) are the others. For an aerospace-leaning reviewer, the absence of a discussion of which one is most appropriate here will draw a comment.
**Fix:** One-paragraph remark in §8 explaining why projection is preferred (hard bound on $\hat\theta$ matches the strict prior tightness $\kappa_\Lambda$; $\sigma$-mod would relax it and conflict with the QP feasibility argument).

#### 🟡 MINOR - $L_\infty$ saturation in the QP vs $L_2$ in the Lyapunov
**Location:** §2 ($\|u\|_\infty \le u_{\max}$); §3 ($V_i$ uses $\|x_i - z_i\|^2$).
**Issue:** Mixing $\infty$- and 2-norms incurs constant factors $\sqrt{d}$ that show up in Lemma 5.2 ($\sqrt{d}\,u_{\max}$) but are not tracked elsewhere. A robustness reviewer who chases constants will find the $\sqrt{d}$ floats undocumented.
**Fix:** Either standardise to $\|u\|_2 \le u_{\max}$ (cleanest, marginally more conservative) or add a one-line table converting $\infty$- and 2-norm bounds. Also flag this in §7.3.

#### 🔵 INFO - L1-adaptive comparison
**Suggestion:** L1-adaptive theory bounds the transient over-shoot independently of the adaptation gain $\gamma$. The current construction's transient is bounded only by $V(0)$ and decays at rate $\eta$. A short paragraph in §8 contrasting with L1-adaptive (Cao-Hovakimyan 2008) would head off the obvious "why not L1?" reviewer comment.

### Summary of Key Actions
- Construct $\eta$ explicitly (or at least give a sufficient inequality).
- Decide between $Q = 0$ + PE-always or $Q > 0$ + non-vanishing floor; rewrite conclusion (2) accordingly.
- Bound $\delta_i^{\text{QP}}$ explicitly via Hager (1979) in the Lemma 2 sketch.
- Add one-paragraph remark on projection vs $\sigma$-mod vs dead-zone.
- Standardise $\infty$- vs 2-norm conventions.

---

## Review - Kevin Wise

### Overall Assessment
The Crandall-Liggett framing is mathematically attractive but engineering-speaking it just says "you do an implicit Euler step where the implicit step is a QP." That's fine, and it's how OSQP / qpOASES are already used inside ode15s wrappers in practice. However the document is silent on the actual integration scheme, the QP step size $h$, and the per-step solver budget; for a real CDC submission these are not optional. Also the figure plan looks reasonable but would not survive contact with simulator data without three more sweeps (delay tolerance, $Q$ sensitivity, and gain-margin) that the document doesn't currently promise.

### Findings

#### 🔴 BLOCKER - Integration scheme and step-size selection are unspecified
**Location:** §2.2 "the implicit-Euler scheme with the QP as the resolvent map"; entire document.
**Issue:** Crandall-Liggett's $\lim_{n \to \infty}$ is a continuous-time existence result, not an integration prescription. The simulation will pick a finite $h$. The convergence rate of the implicit-Euler scheme to the semigroup is $\mathcal{O}(h)$ on bounded intervals (Brezis 1973 Cor 4.2) under maximal-monotonicity, *but only if the QP is solved to accuracy $o(h)$*. This couples $h$ to the QP solver's stopping tolerance: if you run OSQP to $10^{-3}$ tolerance and pick $h = 10^{-2}$, the implicit-Euler error and the QP error are the same order and the safety margin is meaningless. There's no recommended pairing in the document.
**Fix:** Add §2.4 "Numerical scheme":
- Use an outer fixed-step integrator at $h_{\text{outer}} = 5 \times 10^{-3}$ s (matches existing repo); inside each step solve the QP to tolerance $10^{-7}$ (warm-started with previous solution).
- Justify with the inequality $\|x_n - x(t_n)\| \le C h_{\text{outer}} + (1/h_{\text{outer}}) \cdot \text{tol}_{\text{QP}}$ (Brezis 1973 Cor 4.2 + Hager 1979).
- Recommend OSQP (Stellato et al. 2020) for the per-agent QP; closed-form for $N=2$.
- Recommend ode15s (variable-step BDF) for the *outer* loop only if you need adaptive step sizing; otherwise fixed $h$ inside Simulink is faster and matches the analysis.

#### 🟠 MAJOR - Communication-delay tolerance is not tested in the figure plan
**Location:** §7.4.
**Issue:** (A4) is the most fragile axiom in deployment. Five figures and zero of them probe what happens when the broadcast latency is $5$ ms, $20$ ms, $100$ ms. A submission reviewer with an ICRA / IROS background will call this out immediately.
**Fix:** Add Figure 6: $\min_{ij} h_{ij}(t)$ vs. communication latency $\tau \in \{0, 5, 20, 50, 100\}$ ms, two scenarios (cross-swap, parallel approach), with annotation of the latency at which safety is first violated. This becomes the empirical robustness margin and is exactly what a deployment-oriented reviewer asks for.

#### 🟠 MAJOR - Slack penalty $M$ is not quantified
**Location:** §2.2, "$M \gg 1$"; §6 Lemma 5.4.
**Issue:** $M$ is the only parameter in the QP that controls "how much safety we are willing to violate when infeasible." Picking $M = 100$ vs $M = 10^4$ vs $M = 10^6$ produces wildly different transient behaviour. The text says "$M \to \infty$ recovers the hard-constrained solution where feasible" - true asymptotically, but a real solver returns $\|s_{ij}\|$ inversely proportional to $M$, and large $M$ ruins QP conditioning.
**Fix:** Recommend $M = 10^4$ as default (gives $\|s_{ij}\| \le 10^{-3}$ typical when not actually safety-critical, $\|s_{ij}\| \approx 10^{-1}$ when infeasible) and quantify the trade with QP condition number in §2.4. Pair with Wright 1997 §11.

#### 🟡 MINOR - "Closed-form for $N=2$" is true but the document doesn't say so
**Location:** §7 worked examples.
**Issue:** For $N=2$, $d=2$, single active constraint, the QP has a closed-form Lagrangian solution. This is good for unit-testing the implementation - simulate with closed-form, then with OSQP, and require agreement to $10^{-9}$. The document does not point this out.
**Fix:** Add to §7.1: "For this scenario, the QP admits the closed-form $u_i^{\text{safe}} = u_i^{\text{AC}} + \tilde e_i^{\text{pe}} + \mu_{ij}^* \cdot 2(x_i - x_j)$ with $\mu_{ij}^* = \max(0, [\delta_{ij} - c_{ij}(u_i^{\text{AC}} + \tilde e_i^{\text{pe}})] / \|2(x_i-x_j)\|^2)$. Use this as a unit test for the OSQP wrapper before scaling to $N \ge 3$."

#### 🟡 MINOR - Reproducibility hash / seed
**Location:** §7.3.
**Issue:** The simulation uses sinusoidal $e_i^{\text{pe}}$ - phase and frequency unspecified. Different choices give materially different $\bar\rho_i$.
**Fix:** Specify $e_i^{\text{pe}}(t) = A_e [\sin(\omega_1 t + \phi_i^1), \sin(\omega_2 t + \phi_i^2)]^\top$ with $\omega_1 = 2\pi \cdot 0.7$ Hz, $\omega_2 = 2\pi \cdot 1.1$ Hz, $\phi_i^k$ uniformly random in $[0, 2\pi)$ with seed $\texttt{rng(42)}$ (or numpy equivalent). One sentence; saves the reader 30 minutes of replicating-the-result.

#### 🔵 INFO - Submission target
**Suggestion:** The four-page bound mentioned in the closing line is realistic for IEEE-LCSS (8 pages typical, 4 pages of proof leaves 4 pages for setup + figures + discussion). For CDC the page budget is 6 + 2 references and the proof should be ~3 pages with the rest devoted to experiments. The current document maps cleanly to LCSS; for CDC, expect to cut the diff table (§10) and one of the worked examples.

### Summary of Key Actions
- Specify integration scheme (fixed $h_{\text{outer}}$, QP tolerance, solver pairing).
- Add Figure 6 (delay tolerance sweep).
- Quantify $M$ and document the conditioning trade.
- Add closed-form unit test for $N=2$.
- Specify excitation phases / frequencies / RNG seed.

---

## Consolidated Action List (All Reviewers)

| Priority | Issue | Raised By | Fix |
|---|---|---|---|
| 🔴 BLOCKER | Initial QP feasibility asserted, not proven | Tomlin | Replace (A3) with (A3'): $h_{ij}(0) \ge \delta_{ij}(0) + \zeta$ explicitly. |
| 🔴 BLOCKER | $\eta > 0$ in Lemma 2 not constructed | Lavretsky | Give explicit inequality: $\eta \ge \Lambda_{\min} K_T - 2 K_F \deg(\mathcal{G}) \kappa_\Lambda^2$. |
| 🔴 BLOCKER | Integration scheme + QP tolerance unspecified | Wise | Add §2.4: $h_{\text{outer}} = 5\text{ms}$, OSQP tol $10^{-7}$, Brezis Cor 4.2 + Hager 1979 error pairing. |
| 🟠 MAJOR | Multi-surface hysteresis dwell-time not proved | Tomlin | Add Lemma 5.6: $\tau_d \ge \varepsilon / (L_u \cdot D_{\max})$. |
| 🟠 MAJOR | (A4) continuous-broadcast hidden in theorem statement | Tomlin | Promote (A4) into the theorem hypothesis line. |
| 🟠 MAJOR | $Q \ge 0$ ambiguity (vanishing $\delta_{ij}$ vs. floor) | Lavretsky | Pick: $Q = 0$ + always-PE, or $Q > 0$ + revise conclusion (2). |
| 🟠 MAJOR | $\delta_i^{\text{QP}}$ bound not derived | Lavretsky | Cite Hager 1979 in Lemma 2 sketch with $L_{\text{QP}} = \kappa_\Lambda \deg(\mathcal{G})$. |
| 🟠 MAJOR | Communication-delay sweep missing from figure plan | Wise | Add Figure 6: safety vs. broadcast latency $\tau \in \{0,5,20,50,100\}$ ms. |
| 🟠 MAJOR | Slack penalty $M$ unquantified | Wise | Default $M = 10^4$; pair with QP condition number in §2.4. |
| 🟡 MINOR | Hysteresis $\varepsilon$ upper bound missing | Tomlin | Recommend $\varepsilon \in [\delta_{ij}+\text{tol},\, 0.1 r_{\text{safe}}^2]$. |
| 🟡 MINOR | $\alpha$ symbol introduced late | Tomlin | One-line gloss after eq. (68): "$\alpha$ = ZCBF class-$\mathcal{K}$ gain." |
| 🟡 MINOR | Projection vs $\sigma$-mod vs dead-zone not discussed | Lavretsky | One-paragraph remark in §8. |
| 🟡 MINOR | Mixed $\infty$- and 2-norm conventions | Lavretsky | Standardise or add conversion table; track $\sqrt{d}$ factors. |
| 🟡 MINOR | Closed-form $N=2$ QP unit-test not noted | Wise | Add explicit Lagrangian formula in §7.1. |
| 🟡 MINOR | Excitation phases / RNG seed unspecified | Wise | $\omega_1 = 2\pi(0.7)$, $\omega_2 = 2\pi(1.1)$, rng(42). |
| 🔵 INFO | HJB / reachability bridge | Tomlin | Cite Mitchell-Bayen-Tomlin 2005. |
| 🔵 INFO | L1-adaptive comparison | Lavretsky | One paragraph contrasting transient bound. |
| 🔵 INFO | LCSS vs CDC submission target | Wise | LCSS clean; CDC needs §10 cut + one worked example dropped. |

---

## Verdict

**SUBMIT-READY (LCSS) with three blocker fixes.** The Bourbaki rewrite is the right framing; the maximal-monotone + Crandall-Liggett + Birkhoff-Rayleigh + Klein-Erlangen scaffold composes cleanly and the proof outline is at most 4 pages. After fixing the three blockers (initial-feasibility margin, explicit $\eta$ inequality, numerical scheme spec), the document is paper-quality. The seven major findings are LCSS-survivable but CDC-mandatory.

Sign-off: Tomlin / Lavretsky / Wise concur.
