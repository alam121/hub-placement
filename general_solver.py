"""
General, parameterized re-implementation of the pseudo-optimization heuristic
from Multi_Agent_phase1.ipynb, for arbitrary networks. Validated to reproduce
the 6-city equilibrium utility f(u*) = 6.185.
"""
import numpy as np
import itertools, time
from math import comb


def coverage_matrix(D, sites, r):
    """For a given placement (tuple of site indices), which cities each site covers."""
    return {s: [j for j in range(D.shape[0]) if D[s, j] <= r] for s in sites}


def compositions(total, parts):
    """All ways to distribute `total` identical AMs over `parts` cities (stars & bars)."""
    for c in itertools.combinations(range(total + parts - 1), parts - 1):
        prev = -1
        row = []
        for x in c:
            row.append(x - prev - 1)
            prev = x
        row.append(total + parts - 1 - prev - 1)
        yield row


def eval_pair(w, placement, D, v, c, p, r, N, has_sam=None, covers=None, order=None):
    """Terminal-stage greedy interception for one (defender placement, attacker w).
    Returns defender utility. Mirrors the notebook's greedy logic.
    has_sam/covers/order may be precomputed per placement for speed."""
    if has_sam is None:
        has_sam = set(placement)
    if covers is None:
        covers = {x: sorted([s for s in placement if D[s, x] <= r], key=lambda s: D[s, x])
                  for x in range(N)}
    # cities under attack, highest-value first (defend most valuable first)
    attacked = [j for j in (order if order is not None else range(N)) if w[j] > 0]

    fired_from = {s: 0 for s in placement}
    delivered = np.zeros(N)

    for x in attacked:
        need = w[x]
        # dispatch from covering hubs (a_{sx}=1), nearest first (covers[x] pre-sorted).
        # No hub=zone co-location shortcut: works whether or not hub sites coincide with
        # zones (general reachability matrix). Equivalent to the old co-location rule when
        # a hub sits at the zone, since that hub is then covers[x][0] at zero travel cost.
        for s in covers[x]:
            while delivered[x] < need and fired_from[s] < c:
                fired_from[s] += 1
                delivered[x] += 1
            if delivered[x] >= need:
                break

    # utility: not-attacked -> full value; fully intercepted -> v*p^w; else 0
    u = 0.0
    for j in range(N):
        if w[j] == 0:
            u += v[j]
        elif delivered[j] >= w[j]:
            u += v[j] * (p ** w[j])
    return u


def solve(coords, v, m, n, c, p, r, verbose=False, D=None):
    if D is None:
        coords = np.array(coords, float)
        N = len(coords)
        D = np.sqrt(((coords[:, None, :] - coords[None, :, :]) ** 2).sum(-1))
    else:
        D = np.array(D, float)
        N = D.shape[0]
    Sd = list(itertools.combinations(range(N), m))
    Sa = list(compositions(n, N))
    t0 = time.time()
    U = np.empty((len(Sd), len(Sa)))
    order = sorted(range(N), key=lambda j: -v[j])  # highest value first
    for i, placement in enumerate(Sd):
        has_sam = set(placement)
        covers = {x: sorted([s for s in placement if D[s, x] <= r], key=lambda s: D[s, x])
                  for x in range(N)}
        for k, w in enumerate(Sa):
            U[i, k] = eval_pair(w, placement, D, v, c, p, r, N, has_sam, covers, order)
    build_t = time.time() - t0
    # security strategies
    defender_maximin = U.min(axis=1).max()
    attacker_minimax = U.max(axis=0).min()
    return dict(N=N, nSd=len(Sd), nSa=len(Sa), pairs=len(Sd) * len(Sa),
                defender_maximin=defender_maximin, attacker_minimax=attacker_minimax,
                build_seconds=build_t)


if __name__ == "__main__":
    # ---- Validation: the exact 6-city network from the report ----
    # coordinates chosen to reproduce the report's inter-city distances closely
    # (report uses an explicit distance matrix; we instead validate the utility value)
    D6 = [[0, 10, 8, 4, 14, 11],
          [10, 0, 8, 14, 4, 11],
          [8, 8, 0, 11, 11, 18],
          [4, 14, 11, 0, 10, 7],
          [14, 4, 11, 10, 0, 7],
          [11, 11, 18, 7, 7, 0]]
    v6 = [1, 1, 1, 5, 3, 10]
    res = solve(None, v6, m=2, n=10, c=4, p=0.7, r=9, D=D6)
    print("== 6-city validation ==")
    for k, val in res.items():
        print(f"  {k}: {val}")
