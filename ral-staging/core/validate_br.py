"""Brute-force check of the B&B attacker best response: N=20 zones, n=6 (177,100 allocations), random mixtures."""
import json, itertools, numpy as np
from sim import scenario
from evaluator import compositions, full_matrix
from scale_solver import attacker_br
W = compositions(6, 20); rng = np.random.default_rng(11); worst = 0.0; n = 0
for prio in ("skewed", "uniform"):
    for kind in ("warehouse", "office", "campus"):
        for c in (1, 2):
            sc = scenario(kind, 1300 + c, K=12, N=20, density=0.2, priority=prio, c=c, min_sep=5.0)
            cov = np.array([sum(1 << i for i in range(12) if sc["A"][i, j]) for j in range(20)], np.int64)
            pls = list(itertools.combinations(range(12), 3))
            for _ in range(3):
                idx = rng.choice(len(pls), int(rng.integers(1, 5)), replace=False)
                dms = np.array([sum(1 << i for i in pls[k]) for k in idx], np.int64)
                xw = rng.dirichlet(np.ones(len(idx)))
                U = full_matrix(dms, W, cov, sc["v"], c, 0.7)
                brute = float((xw @ U).min())
                val, w, nodes = attacker_br(dms, xw, cov, sc["v"], c, 0.7, 6, np.argsort(-sc["v"], kind="stable").astype(np.int64), 1e18)
                worst = max(worst, abs(val - brute)); n += 1
print(json.dumps({"checks": n, "max_abs_diff": worst}))
json.dump({"checks": n, "max_abs_diff": worst}, open("validate_br.json", "w"))
