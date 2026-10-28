"""Closed-loop simulation study (pre-registered in PREREGISTRATION.md addendum).
3 maps x 5 layouts x 2 regimes; 5 policies; q in {0, .25, .5}; 1000 shifts each."""
import json, sys, time
import numpy as np
from multiprocessing import Pool
from sim import scenario, Sim
from leakage import solve_q

MAPS = ["warehouse", "office", "campus"]
REGIMES = {"sparse": 0.20, "dense": 0.60}
QS = [0.0, 0.25, 0.5]
SHIFTS = 1000
M, C = 3, 1


def model_value(U, mvec, x, q):
    return (1 - q) * float((U.T @ x).min()) + q * float(x @ mvec)


def job(args):
    kind, layout, regime = args
    t0 = time.time()
    sc = scenario(kind, 700 + layout, density=REGIMES[regime], priority="skewed", c=C)
    s = Sim(sc, M)
    U, mvec = s.U, s.mvec
    D = len(U)
    fixed = np.zeros(D); fixed[int(np.argmax(mvec))] = 1
    # MEXCLP-style: maximize sum_j v_j (1 - 0.5^{k_j}), k_j = open docks covering j (capacity ignored)
    k = np.array([[sc["A"][list(pl), j].sum() for j in range(len(sc["v"]))] for pl in s.P])
    mex = np.zeros(D); mex[int(np.argmax(((1 - 0.5 ** k) * sc["v"]).sum(1)))] = 1
    unif = np.ones(D) / D
    x0 = solve_q(U, 0.0, mvec)["x"]
    out = []
    for q in QS:
        xq = solve_q(U, q, mvec)["x"]
        pols = {"fixed_maximin": fixed, "mexclp": mex, "uniform_random": unif, "concealed_q0": x0, "leakage_aware": xq}
        for name, x in pols.items():
            rng = np.random.default_rng(hash((kind, layout, regime, q, name)) % 2**32)
            r = s.run(x, q, SHIFTS, rng)
            out.append(dict(map=kind, layout=layout, regime=regime, q=q, policy=name,
                            model=model_value(U, mvec, x, q), P=float(mvec.max()),
                            deadline=sc["deadline"], density=float(sc["A"].mean()),
                            support=int((x > 1e-6).sum()), **r))
    print(kind, layout, regime, round(time.time() - t0, 1), "s", flush=True)
    return out


if __name__ == "__main__":
    jobs = [(k, l, r) for k in MAPS for l in range(5) for r in REGIMES]
    with Pool(int(sys.argv[1]) if len(sys.argv) > 1 else 2) as pool:
        res = [row for rows in pool.imap_unordered(job, jobs) for row in rows]
    json.dump(res, open("sim_results.json", "w"), indent=1)
    print("rows", len(res))
