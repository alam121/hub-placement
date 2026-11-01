# Leakage-aware randomized staging for capacity-constrained multi-robot response

Code, data, Gazebo/Nav2 setup, manuscript source and supplementary video for
*"When Should Robots Hide Where They Wait? Leakage-Aware Randomized Staging for
Capacity-Constrained Multi-Robot Response"* (S. M. Alam, H. Rafique), submitted to IEEE RA-L.

The base place–attack–assign game and the max-flow terminal evaluator come from the
earlier work in the repository root; this folder adds the leakage-aware staging model and everything in the RA-L paper.

## Setup
```
pip install -r requirements.txt
python3 localize.py          # rewrites development paths to this checkout (run once)
```

## Layout
| Path | Contents |
|------|----------|
| `core/evaluator.py` | exact terminal evaluator (Gale condition, Lemma 1), any number of docks |
| `core/leakage.py` | V*(q) LP by constraint generation, exact q* (Charnes–Cooper LP), tie test |
| `core/scale_solver.py` | matrix-free exact solver: numba branch-and-bound attacker best response with the joint-recourse bound, lazy mu_d |
| `core/PREREGISTRATION.md` | pre-specified grid, metrics and decision rule (dated file, not an external registry) |
| `core/run_grid.py`, `analyze.py`, `results.jsonl`, `summary.json` | 540-game synthetic study (Sec. VI-A) |
| `core/validate.py`, `validate_scale.py`, `validate_br.py`, `verify_qstar.py` | independent checks (MILP, max-flow, brute force, LP bracketing) |
| `core/marginal_gap.py`, `marginal_gap.json` | same-marginal value spread and comb-sampling loss (Sec. IV) |
| `core/run_scale.py`, `stress_scale.py`, `scale_results.jsonl`, `stress.jsonl` | 30–100-zone scaling study (Sec. VI-B) |
| `core/sim.py`, `sim_experiment.py`, `sim_results.json` | closed-loop shift simulator, 450 runs (Sec. VI-C) |
| `core/relocation_study.py`, `relocation_study.json` | policy-dependent relocation exposure, shift-length sensitivity (Sec. VI-E, Supp. S3) |
| `core/terminal_variants.py`, `terminal_variants.json` | response-model sensitivity: partial credit, p = 0.5 / 0.9 (Supp. S4) |
| `core/sensitivity_study.py`, `sensitivity_study.json` | one-factor-at-a-time scenario sensitivity (Table II, Supp. S5) |
| `core/lemma2_example.py` | exact check of the positive-priority Lemma 2 counterexample |
| `core/REVISION_NOTES.md` | point-by-point response to the pre-submission review |
| `core/paper/supplement.tex`, `gen_supplement.py` | supplementary material (tables generated from the raw results) |
| `gazebo/near_deadline.py` | navigation-model discrepancy near deadlines + tightened-deadline check |
| `gazebo/multi/` | concurrent three-robot Nav2 experiment (setup, runner, per-shift results, verified-reachability runs) |
| `core/figures.py` | paper figures |
| `core/paper/` | LaTeX source (IEEEtran), figure PDFs, compiled PDF |
| `gazebo/` | Gazebo Harmonic worlds, robot model, Nav2 params, mission runner, results (Sec. VI-D); see `gazebo/README.md` |
| `gazebo/video/` | headless-rendered video pipeline |
| `video/RAL_video_leakage_aware_staging.mp4` | supplementary video |

## Reproduce
```
cd core
python3 validate.py ../..        # evaluator vs the root exact_solver.py (max-flow) and an independent MILP
python3 run_grid.py 2 && python3 analyze.py && python3 verify_qstar.py
python3 marginal_gap.py
python3 validate_scale.py && python3 validate_br.py && python3 run_scale.py 2
python3 sim_experiment.py 2 && python3 sim_summary.py
python3 figures.py grid_figs map_fig sim_figs
cd paper && latexmk -pdf main.tex
```
Gazebo/Nav2 (ROS 2 Jazzy, Gazebo Harmonic): see `gazebo/README.md`.
Single-threaded NumPy/SciPy (HiGHS); all seeds are fixed in the scripts.

## Concurrent multi-robot Nav2 study (Table IV; Supp. Tables S13-S15)

`gazebo/multi/` runs every (configuration, attack) pair that the leakage-aware policy (q = 0.25) or the best fixed staging can produce,
with three namespaced Nav2 stacks running throughout and robots perceiving each other through shared poses (`fleet_scan.py`).

```bash
python3 gazebo/multi/setup_exact.py <warehouse|office|campus> <layout> <model|verified|verified2> 0.5
gazebo/multi/run_batch.sh <model|verified|verified2> warehouse0 office1 ...
python3 gazebo/multi/analyze_exact.py <model|verified|verified2>
```

- `model`: the paper's grid reachability.
- `verified`: drops arcs with slack below 3.8 s (95th-percentile single-robot error, fixed in advance).
- `verified2`: additionally requires 9.66 s slack for zones served by two or more robots (`exact/shared_margin.json`).
- `gazebo/cleanup.sh` stops all simulator and ROS processes. Its patterns are anchored to full executable paths, so it never matches the calling shell.
- Raw per-dispatch results are `exact/<round>/<layout>/gazebo_results.json`; per-round summaries are `exact/<round>/summary.json`.

## Real floor plan (Supp. Table S12)

`realmaps/willow-full.pgm` is the Willow Garage office map distributed with `stage_ros` (BSD licence; https://github.com/ros-simulation/stage_ros).
`realmaps/willow_fine.py` builds the 0.1 m geometry and the robot-radius-inflated planning grid. `core/willow_study.py` runs the exact model and the closed-loop simulation.
`gazebo/multi/exact/willow_pilot_dispatch.json` is the Nav2 pilot dispatch on this map that aborted or ran 3x slower than the model, which is why the map is evaluated in simulation only.
