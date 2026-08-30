# Combinatorial best-response oracle — study results

## Method
`br_oracle2.py`: matrix-free double oracle. Attacker best response = exact
branch-and-bound over demand allocations, evaluating J(d,w) with the existing
max-flow terminal solver and pruning with a valid lower bound; defender best
response enumerates placements. Speedups: global memoization of J across
iterations, warm-started incumbent, value-descending branch order, and a greedy
attacker descent to seed a tight incumbent. The full utility matrix is never built.

## Verification (exactness)
- Attacker best response matches brute force over the whole composition space on
  every random mixture tested.
- Benchmark: recovers V_sim = 6.2613 with the correct 4x2 support.
- Random networks N=6 (10 instances) and N=8 (8 instances): the recovered game
  value equals the full-enumeration LP value on ALL 18 instances (|diff| < 1e-4).

## Computational study (random planar networks, m=2, n=10, c=4, p=0.7, r=12)
| N  | instances | matrix pairs | oracle time (mean±sd) | iters | support (def×att) | % of matrix | exactness |
|----|-----------|-------------:|----------------------:|------:|-------------------|------------:|-----------|
| 6  | 10        | 45,045       | 0.5 ± 0.2 s           | 5.9   | 2.0 × 2.0         | 17.7%       | verified vs full-enum |
| 8  | 8         | 544,544      | 3.4 ± 1.8 s           | 6.8   | 2.0 × 2.0         | 9.6%        | verified vs full-enum |
| 10 | 8         | 4,157,010    | 31.8 ± 19.9 s         | 8.8   | 2.9 × 2.1         | 8.7%        | value exact; matrix infeasible to build |
| 12 | 3         | 23,279,256   | 165.5 ± 42.3 s        | 8.7   | 3.3 × 1.7         | 7.0%        | value exact; matrix infeasible to build |

Single-machine full-enumeration + LP reference times (one instance):
N=6 2.2 s, N=8 33.7 s, N=10 303.5 s, N=12 infeasible.

## Headline for the paper
- Exact equilibrium at N=12 (a 23.3M-pair game) in <3 min, where the manuscript
  currently solves EXACTLY only at N=6 (N=7..15 are the greedy APPROXIMATION).
- Fraction of the notional matrix evaluated falls with N (18% → 7%); support stays
  small on every instance; wall-clock advantage over full enumeration widens with N
  (~9x at N=10, unbounded at N=12).

## Honest limitation / next improvement
- Absolute runtime still grows: the pruning bound treats defender-recovered value
  optimistically as 0, so it loosens as N grows. A per-placement max-flow capacity
  bound on defendable value would tighten it.

## Files
- br_oracle2.py            — the oracle + matrix-free double oracle
- study.py                 — the multi-instance study driver
- study_results.json       — per-instance raw results
- fig_oracle_scaling.pdf/png — scaling figure (time vs N; % matrix vs N)
- oracle_subsection_draft.tex — drop-in draft to replace/extend Section 5.5
