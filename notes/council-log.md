# Council Log - `pe-aware-cbf-theorem.md`

**Protocol:** every council-skill invocation (math-god-mode, OG-math-experts, controls-expert-reviewer) reads this log BEFORE the paper, classifies its findings as NEW / RECURRING-UNFIXED / CONFLICT-WITH-PRIOR-SIGNOFF, honours prior pre-commitments, and appends a new entry at the bottom. Persists across Claude sessions.

**Loop-break heuristic:** after 6+ passes with the most recent 3 all SOUND-or-better, councils default to SHIP IT and only flag genuinely blocking issues. New scope (e.g. "TAC submission" instead of "LCSS") resets the clock.

---

## Pass 1 - 2026-04-?? - math-god-mode (v6 close-out)
**Audited:** `notes/pe-aware-cbf-theorem.md` @ `7a8d520` (v6)
**Verdict:** SOUND with caveats
**Personas:** Tao, Annaswamy, Ames, Tomlin, Krstić
**Findings (summary):** η inequality wrong-form; (H5) closed-loop PE hidden; Krylov-Bogolyubov needs PDMP not Brezis §3.3; L_QP* needs Hager 1979 derivation; (A5) non-saturation must be explicit; dwell-time missing $\dot{\hat\theta}$ term; $D_{\max}$ non-circularity.
**Sign-off conditions:** "After all 7 items, modern panel will sign off."
**Status of prior commitments:** N/A (first pass)

## Pass 2 - 2026-04-?? - OG-math-experts (v6 → v7 reformulation)
**Audited:** `notes/pe-aware-cbf-theorem.md` @ `7a8d520`
**Verdict:** SOUND
**Personas:** Noether, Hilbert, Klein, Poincaré, Lyapunov
**Findings (summary):** classical attribution missing for swapped-signal (Noether 1918), formation Laplacian gain (Hilbert-Courant 1924), identifiability (Klein 1872 + Rayleigh 1877). Davis 1984 PDMP cleaner than Brezis §3.3 for hysteresis. ★ Foundational reformulation: identifiability is the Klein-invariant Frobenius inner product $\langle \bar P_i, \Sigma_i\rangle_F$.
**Sign-off conditions:** "After 4 OG attributions added, OG council signs off."
**Status of prior commitments:** Pass 1 modern-panel commitment: PENDING (user will fix in v7).

## Pass 3 - 2026-04-?? - math-god-mode (v7 verification)
**Audited:** v7
**Verdict:** NOT SOUND
**Personas:** Tao, Annaswamy, Ames
**Findings:** ❌ Klein-Frobenius factorisation $\bar\rho_i = \langle \bar P_i, \Sigma_i\rangle_F$ is FALSE in general (counter-example: 2-stratum with 50% gap). Expectation of product ≠ product of expectations when projector and reference are correlated under $\mu$.
**Sign-off conditions:** "After Q_i correction (single joint moment) + (A5') for $d \ge 3$, panel signs off."
**Status of prior commitments:** Pass 2 OG commitment: HONOURED (4 attributions present); but Pass 2's Klein-Frobenius proposal turned out to be WRONG and Pass 3 catches it.

