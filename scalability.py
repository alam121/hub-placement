import numpy as np, time, json
from math import comb
from general_solver import solve

rng = np.random.default_rng(7)
m, n, c, p, r = 2, 10, 4, 0.7, 12.0

rows = []
for N in range(6, 13):
    coords = rng.uniform(0, 30, size=(N, 2))
    v = rng.integers(1, 11, size=N).tolist()
    t0 = time.time()
    res = solve(coords.tolist(), v, m=m, n=n, c=c, p=p, r=r)
    wall = time.time() - t0
    rows.append(dict(N=N, nSd=res['nSd'], nSa=res['nSa'], pairs=res['pairs'],
                     seconds=round(wall, 3),
                     attacker_minimax=round(res['attacker_minimax'], 3)))
    print(f"N={N:2d}  Sd={res['nSd']:4d}  Sa={res['nSa']:8d}  pairs={res['pairs']:11,d}  "
          f"time={wall:8.2f}s  f(u*)={res['attacker_minimax']:.3f}")

json.dump(rows, open("scalability_results.json", "w"), indent=2)
print("\nSaved scalability_results.json")
