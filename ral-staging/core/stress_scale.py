import json, sys, time, itertools
from math import comb
from sim import scenario
from scale_solver import Solver
N, K, m, n, c, prio, kind, lay = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]), sys.argv[6], sys.argv[7], int(sys.argv[8])
sc = scenario(kind, 900 + 10 * N + lay, K=K, N=N, density=0.20, priority=prio, c=c, min_sep=4.0)
pl = [list(p) for p in itertools.combinations(range(K), m)]
S = Solver(sc["A"], sc["v"], c, 0.7, m, n, pl); S.init()
out = dict(N=N, K=K, m=m, n=n, c=c, priority=prio, map=kind, layout=lay, n_place=len(pl), n_attacks_total=comb(N + n - 1, n))
t0 = time.time()
for q in (0.0, 0.5):
    t = time.time(); r = S.solve(q); out[f"V{q}"] = r["value"]; out[f"sec{q}"] = time.time() - t
out.update(P=r["P"], sec=time.time() - t0, nodes=S.nodes, br_calls=S.br_calls, attacks_generated=len(S.W))
out["G0"] = 100 * (out["V0.0"] - out["P"]) / out["P"]; out["G0.5"] = 100 * (out["V0.5"] - out["P"]) / out["P"]
print(json.dumps(out), flush=True)
