import numpy as np, time, json, sys, os
from vectorized_solver import solve_vec

lo, hi = int(sys.argv[1]), int(sys.argv[2])
reps = int(sys.argv[3]) if len(sys.argv) > 3 else 5
m, n, c, p, r = 2, 10, 4, 0.7, 12.0
path = "scal_bench.json"
data = json.load(open(path)) if os.path.exists(path) else []

for N in range(lo, hi + 1):
    times = []
    for rep in range(reps):
        rng = np.random.default_rng(20000 + 100 * N + rep)   # distinct instance per rep
        coords = rng.uniform(0, 30, size=(N, 2))
        v = rng.integers(1, 11, size=N).tolist()
        t0 = time.time()
        res = solve_vec(coords=coords.tolist(), v=v, m=m, n=n, c=c, p=p, r=r)
        times.append(time.time() - t0)
    times = np.array(times)
    row = dict(N=N, reps=reps, nSd=res['nSd'], nSa=res['nSa'], pairs=res['pairs'],
               mean_s=round(float(times.mean()), 3), std_s=round(float(times.std(ddof=1)), 3),
               min_s=round(float(times.min()), 3), max_s=round(float(times.max()), 3))
    data = [d for d in data if d['N'] != N] + [row]
    data.sort(key=lambda d: d['N'])
    json.dump(data, open(path, "w"), indent=2)
    print(f"N={N:2d}  pairs={res['pairs']:13,d}  mean={row['mean_s']:7.3f}s  "
          f"sd={row['std_s']:6.3f}  [{row['min_s']:.3f}, {row['max_s']:.3f}]  (reps={reps})", flush=True)
