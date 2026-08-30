"""
Two-model equilibrium statistics over many random networks:
V_seq (pure maximin), V_sim (mixed LP value), concealment gain, support sizes,
and the greedy mixed-value gap. Shows whether the benchmark's 0.38 concealment
gain and small support are typical.
"""
import numpy as np, itertools, json, sys
from exact_solver import solve_exact
from general_solver import eval_pair, compositions as gcomp
from game_lp import solve_matrix_game

N = int(sys.argv[1]); count = int(sys.argv[2]); seed0 = int(sys.argv[3]) if len(sys.argv) > 3 else 40000
m, n, c, p, r = 2, 10, 4, 0.7, 12.0
rows = []
for s in range(seed0, seed0 + count):
    rng = np.random.default_rng(s)
    coords = rng.uniform(0, 30, size=(N, 2)); v = rng.integers(1, 11, size=N).astype(float)
    D = np.sqrt(((coords[:, None, :] - coords[None, :, :]) ** 2).sum(-1))
    Uex = solve_exact(coords=coords.tolist(), v=v, m=m, n=n, c=c, p=p, r=r)['U']
    gex = solve_matrix_game(Uex)
    # greedy matrix
    Sd = list(itertools.combinations(range(N), m)); Sa = list(gcomp(n, N))
    order = sorted(range(N), key=lambda j: -v[j])
    Ug = np.empty((len(Sd), len(Sa)))
    for i, pl in enumerate(Sd):
        hs = set(pl); cov = {x: sorted([b for b in pl if D[b, x] < r], key=lambda b: D[b, x]) for x in range(N)}
        for k, w in enumerate(Sa):
            Ug[i, k] = eval_pair(w, pl, D, v, c, p, r, N, hs, cov, order)
    gg = solve_matrix_game(Ug)
    Vseq, Vsim = gex['pure_maximin'], gex['value']
    row = dict(N=N, seed=s, Vseq=round(Vseq, 3), Vsim=round(Vsim, 3),
               conceal=round(Vsim - Vseq, 3),
               def_support=int((gex['x'] > 1e-6).sum()), att_support=int((gex['y'] > 1e-6).sum()),
               Vg=round(gg['value'], 3),
               greedy_gap_pct=round(100 * (Vsim - gg['value']) / Vsim, 2))
    rows.append(row)
    print(f"seed {s}: Vseq={row['Vseq']:.3f} Vsim={row['Vsim']:.3f} conceal={row['conceal']:.3f} "
          f"supp={row['def_support']}x{row['att_support']} greedy_gap={row['greedy_gap_pct']:.1f}%", flush=True)

path = f"multi_N{N}.json"
import os
prev = json.load(open(path)) if os.path.exists(path) else []
prev = [x for x in prev if x['seed'] not in {r['seed'] for r in rows}] + rows
json.dump(prev, open(path, "w"), indent=2)
