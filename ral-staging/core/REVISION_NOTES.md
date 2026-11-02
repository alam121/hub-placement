# Response to the pre-submission review (point by point)

**1. Physical staging and leakage not integrated (Major).**
- Remark 1 now states that all optimal policies are optimal for *exogenous* leakage, and gives the end-to-end value with policy-dependent exposure q_eff(x) = q + (1-q) E_x[tau]/H, which is quadratic in x.
- New Sec. VI-E evaluates exposure for H = 8 h, 1 h, 15 min, 5 min and 2 min (`relocation_study.py`, Supp. Table S3):
  - Exposure is 0.1% / 0.9% / 3.7% / 11% / 28%.
  - The gain at q = 0 falls from 11.2% to 6.4% at 2 min.
  - Exposure-aware re-optimization adds at most 1.1 points.
  - The exogenous optimum stays above fixed staging in at least 13 of 15 layouts.
  - The end-to-end threshold moves from 0.83 to 0.79.
- Closed loop at H = 15 min, q = 0.25: +5.6% (exogenous policy) and +5.3% (exposure-aware policy), statistically indistinguishable.
- Conclusion: the exogenous optimum is adequate for shifts of 15 min or longer; minute-scale re-staging needs explicit exposure modelling.

**2. Threshold precision (Major).**
- Prop. 1 now defines q* = 0 when G(0) = 0.
- New Remark 2, "Scope of q*", separates three things: (a) the strict advantage disappearing, (b) optimality of deterministic staging, which need not be unique, and (c) operational desirability, which lies outside the objective.
- It also documents the implementation: the tie test runs first, with tolerances 1e-9 and 1e-7; the Charnes–Cooper LP excludes b(x) = P; the cap lambda <= 1e8 was never active (largest non-tie q* = 0.993).
- Counts: 97 tie cases with q* = 1; 219 zero-gain cases with q* = 0.
- "Worthless" is replaced everywhere by "loses its strict worst-case advantage".

**3. Novelty positioning (Major).**
- New Related Work paragraph, "What is and is not new", lists the established ingredients and the four specific new results.
- The claim about compact formulations is narrowed: Lemma 2 rules out per-site-marginal formulations only, and does not exclude every compact representation.

