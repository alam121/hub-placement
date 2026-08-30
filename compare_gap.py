"""
Optimality gap of the greedy heuristic vs the exact (max-flow) optimum, across N.
For each random network: build exact utility matrix U and greedy matrix G, then report
per-pair gap and the gap in the two security (equilibrium) values.
"""
import numpy as np, itertools, time, json, sys, os
from exact_solver import exact_terminal
from general_solver import eval_pair
from vectorized_solver import compositions_array

lo, hi = int(sys.argv[1]), int(sys.argv[2])
reps = int(sys.argv[3]) if len(sys.argv) > 3 else 3
m, n, c, p, r = 2, 10, 4, 0.7, 12.0
path = "gap_results.json"
data = json.load(open(path)) if os.path.exists(path) else []


def matrices(D, v, N):
    Sd = list(itertools.combinations(range(N), m))
    Sa = compositions_array(n, N)
    order = sorted(range(N), key=lambda j: -v[j])
    E = np.empty((len(Sd), len(Sa))); G = np.empty((len(Sd), len(Sa)))
    for i, pl in enumerate(Sd):
        hs = set(pl)
        cov = {x: sorted([s for s in pl if D[s, x] < r], key=lambda s: D[s, x]) for x in range(N)}
        for k in range(len(Sa)):
            w = Sa[k]
            E[i, k] = exact_terminal(w, pl, D, v, c, p, r, N)
            G[i, k] = eval_pair(w, pl, D, v, c, p, r, N, hs, cov, order)
    return E, G


for N in range(lo, hi + 1):
    agg = {'pair_max': [], 'pair_mean': [], 'frac_sub': [],
           'minimax_gap_pct': [], 'maximin_gap_pct': [], 'secs': []}
    for rep in range(reps):
        rng = np.random.default_rng(30000 + 100 * N + rep)
        coords = rng.uniform(0, 30, size=(N, 2))
        v = rng.integers(1, 11, size=N).astype(float)
        D = np.sqrt(((coords[:, None, :] - coords[None, :, :]) ** 2).sum(-1))
        t0 = time.time()
        E, G = matrices(D, v, N)
        secs = time.time() - t0
        d = E - G
        ex_mm, gr_mm = float(E.max(0).min()), float(G.max(0).min())      # minimax
        ex_MM, gr_MM = float(E.min(1).max()), float(G.min(1).max())      # maximin
        agg['pair_max'].append(float(d.max()))
        agg['pair_mean'].append(float(d.mean()))
        agg['frac_sub'].append(float((d > 1e-9).mean()))
        agg['minimax_gap_pct'].append(100 * (ex_mm - gr_mm) / ex_mm if ex_mm else 0)
        agg['maximin_gap_pct'].append(100 * (ex_MM - gr_MM) / ex_MM if ex_MM else 0)
        agg['secs'].append(secs)
    row = {'N': N, 'reps': reps}
    for k, vals in agg.items():
        row[k] = round(float(np.mean(vals)), 4)
    data = [x for x in data if x['N'] != N] + [row]
    data.sort(key=lambda x: x['N'])
    json.dump(data, open(path, "w"), indent=2)
    print(f"N={N}: minimax_gap={row['minimax_gap_pct']:5.2f}%  maximin_gap={row['maximin_gap_pct']:6.2f}%  "
          f"frac_pairs_suboptimal={row['frac_sub']:.3f}  mean_pair_gap={row['pair_mean']:.4f}  "
          f"({row['secs']:.1f}s/inst)", flush=True)
