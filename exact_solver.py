"""
EXACT terminal-stage solver for the IADS game, with no external MILP solver.

For a fixed defender placement and attacker allocation w, the terminal stage is:
    maximize  sum_j v_j * y_j * p^{w_j}
    s.t. each defended city j (y_j=1, w_j>0) receives w_j interceptors routed from
         covering batteries, each battery delivering at most c in total.

Because a city contributes v_j*p^{w_j} only if it is FULLY intercepted, the optimum
is: choose the subset S of attacked cities to fully defend that maximizes total value,
subject to a feasible interceptor routing. Feasibility of defending a subset S is a
transportation/max-flow check (batteries = supply c, cities = demand w_j, edges where
a battery covers a city). We enumerate subsets of attacked cities and take the best
feasible one. This yields the provably optimal terminal utility, giving a ground-truth
against which the greedy heuristic's optimality gap is measured.
"""
import numpy as np, itertools, time
from vectorized_solver import compositions_array


# ---- tiny max-flow (BFS / Edmonds-Karp) ----
def max_flow(cap, s, t):
    n = len(cap)
    flow = 0
    while True:
        parent = [-1] * n
        parent[s] = s
        q = [s]
        while q and parent[t] == -1:
            u = q.pop(0)
            for w in range(n):
                if parent[w] == -1 and cap[u][w] > 0:
                    parent[w] = u
                    q.append(w)
        if parent[t] == -1:
            break
        # bottleneck along augmenting path
        b = float('inf'); v = t
        while v != s:
            b = min(b, cap[parent[v]][v]); v = parent[v]
        v = t
        while v != s:
            u = parent[v]
            cap[u][v] -= b
            cap[v][u] += b
            v = u
        flow += b
    return flow


def feasible(subset, w, batteries, covers_city, c):
    """Can we fully intercept every city in `subset`? Max-flow feasibility."""
    demand = sum(w[j] for j in subset)
    if demand == 0:
        return True
    # nodes: 0=source, 1..B=batteries, B+1..B+K=cities, last=sink
    B = len(batteries); cities = list(subset); K = len(cities)
    S = 0; T = 1 + B + K
    n = T + 1
    cap = [[0] * n for _ in range(n)]
    bidx = {b: 1 + i for i, b in enumerate(batteries)}
    cidx = {j: 1 + B + i for i, j in enumerate(cities)}
    for b in batteries:
        cap[S][bidx[b]] = c
    for j in cities:
        cap[cidx[j]][T] = w[j]
        for b in covers_city[j]:
            cap[bidx[b]][cidx[j]] = 10**9
    return max_flow(cap, S, T) == demand


def exact_terminal(w, placement, D, v, c, p, r, N):
    w = [int(x) for x in w]
    c = int(c)
    batteries = list(placement)
    covers_city = {j: [b for b in batteries if D[b, j] <= r] for j in range(N)}
    attacked = [j for j in range(N) if w[j] > 0]
    base = sum(v[j] for j in range(N) if w[j] == 0)
    # value of defending a city (only meaningful for attacked ones)
    best = 0.0
    # prune: a city is defendable at all only if its covering capacity >= w_j
    defendable = [j for j in attacked if len(covers_city[j]) * c >= w[j]]
    for k in range(len(defendable) + 1):
        for S in itertools.combinations(defendable, k):
            val = sum(v[j] * (p ** w[j]) for j in S)
            if val <= best:
                continue
            if feasible(set(S), w, batteries, covers_city, c):
                best = max(best, val)
    return base + best


def solve_exact(coords=None, v=None, m=2, n=10, c=4, p=0.7, r=12.0, D=None):
    if D is None:
        coords = np.asarray(coords, float); N = len(coords)
        D = np.sqrt(((coords[:, None, :] - coords[None, :, :]) ** 2).sum(-1))
    else:
        D = np.asarray(D, float); N = D.shape[0]
    v = np.asarray(v, float)
    Sd = list(itertools.combinations(range(N), m))
    Sa = compositions_array(n, N)
    U = np.empty((len(Sd), len(Sa)))
    for i, pl in enumerate(Sd):
        for k in range(len(Sa)):
            U[i, k] = exact_terminal(Sa[k], pl, D, v, c, p, r, N)
    return dict(N=N, U=U,
                defender_maximin=float(U.min(1).max()),
                attacker_minimax=float(U.max(0).min()))
