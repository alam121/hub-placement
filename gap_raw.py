import numpy as np, itertools, time, json, sys, os
from exact_solver import exact_terminal
from general_solver import eval_pair
from vectorized_solver import compositions_array

N = int(sys.argv[1]); seed0 = int(sys.argv[2]); count = int(sys.argv[3])
budget = float(sys.argv[4]) if len(sys.argv) > 4 else 40.0
m, n, c, p, r = 2, 10, 4, 0.7, 12.0
path = "gap_raw.json"
data = json.load(open(path)) if os.path.exists(path) else []
t_start = time.time()

Sd = list(itertools.combinations(range(N), m))
Sa = compositions_array(n, N)
done = 0
for s in range(seed0, seed0 + count):
    if time.time() - t_start > budget:
        break
    rng = np.random.default_rng(s)
    coords = rng.uniform(0, 30, size=(N, 2))
    v = rng.integers(1, 11, size=N).astype(float)
    D = np.sqrt(((coords[:, None, :] - coords[None, :, :]) ** 2).sum(-1))
    order = sorted(range(N), key=lambda j: -v[j])
    E = np.empty((len(Sd), len(Sa))); G = np.empty((len(Sd), len(Sa)))
    for i, pl in enumerate(Sd):
        hs = set(pl)
        cov = {x: sorted([b for b in pl if D[b, x] < r], key=lambda b: D[b, x]) for x in range(N)}
        for k in range(len(Sa)):
            E[i, k] = exact_terminal(Sa[k], pl, D, v, c, p, r, N)
            G[i, k] = eval_pair(Sa[k], pl, D, v, c, p, r, N, hs, cov, order)
    d = E - G
    ex_mm, gr_mm = float(E.max(0).min()), float(G.max(0).min())
    ex_MM, gr_MM = float(E.min(1).max()), float(G.min(1).max())
    rec = dict(N=N, seed=s,
               minimax_gap_pct=round(100 * (ex_mm - gr_mm) / ex_mm, 3) if ex_mm else 0,
               maximin_gap_pct=round(100 * (ex_MM - gr_MM) / ex_MM, 3) if ex_MM else 0,
               frac_sub=round(float((d > 1e-9).mean()), 4),
               overstate=int((G - E > 1e-9).sum()))
    data = [x for x in data if not (x['N'] == N and x['seed'] == s)] + [rec]
    json.dump(data, open(path, "w"), indent=2)
    done += 1
print(f"N={N}: completed {done} instances (seeds {seed0}..{seed0+done-1}) in {time.time()-t_start:.1f}s", flush=True)
