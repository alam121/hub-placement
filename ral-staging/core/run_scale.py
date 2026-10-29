"""Scaling study: N in {30,40,50} zones, K=20 staging sites, m=3 docks (1140 configurations), n=6 alarms
(1.6M-3.3M+ demand allocations; never enumerated). Sparse reachability, skewed priorities, c in {1,2}.
3 maps x 3 layouts per (N, c). Exact V*(q) for q in {0, .25, .5} and P via the matrix-free solver."""
import json, sys, time, itertools
from math import comb
import numpy as np
from multiprocessing import Pool
from sim import scenario
from scale_solver import Solver

def job(a):
    N, c, kind, lay = a
    sc = scenario(kind, 900 + 10 * N + lay, K=20, N=N, density=0.20, priority="skewed", c=c, min_sep=5.0)
    pl = [list(p) for p in itertools.combinations(range(20), 3)]
    S = Solver(sc["A"], sc["v"], c, 0.7, 3, 6, pl); S.init()
    t0 = time.time(); out = dict(N=N, c=c, map=kind, layout=lay, n_attacks_total=comb(N + 5, 6), n_place=len(pl))
    for q in (0.0, 0.25, 0.5):
        t = time.time(); r = S.solve(q)
        out[f"V{q}"] = r["value"]; out[f"sec{q}"] = time.time() - t; out[f"supp{q}"] = r["support"]
    out.update(P=r["P"], attacks_generated=len(S.W), nodes=S.nodes, br_calls=S.br_calls, sec=time.time() - t0)
    for q in (0.0, 0.25, 0.5):
        out[f"G{q}"] = 100 * (out[f"V{q}"] - out["P"]) / out["P"]
    print(N, c, kind, lay, round(out["sec"], 1), "s", "G0 %.2f" % out["G0.0"], flush=True)
    return out

if __name__ == "__main__":
    jobs = [(N, c, k, l) for N in (30, 40, 50) for c in (1, 2) for k in ("warehouse", "office", "campus") for l in range(3)]
    if len(sys.argv) > 2: jobs = jobs[:int(sys.argv[2])]
    with Pool(int(sys.argv[1])) as pool, open("scale_results.jsonl", "w") as f:
        for r in pool.imap_unordered(job, jobs):
            f.write(json.dumps(r) + "\n"); f.flush()
