"""
Combinatorial best-response oracle (v2) with three speedups over br_oracle.py:
  1. Global memoization of the exact terminal value J(placement, w) across the
     whole double-oracle run (placements recur every iteration).
  2. Warm-started incumbent: the attacker branch-and-bound starts from the best
     of the current demand columns plus concentration guesses, so the valid
     lower bound prunes from the first node.
  3. Value-descending zone order in the branch-and-bound, so a strong incumbent
     is found early.

Exactness is unchanged: the lower bound is a valid underestimate of J(d,w) for
every completion of a partial allocation, so the attacker best response is exact
and the matrix-free double-oracle returns the full-game Nash value to LP tolerance.
"""
import numpy as np, itertools
from math import comb
from exact_solver import exact_terminal
from game_lp import solve_matrix_game

_MEMO = {}
def _J(w, placement, D, v, c, p, r, N):
    key = (placement, tuple(int(x) for x in w))
    val = _MEMO.get(key)
    if val is None:
        val = exact_terminal(list(key[1]), placement, D, v, c, p, r, N)
        _MEMO[key] = val
    return val


def attacker_best_response(weights, placements, v, D, c, p, r, N, n, warm=None):
    v = np.asarray(v, float)
    supp = [(float(wi), tuple(pl)) for wi, pl in zip(weights, placements) if wi > 1e-12]
    stats = {"evals": 0}

    def g(w):
        stats["evals"] += 1
        return sum(wi * _J(w, pl, D, v, c, p, r, N) for wi, pl in supp)

    # branch in value-descending zone order; `pos` maps branch depth -> zone id
    pos = list(np.argsort(-v))
    vsorted = [v[j] for j in pos]                 # descending zone values along branch
    suffix = [0.0] * (N + 1)                       # suffix[t] = sum of values of zones at depth >= t
    for t in range(N - 1, -1, -1):
        suffix[t] = suffix[t + 1] + vsorted[t]

    w = [0] * N
    best = {"val": np.inf, "w": None}

    # valid lower bound on g over completions: zones at depth < t fixed in w,
    # `remaining` units to spread over zones at depth >= t. Defended value >= 0,
    # so J >= (base from fixed zeros) + (min base achievable on the tail).
    def lb(t, remaining):
        fixed_base = 0.0
        for d in range(t):
            if w[pos[d]] == 0:
                fixed_base += vsorted[d]
        tail_len = N - t
        k = remaining if remaining < tail_len else tail_len
        # zones are value-descending, so the top-k tail values are the first k
        removed = 0.0
        for d in range(t, t + k):
            removed += vsorted[d]
        return fixed_base + (suffix[t] - removed)

    def rec(t, remaining):
        if t == N - 1:
            w[pos[t]] = remaining
            val = g(w)
            if val < best["val"]:
                best["val"] = val; best["w"] = w.copy()
            w[pos[t]] = 0
            return
        for a in range(remaining + 1):
            w[pos[t]] = a
            if lb(t + 1, remaining - a) < best["val"] - 1e-12:
                rec(t + 1, remaining - a)
        w[pos[t]] = 0

    # warm-start incumbent from provided candidates + concentration guesses
    cands = list(warm or [])
    top = int(pos[0])
    conc = [0] * N; conc[top] = n; cands.append(conc)
    if N >= 2:
        s2 = [0] * N; s2[int(pos[0])] = n - n // 2; s2[int(pos[1])] = n // 2; cands.append(s2)
    for cnd in cands:
        if sum(cnd) == n and len(cnd) == N:
            val = g(cnd)
            if val < best["val"]:
                best["val"] = val; best["w"] = list(cnd)

    # greedy attacker descent: place units one at a time into the zone that most
    # reduces g. Cheap (~n*N evals) and usually near-optimal, so the incumbent is
    # tight before branch-and-bound starts. Does not affect exactness.
    gw = [0] * N
    for _ in range(n):
        bestj = None; bestval = np.inf
        for j in range(N):
            gw[j] += 1
            val = g(gw)
            if val < bestval:
                bestval = val; bestj = j
            gw[j] -= 1
        gw[bestj] += 1
    val = g(gw)
    if val < best["val"]:
        best["val"] = val; best["w"] = list(gw)

    rec(0, n)
    return best["w"], best["val"], stats["evals"]


def defender_best_response(y_weights, demands, v, D, c, p, r, N, m):
    v = np.asarray(v, float)
    supp = [(float(yk), list(wk)) for yk, wk in zip(y_weights, demands) if yk > 1e-12]
    best = {"val": -np.inf, "pl": None}
    evals = 0
    for pl in itertools.combinations(range(N), m):
        s = 0.0
        for yk, wk in supp:
            s += yk * _J(wk, pl, D, v, c, p, r, N); evals += 1
        if s > best["val"]:
            best["val"] = s; best["pl"] = pl
    return best["pl"], best["val"], evals


def double_oracle_oracle(v, D, N, m=2, n=10, c=4, p=0.7, r=9.0, verbose=True):
    global _MEMO; _MEMO = {}
    v = np.asarray(v, float)
    placements = list(itertools.combinations(range(N), m))
    R = [placements[0]]
    C = [tuple([n] + [0] * (N - 1))]
    total_att_evals = 0; total_def_evals = 0; iters = 0
    while True:
        iters += 1
        M = np.array([[_J(list(wk), pl, D, v, c, p, r, N) for wk in C] for pl in R])
        g = solve_matrix_game(M)
        x = g["x"]; y = g["y"]; val = g["value"]
        w_star, att_val, ev = attacker_best_response(x, R, v, D, c, p, r, N, n, warm=C)
        total_att_evals += ev
        pl_star, def_val, dev = defender_best_response(y, C, v, D, c, p, r, N, m)
        total_def_evals += dev
        added = False
        if att_val < val - 1e-7 and tuple(w_star) not in [tuple(z) for z in C]:
            C.append(tuple(w_star)); added = True
        if def_val > val + 1e-7 and pl_star not in R:
            R.append(pl_star); added = True
        if verbose:
            print(f"  iter {iters:2d}: value={val:.4f} |R|={len(R)} |C|={len(C)} "
                  f"att_BR={att_val:.4f} def_BR={def_val:.4f} att_evals(cum)={total_att_evals}")
        if not added:
            break
    return dict(value=val, iters=iters, nR=len(R), nC=len(C),
                support_def=int((g["x"] > 1e-6).sum()),
                support_att=int((g["y"] > 1e-6).sum()),
                att_evals=total_att_evals, def_evals=total_def_evals,
                memo_size=len(_MEMO),
                full_cols=comb(N + n - 1, n), full_matrix=len(placements) * comb(N + n - 1, n))


if __name__ == "__main__":
    D6 = [[0,10,8,4,14,11],[10,0,8,14,4,11],[8,8,0,11,11,18],
          [4,14,11,0,10,7],[14,4,11,10,0,7],[11,11,18,7,7,0]]
    res = double_oracle_oracle([1,1,1,5,3,10], np.asarray(D6, float), N=6, m=2, n=10, c=4, p=0.7, r=9)
    print(f"\nvalue={res['value']:.4f} iters={res['iters']} support {res['support_def']}x{res['support_att']} "
          f"att_evals={res['att_evals']} def_evals={res['def_evals']} memo={res['memo_size']}")
