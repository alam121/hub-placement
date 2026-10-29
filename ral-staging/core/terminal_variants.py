"""R5: sensitivity of the concealment benefit to the terminal-response model.

Variants (all with the same instances as the 540-game grid, m in {3,4}, c in {1,2}):
  * aon_p0.7  : baseline all-or-nothing restoration, p = 0.7 (from results.jsonl)
  * aon_p0.5, aon_p0.9 : all-or-nothing with lower / higher robot reliability
  * partial   : partial credit, zone j earns v_j * (resolved alarms / w_j); each served alarm resolves w.p. p = 0.7.
    Expected value sum_{w_j=0} v_j + sum_j (v_j p / w_j) s_j, maximised over feasible served counts s.
    Feasible count vectors form a transversal matroid on alarm units (Gale condition), and every unit of
    zone j has weight v_j p / w_j, so the greedy rule (zones by weight, as many units as feasible) is exact.
"""
import json, sys
import numpy as np
from numba import njit
from multiprocessing import Pool
from evaluator import compositions, placements, full_matrix, _popcount
from instances import make_instance
from leakage import solve_q, q_star


@njit(cache=True)
def terminal_pc(dmask, w, covmask, v, c, p):
    N = w.shape[0]
    loaded = np.empty(N, np.int64); L = 0; base = 0.0
    for j in range(N):
        if w[j] == 0: base += v[j]
        else: loaded[L] = j; L += 1
    if L == 0: return base
    wt = np.empty(L)
    for t in range(L): wt[t] = v[loaded[t]] * p / w[loaded[t]]
    order = np.argsort(-wt)
    s = np.zeros(L, np.int64)
    cap = np.zeros(1 << L, np.int64)
    for T in range(1, 1 << L):
        nb = 0
        for t in range(L):
            if (T >> t) & 1: nb |= covmask[loaded[t]] & dmask
        cap[T] = c * _popcount(nb)
    val = base
    for k in range(L):
        t = order[k]; j = loaded[t]
        room = w[j]
        for T in range(1, 1 << L):
            if (T >> t) & 1:
                used = 0
                for u in range(L):
                    if u != t and (T >> u) & 1: used += s[u]
                r = cap[T] - used
                if r < room: room = r
        if room > 0:
            s[t] = room; val += wt[t] * room
    return val


@njit(cache=True)
def full_matrix_pc(dmasks, W, covmask, v, c, p):
    U = np.empty((dmasks.shape[0], W.shape[0]))
    for i in range(dmasks.shape[0]):
        for k in range(W.shape[0]):
            U[i, k] = terminal_pc(dmasks[i], W[k], covmask, v, c, p)
    return U


def job(r):
    inst = make_instance(r["seed"], r["density"], r["priority"], r["c"])
    P_ = placements(12, r["m"]); W = compositions(6, 12)
    dm = np.array([sum(1 << int(i) for i in pl) for pl in P_], np.int64)
    cov = np.array([sum(1 << i for i in range(12) if inst["A"][i, j]) for j in range(12)], np.int64)
    out = dict(m=r["m"], c=r["c"], density=r["density"], priority=r["priority"], s=r["s"])
    for name in ("aon_p0.5", "aon_p0.9", "partial"):
        if name == "partial":
            U = full_matrix_pc(dm, W, cov, inst["v"], r["c"], 0.7)
        else:
            U = full_matrix(dm, W, cov, inst["v"], r["c"], float(name[-3:]))
        mv = U.min(1); P = float(mv.max())
        g0 = 100 * (solve_q(U, 0.0, mv)["value"] - P) / P
        g5 = 100 * (solve_q(U, 0.5, mv)["value"] - P) / P
        qs = q_star(U, P, mv)[0] if g0 > 1e-6 else 0.0
        out[name] = dict(G0=g0, G5=g5, qstar=qs)
    out["aon_p0.7"] = dict(G0=100 * (r["V0"] - r["P"]) / r["P"], G5=100 * (r["V0.5"] - r["P"]) / r["P"],
                           qstar=r["qstar"] if r["V0"] - r["P"] > 1e-6 * r["P"] else 0.0)
    return out


if __name__ == "__main__":
    R = [json.loads(l) for l in open("results.jsonl")]
    R = [r for r in R if r["m"] in (3, 4) and r["c"] in (1, 2)]
    with Pool(2) as pool:
        out = pool.map(job, R, chunksize=2)
    json.dump(out, open("terminal_variants.json", "w"), indent=1)
    ci = lambda d: (np.mean(d), 1.96 * np.std(d, ddof=1) / np.sqrt(len(d)))
    V = ("aon_p0.7", "aon_p0.5", "aon_p0.9", "partial")
    print("all 240 instances (m=3,4; c=1,2; all densities/priorities)")
    for name in V:
        g = ci([o[name]["G0"] for o in out]); g5 = ci([o[name]["G5"] for o in out])
        print(f"{name:9s} G0 {g[0]:5.2f}+-{g[1]:4.2f}  G0.5 {g5[0]:5.2f}+-{g5[1]:4.2f}  q* {np.mean([o[name]['qstar'] for o in out]):.3f}  gain>0 {sum(o[name]['G0'] > 1e-6 for o in out)}")
    print("favourable cell (sparse, c=1, skewed; m=3,4: 20 instances)")
    sub = [o for o in out if o["density"] == "sparse" and o["c"] == 1 and o["priority"] == "skewed"]
    for name in V:
        g = ci([o[name]["G0"] for o in sub]); g5 = ci([o[name]["G5"] for o in sub])
        print(f"{name:9s} G0 {g[0]:5.2f}+-{g[1]:4.2f}  G0.5 {g5[0]:5.2f}+-{g5[1]:4.2f}  q* {np.mean([o[name]['qstar'] for o in sub]):.3f}")
    rank = np.corrcoef([o["aon_p0.7"]["G0"] for o in out], [o["partial"]["G0"] for o in out])[0, 1]
    print("correlation of per-instance G0, all-or-nothing vs partial credit:", round(rank, 3))
