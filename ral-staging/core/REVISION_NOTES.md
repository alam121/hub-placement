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
  - Re-planning on Nav2-verified reachability restores it: +3.4% and +15.8%, with every dispatched leg on time and realized value matching the model.
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
