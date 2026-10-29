# Robust Multi-Robot Hub Placement and Task Allocation Under Worst-Case Spatial Demand

Reproducibility code for the paper *"Robust Multi-Robot Hub Placement and Task
Allocation Under Worst-Case Spatial Demand"* (Syed Muhammad Alam, Hamza Rafique).

The code solves a three-stage planner–adversary–planner zero-sum game coupling
pre-deployment hub placement with post-demand robot–task allocation, using an
exact max-flow terminal evaluator, a certified greedy lower bound, an LP matrix-
game solver, and a combinatorial best-response (branch-and-bound) double oracle.
No commercial optimizer is required.

## RA-L follow-up: leakage-aware randomized staging
The folder [`ral-staging/`](ral-staging/) contains the code, data, Gazebo/Nav2 setup, manuscript
source and supplementary video for *"When Should Robots Hide Where They Wait? Leakage-Aware Randomized
Staging for Capacity-Constrained Multi-Robot Response"* (IEEE RA-L submission). See its README.

## Requirements
Python 3.10+, and:
```
pip install -r requirements.txt   # numpy, scipy, matplotlib
```
All results in the paper were produced single-threaded with NumPy and SciPy
(HiGHS via `scipy.optimize.linprog`); random instances use NumPy's PCG64 with
fixed, per-instance seeds recorded in the scripts.

## Core modules
| File | Role |
|------|------|
| `exact_solver.py` | Exact terminal evaluator (Proposition 1): subset selection + max-flow feasibility |
| `general_solver.py` | Greedy terminal evaluator (certified lower bound, Proposition 2) |
| `vectorized_solver.py` | Vectorized greedy evaluator for larger networks |
| `game_lp.py` | Zero-sum matrix game solved by LP (HiGHS) |
| `double_oracle.py` | Double oracle over a pre-built utility matrix |
| `br_oracle2.py` | **Matrix-free** double oracle with the combinatorial best-response oracle (Section 5.6) |

## Reproducing the results
| Paper artifact | Script |
|----------------|--------|
| Benchmark two-model values (Vseq, Vsim) | `game_lp.py`, `exact_solver.py` |
| Empirical scalability (Table 3, Fig. 2) | `scalability.py`, `vec_bench.py`, `vec_run.py` |
| Optimality-gap study (Table 4, Fig. 3) | `compare_gap.py`, `gap_raw.py` |
| Double-oracle (Table 5) | `double_oracle.py` |
| **Best-response oracle scaling (Table 6, Fig. of Sec. 5.6)** | `br_oracle2.py`, `study.py` |
| Robustness across random networks (Table 6/multi) | `multi_instance.py` |
| Exact parameter studies (Figs. 4–6) | `exact_studies.py` |
| Case study (Sec. 7, Table 7–9, Figs. 8–9) | `case_study.py`, `case_sensitivity.py`, `make_case_map.py` |
| Greedy-feasibility verification | `verify_greedy_feasible.py` |

Quick check (benchmark, exact matrix-free equilibrium):
```
python3 br_oracle2.py     # -> V_sim = 6.2613, support 4x2
python3 study.py          # -> multi-instance scaling study (writes study_results.json)
```
The `*.json` files are the recorded outputs used to build the paper's tables.

## License
MIT (see `LICENSE`). If you prefer a different license for the reproducibility
archive, replace `LICENSE` before publishing.

## Citation
If you use this code, please cite the paper. A `CITATION.cff` / BibTeX entry will
be added on acceptance.
