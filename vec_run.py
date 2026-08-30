import numpy as np, time, json, sys, os
from vectorized_solver import solve_vec

lo, hi = int(sys.argv[1]), int(sys.argv[2])
m, n, c, p, r = 2, 10, 4, 0.7, 12.0
path = "scal_vec.json"
data = json.load(open(path)) if os.path.exists(path) else []
for N in range(lo, hi + 1):
    rng = np.random.default_rng(1000 + N)          # same networks as pure-Python run
    coords = rng.uniform(0, 30, size=(N, 2))
    v = rng.integers(1, 11, size=N).tolist()
    t0 = time.time()
    res = solve_vec(coords=coords.tolist(), v=v, m=m, n=n, c=c, p=p, r=r)
    wall = time.time() - t0
    row = dict(N=N, nSd=res['nSd'], nSa=res['nSa'], pairs=res['pairs'],
               seconds=round(wall, 3), attacker_minimax=round(res['attacker_minimax'], 3))
    data = [d for d in data if d['N'] != N] + [row]
    data.sort(key=lambda d: d['N'])
    json.dump(data, open(path, "w"), indent=2)
    print(f"N={N:2d}  Sa={res['nSa']:9d}  pairs={res['pairs']:13,d}  "
          f"time={wall:7.2f}s  f(u*)={row['attacker_minimax']:.3f}", flush=True)