## Pass 4 - 2026-04-?? - math-god-mode (v8 verification)
**Audited:** v8 (Q_i joint-second-moment correction applied)
**Verdict:** SOUND
**Personas:** Tao, Bhargava, Annaswamy, Ames
**Findings:** none blocking; ⚠ §7.1 number "(2-μ̄)β_1" is wrong, should be "(1-μ̄)β_1" with rank-1 Σ_1 explicit; ⚠ section 7.2 reframe needed.
**Sign-off conditions:** "After numerical fixes in §7.1, §7.2 + housekeeping, panel signs off."
**Status of prior commitments:** Pass 3 commitment: HONOURED (Q_i is correct single-moment object; (A5') added).

## Pass 5 - 2026-04-?? - OG-math-experts (v8 verification, Cramér-Rao naming)
**Audited:** v8
**Verdict:** SOUND with caveats
**Personas:** Cramér, Rao, Riemann, Whitney, Noether, Lyapunov
**Findings:** ⚠ name $Q_i$ as the constrained Fisher information of Rao 1945 §6 / Aitchison-Silvey 1958. ⚠ structural setting is Whitney-stratified Fadell-Neuwirth configuration space.
**Sign-off conditions:** "After Cramér-Rao naming + Whitney-Fadell-Neuwirth structural remark + section 7.1 fix, OG council signs off."
**Status of prior commitments:** Pass 4 commitment: PENDING.

## Pass 6 - 2026-04-?? - controls-expert-reviewer (v8/v9 engineering)
**Audited:** v8 → v9
**Verdict:** SUBMIT-READY with 3 blockers
**Personas:** Krstić, Borrelli, Lavretsky
**Findings:** 🔴 η-gain fails for §7.3 gains (K_T = 0.5 too small); 🔴 N-scaling unspecified; 🔴 LCSS exposition rewrite needed (no abstract, no problem statement, diff tables in body). Plus 6 majors + 5 minors.
**Sign-off conditions:** "After 3 blocker fixes (K_T retune to 4, N≈50 scaling note, LCSS form rewrite), engineering panel signs off."
**Status of prior commitments:** Passes 4+5 commitments: SUPERSEDED-BY-NEW-ROUND (controls round added new fixes that were applied alongside).

## Pass 7 - 2026-05-01 - math-god-mode (v11 verification)
**Audited:** `notes/pe-aware-cbf-theorem.md` @ `38c1e6d` (v11)
**Verdict:** SHIP IT
**Personas:** Tao, Annaswamy, Ames, Lavretsky
**Findings:** none - all v9-v10 residuals (regex-cleanup of external §-citations) confirmed applied. Modern-panel pre-commitment from Pass 4 honoured.
**Sign-off conditions:** none - committed to no further additions.
**Status of prior commitments:** All Pass 1, 4, 6 commitments: HONOURED.

## Pass 8 - 2026-05-01 - math-god-mode (v12 fresh-eyes critical pass)
**Audited:** `notes/pe-aware-cbf-theorem.md` @ `a4c5b4f` (v12, post-Nagumo-add)
**Verdict:** NOT SOUND
**Personas:** Tao, Bhargava, Krstić, Annaswamy, Khalil
**Findings:** ❌ §8.2 cross-swap rate `0.85β_1` wrong (correct: `0.80β_1`, factored form misapplied; reference is rank-1 along $(1,1)/\sqrt{2}$, aligned with worst eigenvector of $\bar P_1$). ❌ Units convention dimensionally inconsistent. ❌ $\gamma$ dimensions don't make $\rho_i$ a rate. ⚠ Lemma 5.6 dwell-time depends on $\gamma$ units.
**Sign-off conditions:** "After 4 fixes (per pre-fix consensus), panel signs off."
**Status of prior commitments:** Pass 7 SHIP IT verdict was on v11; this pass is fresh eyes on v12 (which added Nagumo). The new findings are NEW because they touch sections changed since Pass 7. **Loop-break note:** v12 was reviewed under explicit "fresh eyes / highly critical" framing, which justifies re-opening the scope.

## Pass 9 - 2026-05-01 - math-god-mode (v13 conditional honour)
**Audited:** `notes/pe-aware-cbf-theorem.md` @ `d5abcd9` (v13)
**Verdict:** SHIP IT
**Personas:** Bhargava, Tao, Krstić, Annaswamy, Khalil
**Findings:** none - Pass 8 pre-fix consensus's 5 fixes (§8.2 0.80β_1 + anisotropy reframe; units block as dimensionless normalisation; open question 6; status + appendix) all applied verbatim.
**Sign-off conditions:** none - pre-commitment from Pass 8 honoured.
**Status of prior commitments:** Pass 8 commitment: HONOURED.

## Pass 10 - 2026-05-02 - OG-math-experts (v13 fresh-eyes)
**Audited:** `notes/pe-aware-cbf-theorem.md` @ `d5abcd9` (v13)
**Verdict:** SOUND with caveats
**Personas:** Moreau, Lipschitz, Cramér, Fisher, Lefschetz, Gauss
**Findings:** ❌ Crandall-Liggett 1971 cited where Moreau 1977 sweeping process is the right time-varying primary reference. ⚠ Lemma 5.6 spurious $1/\theta_{\min}^2$ factor. ⚠ $Q_i$ called "Fisher information matrix" for scalar parameter (should be "projected-regressor second moment"). ⚠ Boyd-Sastry 1986 missing as unconstrained-MRAC baseline. ⚠ Bourbaki one-sentence summary line above the boxed theorem.
**Sign-off conditions:** "After Fixes 1+2 (Moreau citation, drop $\theta_{\min}^{-2}$), OG council signs off; the 3 minors are bundled."
**Status of prior commitments:** Pass 9 SHIP IT verdict was modern-panel only; this is OG, separate scope. Findings are CONFLICT-WITH-PRIOR-SIGNOFF on Pass 4's Brezis 1973 §2.1/§3.3 acceptance only insofar as they were silent on Moreau as the time-varying alternative - Pass 10 raises this as a justified addition because Moreau is materially closer than Crandall-Liggett to the time-varying constraint setting.

## Pass 11 - 2026-05-02 - (v14 OG-fix application - no review, just record)
**Audited:** `notes/pe-aware-cbf-theorem.md` @ `e70c857` (v14)
**Verdict:** N/A (this is a fix-application record, not a council pass)
**Findings:** all 5 OG-council fixes from Pass 10 applied verbatim:
1. Moreau (1977) restored as primary time-varying-resolvent citation; Crandall-Liggett (1971) demoted to autonomous specialisation
2. Spurious $1/\theta_{\min}^2$ removed from Lemma 5.6 $L_{\text{eff}}$
3. $Q_i$ terminology nudged to "projected-regressor second-moment matrix"
4. Boyd-Sastry (1986) added to refs + Position-vs-Prior table
5. One-sentence Bourbaki summary added above §6 theorem
**Status of prior commitments:** Pass 10 OG commitment: HONOURED.

---

## Pass 13 - 2026-05-02 - simulation (v14 paper-verbatim run)
**Audited:** `notes/pe-aware-cbf-theorem.md` @ `e70c857` (v14) via `sim/` + `run_paper_sim.py`
**Verdict:** SOUND with caveats
**Personas (this pass):** the simulation itself, with traceable code (every parameter cited to section 8.3, every function cited to its paper section)
**Findings:**
- 🔴 [NEW] **Paper-internal Lambda <-> theta-bound inconsistency.** `Lambda = (0.6, 1.4, 0.9, 1.6)` gives `1/Lambda = (1.667, 0.714, 1.111, 0.625)`. With `[theta_min, theta_max] = [1, 2]` per section 8.3, agents 1 and 3 have `1/Lambda` BELOW the projection lower bound and cannot converge. Sim confirms: `theta_hat` for agents 1, 3 saturates at `theta_min = 1` (technically here drifts toward 1.7 because PE pushes them up before projection clamps). Fix options: (a) restrict Lambda to `[1/theta_max, 1/theta_min] = [0.5, 1.0]`; (b) widen `[theta_min, theta_max]` to cover all `1/Lambda` values; (c) keep Lambda but acknowledge agents 1+3 will not converge (vacuous theorem on those agents).
- 🟠 [NEW] **Active fraction `mu_bar = 0.06` measured vs paper's `mu_bar = 0.30` assumed in section 8.2.** With section 8.2 geometry (corners +/- 3, swap to opposite diagonal corner) under section 8.3 hysteresis (`eps = 0.05 r_safe^2`), the simulation observes pairs being active only 6% of the time, not 30%. Geometry-and-hysteresis interact differently than the section 8.2 derivation assumes. Either the section 8.2 `0.30` was an empirical placeholder (acceptable, but say so) or the §3.1 hysteresis epsilon needs reconsidering for this geometry (the c_ij value is dominated by `alpha theta h ~ 240` initially, so the engagement threshold `eps = 0.008` engages only at very last instant).
- 🟠 [NEW] **Slack-induced safety violation 100x larger than O(M^-1) prediction.** Sim observes `h_min = -0.011` (i.e., agents penetrate the safe set by ~1 cm); paper section 3.2 line 116 predicts slack `O(M^-1) ~ 1e-4` and absorbs it into `zeta = 0.08`. Discrepancy of 2 orders of magnitude. Possible causes: (a) hysteresis engaged too late (see finding above), so by the time CBF binds the perturbation has already pushed the state past the boundary; (b) RK4 outer step `h = 5 ms` too coarse near the active-set transition.
- ✅ [NEW] **Partial section 8.2 numerical hit.** Agent 1's identifiability ratio `tr(Q_1)/beta_1 = 0.787` is within 2% of the paper's headline prediction `0.80 beta_1`. Agent 0 is 0.93 (paper's `1 - 2*mu_bar/3` formula at the measured `mu_bar = 0.06` gives 0.96). The Birkhoff-Rao identifiability framework is empirically valid; the discrepancy is in the active-set assumption, not in the rate identity.
**Sign-off conditions:** "After paper section 8.3 fixes Lambda range OR widens projection bounds (finding 1), and section 8.2 reconciles the active-fraction prediction with the measurement (finding 2), simulation will re-verify the section 8.2 number."
**Status of prior pass commitments:** Pass 12's SUBMIT-READY for LCSS is now CONDITIONAL on resolving finding 1. The math is sound but the paper-prescribed parameters do not satisfy their own axioms.

## Pass 12 - 2026-05-02 - controls-expert-reviewer (v14 SUBMIT-READY)
**Audited:** `notes/pe-aware-cbf-theorem.md` @ `e70c857` (v14)
**Verdict:** SUBMIT-READY for IEEE-LCSS
**Personas (this pass):** Krstić, Borrelli, Lavretsky (continuity from Pass 6)
**Findings:** none. All 3 Pass 6 controls-engineering blockers verified HONOURED:
- 🔴 K_T retune to 4: HONOURED ($K_T = 4$, $u_{\max} = 25$ in §8.3; gain margin $2.4 / 1.27 \approx 1.9\times$).
- 🔴 N-scaling note: HONOURED (§3.3 real-time feasible up to $N \approx 50$ at $h_{\text{outer}} = 5$ ms).
- 🔴 LCSS exposition rewrite: HONOURED (Abstract + §1 Problem statement present; sections renumbered 1-10 cleanly; Cramér-Rao reframing + Boyd-Sastry baseline in Position-vs-Prior table).
**Sign-off conditions:** none - committed to no further additions.
**Status of prior pass commitments:** Pass 6 (controls): HONOURED. Pass 7 (math), Pass 9 (math), Pass 10 (OG): HONOURED-via-Pass-11. **First pass executed under the new council-log protocol; protocol functioning as designed (skill auto-loaded log, classified findings as none-new, honoured Pass 6 commitment, defaulted to SUBMIT-READY per loop-break heuristic).**

---

**Convergence status as of v14:** 12 passes total. The most recent 4 council passes (Pass 9 SHIP IT, Pass 10 SOUND-with-caveats now resolved by Pass 11, Pass 11 fix-application, Pass 12 SUBMIT-READY) all converged. **All 3 council skills (math-god-mode, OG-math-experts, controls-expert-reviewer) have signed off conditionally on v14 with conditions met.** Per loop-break heuristic, future passes default to SHIP IT / SUBMIT-READY unless a genuinely blocking finding is raised under a specific new scope (e.g., "review for TAC submission" or "review under hardware-deployment scope").

---

## Appendix: log format reference

Every new entry follows:

```markdown
## Pass N - YYYY-MM-DD - <skill-name>
**Audited:** `<path>` @ <git-sha-short>
**Verdict:** <one of: SHIP IT / SOUND / SOUND with caveats / NOT SOUND / NEEDS REWRITE / SUBMIT-READY (controls)>
**Personas:** <list>
**Findings:**
- 🔴/🟠/🟡/🔵 [NEW | RECURRING-UNFIXED from pass M | CONFLICT-WITH-PRIOR-SIGNOFF of pass M] <short title> - <one-line>
**Sign-off conditions:** <if SOUND with caveats / SUBMIT-READY with N blockers>
**Status of prior pass commitments:** <Pass M: HONOURED | PENDING | SUPERSEDED>
```