**4. Lemma 2 assumptions (Moderate).**
- New counterexample with strictly positive priorities (v_A = 10, v_B = 1, p = 0.9).
- Both policies have identical marginals (1/2 at every site), but z(x) = 4.95 and z(x') = 1.0.
- All attack values are listed in the proof and in Supp. S0, and verified with the evaluator (`lemma2_example.py`).

**5. Terminal-model restrictiveness (Major).**
- 240 grid games re-solved under three variants (`terminal_variants.py`, Supp. Table S4):
  - partial credit (exact greedy over a transversal matroid, checked against an LP on 400 cases);
  - all-or-nothing with p = 0.5;
  - all-or-nothing with p = 0.9.
- Favourable-cell G(0): 9.5% (paper's model), 2.8% (p = 0.5), 15.4% (p = 0.9), 2.1% (partial credit).
- Per-instance gains under the two restoration rules correlate at r = 0.48.
- Conclusions are now explicitly restricted to all-or-nothing restoration with reliable robots, in the abstract, introduction and limitations.

**6. Regime selection (Major).**
- New "Role of each study" paragraph: the grid is exploratory with a pre-specified rule; the simulation is confirmatory for the chosen regime; later studies are reported in full.
- New Table II: one-factor-at-a-time sensitivity over alarm budget, deadline/density, priority skew and fleet size (`sensitivity_study.py`).
- In the least favourable levels the gain falls to 3–4% and appears in only 7–11 of 15 layouts.

**7. Gazebo scope (Major).**
- The single-robot results are now labelled as validating travel times and reachability only.
- New near-deadline analysis:
  - 37 legs within 10 s of their deadline, median error 0.9 s;
  - 95th-percentile error 3.8 s;
  - with every deadline tightened by 3.8 s, the gains are still 10.8% / 7.2% / 3.9%.
- New concurrent three-robot Nav2 experiment (`gz/multi`; Supp. S6–S11): 46 shifts, 53 legs, 23 with concurrent motion.
  - Arrivals are 0.95 s later than the model on average, and concurrency caused no failures.
  - Two deterministic model–Nav2 discrepancies erased part or all of the benefit (warehouse +6.5% vs. a model +11.4%; office 0.0% vs. a model +10.3%).
  - Re-planning on Nav2-verified reachability restores it: +3.4% and +15.7%, with every dispatched leg on time and realized value matching the model.
  - The behaviour-tree acknowledgement timeouts with three full stacks on two cores are reported in Supp. S10–S11.
- The abstract and conclusion now state these results and this scope.

**8. Statistics and reproducibility (Major).**
- Found and fixed a seeding bug: the simulator seeded with Python's salted `hash()`. It now uses deterministic CRC32 seeds with common random numbers across policies, so comparisons are paired. All closed-loop numbers were re-run.
- New "Implementation and reporting" paragraph: CPU, library versions, tolerances, seeds, and t-intervals with layouts as the independent units.
- Table I's caption states exactly what the times include.
- Largest-case branch-and-bound statistics are in Supp. Table S2.

**Presentation items.**
- Abstract: "cell means up to 14.9%" (two docks); 12.0% is the three-dock cell.
- Prop. 2: boundary handling stated in Remark 2.
- Full-matrix and matrix-free runtimes are kept separate.
- Table I's timing scope is stated.
- All policies at every q, including the fixed baseline, are in Supp. Table S1.
- Fig. 2's caption explains how the curves are averaged.
- Fig. 5 has the near-deadline analysis.
- "Worthless" is qualified everywhere.
- Space: the simulation table and the model-vs-simulation figure moved to the supplement (Table S1, Fig. S1).

# Response to the second pre-submission review (risk assessment)

**1. Incremental novelty (high risk).**
- New Table I compares the closest prior models (patrolling games, security games, leakage security games, DAD/robust siting, randomized robust optimization) on randomized first stage, partial observation, coupled recourse, marginal sufficiency and an exact threshold.
- The "What is and is not new" paragraph now argues that the combination changes the problem class: leakage security games stay tractable *because* payoffs depend on marginals, and DAD models assume q = 1, exactly where randomization has no strict advantage (Prop. 1).
- New empirical head-to-head with the closest prior method (`marginal_gap.py`, previously unreported): implementing the optimal marginals by comb sampling loses more than 0.1% in 152 of 321 games (up to 14.7%) and is no better than fixed staging in 63.

**2. Gazebo validation dispatched one robot at a time (high risk).** Replaced by a full concurrent study (`gz/multi/setup_exact.py`, `exact_runner.py`, `analyze_exact.py`; Table IV; Supp. Tables S13-S15):
- Every (configuration, attack) pair that the leakage-aware policy (q = 0.25) or the best fixed staging can produce, on all 15 layouts, executed with three Nav2 stacks running throughout (real-time factor 0.5 to fit two cores; all times are simulation times).
- Robots perceive each other (virtual fleet scan from shared poses feeding an obstacle layer in local and global costmaps; startup check that every costmap is subscribed), and converging robots get distinct service points 1.4 m apart.
- Values are exact expectations over the policy, observation event and success draws; with all legs on time they reproduce V_x(q) and P exactly, so there is no sampling noise.
- Round 1 (model reachability): planned 7.5 +- 2.5%, Nav2 3.3 +- 4.9%, gain in 10/15 layouts, one layout -19%. 26 of 29 failed legs were on arcs with < 3.8 s slack.
- Round 2 (slack >= 3.8 s, rule fixed before these runs from the single-robot data): planned 5.3 +- 2.5%, Nav2 5.4 +- 3.9%; 12/15 layouts realize exactly the planned value; medians equal (3.3%). The mean agreement is partly due to one layout where the fixed baseline's arc fails (28%); without it 3.8 +- 1.9% vs 5.4 +- 2.7%. This is stated in the paper.
- Remaining failures (7/87 legs): robots converging on one zone (delays p95 9.6 s in round 1, up to 54 s in round 2; closest approach 0.49 m) and one wall-adjacent office arc that stalls the controller in all 4 uses.
- Round 3 (additional 9.7 s margin for zones with >= 2 robots): fixes most interference failures, but leaves planned 3.3% and realized 2.0%, so the round-2 rule is recommended and converging dispatch is listed as a limitation.
- The earlier 23-shift sampled experiment is kept in Supp. Tables S6-S11, labelled as superseded.

**3. Restrictive model (medium risk).** No change to the model. Partial credit, reliability and fleet-size sensitivity remain reported as negative results, and the scope statement is unchanged.

**4. Synthetic experiments (medium risk).**
- New real floor plan: the Willow Garage office laser map (0.1 m, stage_ros), planned on the map itself with robot-radius inflation (`realmaps/willow_fine.py`, `ral/willow_study.py`; Supp. Table S12).
  - Exact gains 10.7 / 7.0 / 4.2% at q = 0 / 0.25 / 0.5 (synthetic 11.2 / 7.5 / 4.2), mean q* 0.82.
  - Closed loop: +7.3 / 6.6 / 5.5% (4/5 layouts each). The 95% intervals include zero with five layouts, and the paper says so. Uniform randomization loses 14-20% in every layout.
- Nav2 on this laser map could not reliably pass its cluttered doorways (pilot dispatch aborted or took 3x the model time), even with the true rectangular footprint and 0.1 m costmaps. The paper reports it as simulation-only and says why.
- No hardware or real alarm data: still a limitation.

**Housekeeping.** The Gazebo single-robot figure moved to Supp. Fig. S2 to keep 8 pages. The abstract is 249 words. Tables renumbered: I prior work, II scaling, III sensitivity, IV concurrent Nav2.

# Third pass (remaining weaknesses)

- **Remark 2 correction.** The end-to-end objective z(x) - q_eff(x)(z(x) - b(x)) multiplies a quadratic q_eff(x) by the piecewise-linear z(x) - b(x). It is piecewise cubic and in general not concave, not quadratic as previously stated. The exposure study already used the best of the exogenous optima rather than a claimed global optimum, so no result changes.
- **Novelty.** Sec. V now explains why separation is the hard step: marginal-coverage best responses decompose across targets, while here the recourse couples zones through shared docks. The joint-recourse bound is admissible for all configurations at once because it relies only on monotonicity of feasibility under extra load. The exact q* replaces bisection (an interval, one full constraint-generation solve per step) with one linear-fractional program that returns the exact breakpoint.
- **Outlier-adjusted Nav2 result leads.** The text and Table IV now lead with the 14-layout figure (Nav2 4.1 +- 2.1% vs planned 5.4 +- 2.7%, bold in the table). The 15-layout mean (5.7 +- 3.9%) is reported with the explicit note that we do not rely on it.
- **Repeated trials.** The slack-verified round was executed three times (156 dispatches, 261 legs, 245 on time):
  - Median per-leg arrival spread across repetitions: 0.09 s.
  - 3 of 87 legs changed on-time status, and only one layout's gain changed (campus1: 7.0 / 16.1 / 9.3%).
  - All 16 failures and every spread above 3.1 s come from converging robots (10) or the office wall stall (6; that arc failed in all 8 uses across rounds). The maximum converging-robot delay was 65 s.
  - Data: `gz/multi/exact/verified_all`, `merge_reps.py`, `variability.json`.
- **Real-map wording.** The Willow study is described as a simulation on the map of a real building, with no physical robots (abstract and Sec. VI).
- **Assumptions justified.** Sec. III now motivates all-or-nothing restoration (joint containment or inspection) and independent success (individual navigation and manipulation errors), and points to common-cause failures as out of scope and to the partial-credit analysis.
- **Space.** The validation, Gazebo setup, relocation and closed-loop setup paragraphs were condensed. The paper is 8 pages; the abstract is 249 words.

# Fourth pass (presentation and methodological evidence)

1. **New Fig. 1 (page 2): same marginals, different worst case.** A schematic of Lemma 2: under both policies every dock is open with probability 1/2, yet the worst cases are 4.95 and 1.00. Referenced from the contributions list. `figures_rev3.py`.
2. **Solver ablation (new Table II, Sec. V; `ablation.py`, `ablation.json`).** Identical instances (K=12, m=3, n=6, c=1; three maps; N = 12-50), computing P and V*(0) by:
   - full matrix: out of memory beyond 25 zones;
   - enumerated-separation CG: 0.38 s at 12 zones, 297 s at 40, over 600 s at 50;
   - our branch-and-bound CG: 0.08-0.15 s throughout, about ten best-response calls; about 2700x faster than enumerated CG at 40 zones.
   - All methods agree to 4e-15 wherever more than one finished.
   - Threshold: one linear-fractional LP takes 8-56 ms, against 0.27-0.40 s for 10-step bisection. Bisection only brackets q* to 1e-3 and cannot certify the q* = 1 tie case.
   - Sec. V also explains why separation is hard here (no per-target decomposition) and why the bound is admissible.
3. **Per-layout Nav2 figure (new Fig. 2; planned vs realized, model vs slack-verified, rings for converging robots).** The engineering lesson is stated: optimizing on an inaccurate reachability graph can erase the benefit, and correcting the graph recovers most of it.
4. **Deployment procedure and uncertain leakage (Discussion; `interval_q.py`, `interval_q.json`).**
   - The procedure: verified reachability, compute P, the mixture and q*, then compare with a conservative estimate of q.
   - For q in an interval, V_x(q) is linear and non-increasing, so the max-min policy is x*(q_hi). Regret is convex, so the minimax-regret policy is one LP with two endpoint constraints.
   - On 15 layouts with q in [0.2, 0.5], planning for q_hi guarantees 4.2 +- 1.8% over fixed staging across the whole interval with at most 0.8% regret (minimax regret 0.5%). Planning for q = 0 guarantees only 2.8% and falls below fixed staging in 5 layouts.
5. **Conclusion rewritten** around the general finding that randomization's value depends jointly on configurations, observability and physical reachability.
6. **Space.** The q-curve and map figures moved to Supp. Figs. S3-S4, and the duplicated sensitivity table to Supp. Table S5. The implementation details moved to Supp. S0. The paper is 8 pages; the abstract is 249 words.
