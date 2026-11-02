"""Solver ablation on identical instances (K=12 sites, m=3 docks -> 220 configurations, n=6 alarms, c=1, sparse,
skewed; one layout per map type; N in {12,16,20,25,30} zones). Each method computes P and V*(0) exactly.
  full : build the full payoff matrix (all |W| attacks), then constraint generation over its columns
  cg   : matrix-free constraint generation; separation = exact attacker best response by enumerating all |W|
  bb   : matrix-free constraint generation; separation = branch-and-bound with the joint-recourse bound (ours)
Threshold (N=12, full matrix available): bisection on V*(q) to 1e-3 vs one Charnes-Cooper LP.
Each method runs in its own process with a time limit; full is skipped when the matrix would exceed 1.2 GB."""
import json, sys, time, itertools
from math import comb
import numpy as np
from numba import njit
from multiprocessing import Process, Queue
from sim import scenario
from scale_solver import Solver
from evaluator import build, terminal
from leakage import solve_q, q_star

LIMIT = 600.0
K, M, NAL = 12, 3, 6


@njit(cache=True)
def enum_br(dms, xw, covmask, v, c, p, n, N):
    """exact attacker best response by enumerating all weak compositions of n into N parts (NEXCOM)"""
    r = np.zeros(N + 2, np.int64)
    best = 1e300; bestw = np.zeros(N, np.int64); cnt = 0
    w = np.zeros(N, np.int64)
    mtc = False; t = 0; h = 0
    while True:
        if mtc:
            if t > 1:
                h = 0
            h += 1
            t = r[h]; r[h] = 0; r[1] = t - 1; r[h + 1] += 1
        else:
            r[1] = n
            for i in range(2, N + 1):
                r[i] = 0
            t = n; h = 0
        mtc = r[N] != n
        for i in range(N):
            w[i] = r[i + 1]
        val = 0.0
        for k in range(dms.shape[0]):
            val += xw[k] * terminal(dms[k], w, covmask, v, c, p)
        cnt += 1
        if val < best:
            best = val
            for i in range(N):
                bestw[i] = w[i]
        if not mtc:
            break
    return best, bestw, cnt


class EnumSolver(Solver):
    def br(self, idx, xw, incumbent):
        val, w, cnt = enum_br(self.dmasks[idx], xw, self.covmask, self.v, self.c, self.p, self.n, len(self.v))
        self.nodes += cnt; self.br_calls += 1
        return val, w


def inst(kind, N):
    return scenario(kind, 1700 + N, K=K, N=N, density=0.20, priority="skewed", c=1, min_sep=5.0)


def run_method(method, kind, N, q):
    sc = inst(kind, N)
    t0 = time.time()
    if method == "full":
        P_, W, U = build(dict(A=sc["A"], v=sc["v"], c=1, p=0.7), M, NAL)
        tb = time.time() - t0
        P = float(U.min(1).max()); V = solve_q(U, 0.0)["value"]
        q.put(dict(P=P, V=V, sec=time.time() - t0, build_sec=tb)); return
    pl = [list(c) for c in itertools.combinations(range(K), M)]
    S = (EnumSolver if method == "cg" else Solver)(sc["A"], sc["v"], 1, 0.7, M, NAL, pl); S.init()
    r = S.solve(0.0)
    q.put(dict(P=r["P"], V=r["value"], sec=time.time() - t0, br_calls=S.br_calls, evals=S.nodes, attacks=len(S.W)))


def timed(method, kind, N):
    q = Queue(); pr = Process(target=run_method, args=(method, kind, N, q)); pr.start(); pr.join(LIMIT)
    if pr.is_alive():
        pr.terminate(); pr.join(); return dict(status="timeout", sec=LIMIT)
    return dict(status="ok", **q.get()) if not q.empty() else dict(status="error")


def threshold_ablation(kind):
    sc = inst(kind, 12)
    _, _, U = build(dict(A=sc["A"], v=sc["v"], c=1, p=0.7), M, NAL)
    P = float(U.min(1).max())
    t0 = time.time(); qs, tie, _ = q_star(U, P); t_lf = time.time() - t0
    t0 = time.time(); lo, hi, solves = 0.0, 1.0, 0
    if solve_q(U, 0.0)["value"] <= P * (1 + 1e-9):
        hi = 0.0
    while hi - lo > 1e-3:
        mid = (lo + hi) / 2; solves += 1
        if solve_q(U, mid)["value"] > P * (1 + 1e-9): lo = mid
        else: hi = mid
    return dict(map=kind, qstar=qs, tie=tie, lf_sec=t_lf, bisect_interval=[lo, hi], bisect_solves=solves, bisect_sec=time.time() - t0)


if __name__ == "__main__":
    enum_br(np.array([7], np.int64), np.array([1.0]), np.array([1, 2, 4], np.int64), np.ones(3), 1, 0.7, 2, 3)  # compile
    extra = len(sys.argv) > 1 and sys.argv[1] == "extra"
    out = json.load(open("ablation.json"))["rows"] if extra else []
    for N in ((40, 50) if extra else (12, 16, 20, 25, 30)):
        for kind in ("warehouse", "office", "campus"):
            row = dict(N=N, map=kind, W=comb(N + NAL - 1, NAL))
            for meth in ("full", "cg", "bb"):
                if meth == "full" and 220 * row["W"] * 8 > 1.2e9:
                    row[meth] = dict(status="memory"); continue
                row[meth] = timed(meth, kind, N)
            vals = [row[m_]["V"] for m_ in ("full", "cg", "bb") if row[m_].get("status") == "ok"]
            row["max_disagreement"] = float(max(vals) - min(vals)) if len(vals) > 1 else 0.0
            print(N, kind, {m_: (row[m_]["status"], round(row[m_].get("sec", 0), 2)) for m_ in ("full", "cg", "bb")}, "disagree", row["max_disagreement"], flush=True)
            out.append(row)
            json.dump(dict(rows=out), open("ablation.json", "w"), indent=1)
    th = [threshold_ablation(k) for k in ("warehouse", "office", "campus")]
    for t in th: print(t, flush=True)
    json.dump(dict(rows=out, threshold=th), open("ablation.json", "w"), indent=1)
