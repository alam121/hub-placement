"""Real floor-plan case study (Willow Garage office): same protocol as the 15 synthetic layouts.
5 site/zone layouts x {sparse, dense}; exact model gains and q*, and the closed-loop simulation (1000 paired shifts)."""
import json, sys
import numpy as np
from multiprocessing import Pool
import sim_experiment as se
from sim import scenario, Sim
from leakage import solve_q, q_star

def model(lay):
    sc = scenario("willow", 700 + lay, density=0.20, priority="skewed", c=1); s = Sim(sc, 3)
    U, m = s.U, s.mvec; P = float(m.max())
    r = dict(layout=lay, P=P, density=float(sc["A"].mean()), deadline=sc["deadline"], n_place=len(U), n_attack=U.shape[1])
    for q in (0.0, 0.25, 0.5):
        r[f"G{q}"] = 100 * (solve_q(U, q, m)["value"] - P) / P
    r["qstar"] = q_star(U, P, m)[0]
    return r

if __name__ == "__main__":
    se.MAPS = ["willow"]
    with Pool(2) as pool:
        mod = pool.map(model, range(5))
        sim = [row for rows in pool.imap_unordered(se.job, [("willow", l, r) for l in range(5) for r in se.REGIMES]) for row in rows]
    json.dump(dict(model=mod, sim=sim), open("willow_results.json", "w"), indent=1)
    for r in mod: print(r)
