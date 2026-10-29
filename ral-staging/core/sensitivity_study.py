"""R6: one-factor-at-a-time sensitivity around the simulation's base regime, on the 15 map layouts
(warehouse/office/campus x 5). Base: m=3 docks, c=1, n=6 alarms, reachability density 0.20, Zipf priority
exponent 1 (= 'skewed'), p=0.7. Factors: n in {4,6,8}; density in {0.15,0.20,0.30,0.45};
Zipf exponent in {0,0.5,1,2}; fleet (m,c) in {(3,1),(3,2),(4,1)}. Exact values with the matrix-free solver;
q* by bisection on the exact V*(q) (tolerance 1e-3), q* = 1 if V*(0.999) > P."""
import json, itertools, numpy as np
from multiprocessing import Pool
from sim import scenario
from scale_solver import Solver

BASE = dict(n=6, density=0.20, alpha=1.0, m=3, c=1)
FACT = {"n": [4, 6, 8], "density": [0.15, 0.20, 0.30, 0.45], "alpha": [0.0, 0.5, 1.0, 2.0], "fleet": [(3, 1), (3, 2), (4, 1)]}


def solve(cfg, kind, lay):
    sc = scenario(kind, 700 + lay, density=cfg["density"], priority=f"zipf:{cfg['alpha']}", c=cfg["c"])
    pl = [list(p) for p in itertools.combinations(range(12), cfg["m"])]
    S = Solver(sc["A"], sc["v"], cfg["c"], 0.7, cfg["m"], cfg["n"], pl); S.init()
    V = {q: S.solve(q)["value"] for q in (0.0, 0.25, 0.5)}
    P = S.solve(0.0)["P"]
    tol = 1e-7 * P
    if V[0.0] <= P + tol: qs = 0.0
    elif S.solve(0.999)["value"] > P + tol: qs = 1.0
    else:
        lo, hi = 0.0, 0.999
        while hi - lo > 1e-3:
            mid = (lo + hi) / 2
            if S.solve(mid)["value"] > P + tol: lo = mid
            else: hi = mid
        qs = (lo + hi) / 2
    return dict(G0=100 * (V[0.0] - P) / P, G25=100 * (V[0.25] - P) / P, G5=100 * (V[0.5] - P) / P, qstar=qs)


def job(a):
    factor, level, kind, lay = a
    cfg = dict(BASE)
    if factor == "fleet": cfg["m"], cfg["c"] = level
    else: cfg[factor] = level
    return dict(factor=factor, level=str(level), map=kind, layout=lay, **solve(cfg, kind, lay))


if __name__ == "__main__":
    jobs = [(f, l, k, y) for f, ls in FACT.items() for l in ls for k in ("warehouse", "office", "campus") for y in range(5)]
    with Pool(2) as pool:
        out = pool.map(job, jobs, chunksize=3)
    json.dump(out, open("sensitivity_study.json", "w"), indent=1)
    ci = lambda d: (np.mean(d), 1.96 * np.std(d, ddof=1) / np.sqrt(len(d)))
    for f, ls in FACT.items():
        for l in ls:
            g = [o for o in out if o["factor"] == f and o["level"] == str(l)]
            a, b = ci([o["G0"] for o in g]), ci([o["G25"] for o in g])
            print(f"{f:8s} {str(l):8s} G0 {a[0]:5.2f}+-{a[1]:4.2f} G.25 {b[0]:5.2f}+-{b[1]:4.2f} G.5 {np.mean([o['G5'] for o in g]):5.2f} q* {np.mean([o['qstar'] for o in g]):.2f} gain>0 {sum(o['G0'] > 1e-6 for o in g)}/15")
