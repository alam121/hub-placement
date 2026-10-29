# Leakage-aware randomized robot staging: RA-L package

paper/main.tex        manuscript (article-class shim; swap first lines for IEEEtran, see comment at top)
PREREGISTRATION.md    grid, metrics and decision rule fixed before the m>=3 runs (+ simulation addendum)
evaluator.py          exact terminal evaluator (Gale condition), any number of docks
validate.py           810-case check vs original max-flow code and independent MILP -> validation.json
instances.py          pre-registered instance generator
leakage.py            V*(q) LP (constraint generation), exact q* (Charnes-Cooper), tie test
run_grid.py           540-instance study -> results.jsonl ; analyze.py -> summary.json + decision rule
verify_qstar.py       independent bracketing check of q* -> verify_qstar.json
sim.py, sim_experiment.py   closed-loop grid-map simulator, 450 runs -> sim_results.json
figures.py            all figures

Reproduce: python3 validate.py <folder with original exact_solver.py>; python3 run_grid.py 2;
python3 analyze.py; python3 verify_qstar.py; python3 sim_experiment.py 2;
python3 figures.py grid_figs map_fig sim_figs. Requires numpy, scipy, numba, networkx, matplotlib.

## Added: marginal gap and scaling
marginal_gap.py       same-marginal value spread + comb-sampling loss on the 321 grid games with a gain -> marginal_gap.json
scale_solver.py       matrix-free exact solver: numba B&B attacker best response (joint-recourse bound), lazy mu_d
validate_scale.py     24 grid instances vs full-matrix results -> validate_scale.json (max diff 3.6e-15)
validate_br.py        36 B&B best responses vs brute force on 20-zone maps -> validate_br.json (max diff 7.1e-15)
run_scale.py          54 instances, N = 30/40/50 zones, K = 20 sites, m = 3 -> scale_results.jsonl
stress_scale.py       uniform priorities and N = 100 stress tests -> stress.jsonl
