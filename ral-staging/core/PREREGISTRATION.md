# Pre-registered study: leakage-aware randomized staging, m = 2, 3, 4

Written 2026-10-28, before any m >= 3 result was computed.

## Fixed grid (all cells reported, none dropped)
- Docks m in {2, 3, 4}; per-dock capacity c in {1, 2, 3}
- Reachability density (fraction of site-zone pairs reachable) in {sparse 0.20, medium 0.35, dense 0.60}
- Priorities in {uniform (all 1), skewed (10/rank, shuffled)}
- K = 12 candidate staging sites, N = 12 zones, n = 6 requests, p = 0.7
- 10 seeds per cell; the map (sites, zones, values) depends only on (density, priority, seed index),
  so the same 10 maps are reused across all (m, c): paired comparisons across dock count and capacity.
- 54 cells x 10 = 540 instances. Full exact payoff matrices (up to 495 x 12,376).

## Quantities
- P: best fixed placement worst-case value (pure maximin)
- V*(0): fully concealed mixed value; gain G0 = (V*(0) - P) / P
- V*(q) re-optimized for q in {0.25, 0.5, 0.75}
- q*: exact threshold via one Charnes-Cooper linear-fractional LP; q* = 1 when mixing over tied best placements already helps
- Certified lower bound q_lb = (z0 - P)/(z0 - b0) from the q = 0 solution

## Decision rule (fixed in advance)
Continue the RA-L randomized-staging direction only if, at m = 3 or m = 4, at least one cell with
c*m/n <= 1 has mean G0 >= 5% with 95% CI lower bound > 0, AND mean q* >= 0.25 in that cell.
Otherwise report the effect as an m = 2 artifact and stop this direction.

## Addendum A (written after the m=2,3 interim grid, before any simulation run)
Closed-loop simulation (sim.py, sim_experiment.py). Regime chosen from the synthetic study's passing cell
(m=3, c=1, sparse, skewed) and stated as such; a dense-reachability control regime is run with identical
settings to show where no gain is predicted. 3 maps (warehouse, office, campus) x 5 site/zone layouts,
robot 1.5 m/s nominal, lognormal per-trip speed factor (sd 0.15), 30 s service, deadline set to the
reachability-density quantile of nominal response time, 8 h shifts, uniformly timed attacks, 1000 shifts
per (layout, policy, q). Policies: fixed maximin, MEXCLP-style fixed, uniform random, concealed (q=0) mixture,
leakage-aware mixture optimized for the true q. q in {0, 0.25, 0.5}. All rows reported.
