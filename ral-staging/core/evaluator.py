"""
Exact terminal evaluator for the robot-staging game, any number of docks m.

Instance: K candidate staging sites, N zones, coverage A[i,j] in {0,1},
zone values v_j, per-dock capacity c, success prob p, request budget n.
Placement d: m-subset of sites (bitmask). Attack w: composition of n over N zones.

U(d,w) = sum_{j: w_j=0} v_j + max_{S subset of loaded zones, S feasible} sum_{j in S} v_j p^{w_j}

Feasibility of S (transportation with uncapacitated arcs; Gale/Hall condition):
  S feasible  <=>  for every T subset of S:  sum_{j in T} w_j <= c * |open docks covering some j in T|
(max-flow/min-cut: with infinite hub->zone arcs every finite cut is indexed by a sink subset T.)
This is an exact replacement for the per-subset max-flow test; it is validated against both the
original max-flow code and an independent MILP in validate.py.
"""
import itertools
import numpy as np
from numba import njit


def compositions(n, N):
    out = []
    for bars in itertools.combinations(range(n + N - 1), N - 1):
        prev = -1
        w = []
        for b in bars:
            w.append(b - prev - 1)
            prev = b
        w.append(n + N - 1 - prev - 1)
        out.append(w)
    return np.array(out, dtype=np.int64)


def placements(K, m):
    return np.array(list(itertools.combinations(range(K), m)), dtype=np.int64)


@njit(cache=True)
def _popcount(x):
    c = 0
    while x:
        x &= x - 1
        c += 1
    return c


@njit(cache=True)
def terminal(dmask, w, covmask, v, c, p):
    """covmask[j] = bitmask of sites covering zone j. dmask = bitmask of open docks."""
    N = w.shape[0]
    loaded = np.empty(N, np.int64)
    L = 0
    base = 0.0
    for j in range(N):
        if w[j] == 0:
            base += v[j]
        else:
            loaded[L] = j
            L += 1
    if L == 0:
        return base
    nsub = 1 << L
    ok = np.ones(nsub, np.bool_)
    val = np.zeros(nsub)
    for T in range(1, nsub):
        need = 0
        nb = 0
        vv = 0.0
        for t in range(L):
            if (T >> t) & 1:
                j = loaded[t]
                need += w[j]
                nb |= covmask[j] & dmask
                vv += v[j] * p ** w[j]
        val[T] = vv
        ok[T] = need <= c * _popcount(nb)
    # feasible[S] = AND of ok[T] over all T subset of S  (subset-AND zeta transform)
    for t in range(L):
        bit = 1 << t
        for S in range(nsub):
            if S & bit:
                if not ok[S ^ bit]:
                    ok[S] = False
    best = 0.0
    for S in range(nsub):
        if ok[S] and val[S] > best:
            best = val[S]
    return base + best


@njit(cache=True)
def full_matrix(dmasks, W, covmask, v, c, p):
    D = dmasks.shape[0]
    A = W.shape[0]
    U = np.empty((D, A))
    for i in range(D):
        for k in range(A):
            U[i, k] = terminal(dmasks[i], W[k], covmask, v, c, p)
    return U


def build(inst, m, n):
    K, N = inst["A"].shape
    P = placements(K, m)
    dmasks = np.array([sum(1 << int(i) for i in pl) for pl in P], dtype=np.int64)
    covmask = np.array([sum(1 << i for i in range(K) if inst["A"][i, j]) for j in range(N)], dtype=np.int64)
    W = compositions(n, N)
    U = full_matrix(dmasks, W, covmask, inst["v"].astype(float), int(inst["c"]), float(inst["p"]))
    return P, W, U
