"""
Vectorized (NumPy) version of the pseudo-optimization heuristic.
Evaluates the terminal-stage utility for ALL attacker strategies at once for
each defender placement, keeping only running maximin / column-max so memory
stays O(|S_a|) rather than O(|S_d| x |S_a|). Reproduces the greedy of
general_solver.py. Reaches N = 12..15 that the pure-Python loop cannot.
"""
import numpy as np, itertools, time
from math import comb


def compositions_array(total, parts, dtype=np.int16):
    rows = []
    for c in itertools.combinations(range(total + parts - 1), parts - 1):
        prev = -1; row = []
        for x in c:
            row.append(x - prev - 1); prev = x
        row.append(total + parts - 1 - prev - 1)
        rows.append(row)
    return np.array(rows, dtype=dtype)


def solve_vec(coords=None, v=None, m=2, n=10, c=4, p=0.7, r=12.0, D=None):
    if D is None:
        coords = np.asarray(coords, float); N = len(coords)
        D = np.sqrt(((coords[:, None, :] - coords[None, :, :]) ** 2).sum(-1))
    else:
        D = np.asarray(D, float); N = D.shape[0]
    v = np.asarray(v, float)

    Sa = compositions_array(n, N)                    # (K, N)
    K = len(Sa)
    Sa_f = Sa.astype(np.float32)
    pw = (p ** Sa_f).astype(np.float32)              # p^{w_j}, (K, N)
    wpos = Sa > 0                                    # (K, N)
    base = ((~wpos) * v).sum(1).astype(np.float32)   # not-attacked value per Sa

    order = list(np.argsort(-v, kind='stable'))      # cities, highest value first
    placements = list(itertools.combinations(range(N), m))

    col_max = np.full(K, -np.inf, dtype=np.float32)
    maximin = -np.inf

    for placement in placements:
        cover_order = {}
        for x in range(N):
            covs = [b for b in placement if D[b, x] <= r]
            covs.sort(key=lambda b: (b != x, D[b, x]))   # own battery first, then nearest
            cover_order[x] = covs
        remaining = {b: np.full(K, float(c), dtype=np.float32) for b in placement}
        util = base.copy()
        for x in order:
            need = Sa_f[:, x].copy()
            got = np.zeros(K, dtype=np.float32)
            for b in cover_order[x]:
                give = np.minimum(need - got, remaining[b])
                np.maximum(give, 0, out=give)
                remaining[b] -= give
                got += give
            defended = (Sa[:, x] > 0) & (got >= Sa_f[:, x])
            util += defended * v[x] * pw[:, x]
        rmin = util.min()
        if rmin > maximin:
            maximin = float(rmin)
        np.maximum(col_max, util, out=col_max)

    return dict(N=N, nSd=len(placements), nSa=K, pairs=len(placements) * K,
                defender_maximin=float(maximin), attacker_minimax=float(col_max.min()))


if __name__ == "__main__":
    D6 = [[0, 10, 8, 4, 14, 11], [10, 0, 8, 14, 4, 11], [8, 8, 0, 11, 11, 18],
          [4, 14, 11, 0, 10, 7], [14, 4, 11, 10, 0, 7], [11, 11, 18, 7, 7, 0]]
    t = time.time()
    res = solve_vec(v=[1, 1, 1, 5, 3, 10], m=2, n=10, c=4, p=0.7, r=9, D=D6)
    print("6-city validation:", res, f"({time.time()-t:.2f}s)")
