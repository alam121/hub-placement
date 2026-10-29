"""Validate the Hall-condition evaluator against (a) the original max-flow exact_terminal code
and (b) an independent MILP (SciPy/HiGHS), for m = 2, 3, 4 and c = 1, 2, 3."""
import sys, json, time
import numpy as np
from scipy.optimize import milp, LinearConstraint, Bounds
from evaluator import terminal, compositions, placements
from instances import make_instance

sys.path.insert(0, sys.argv[1])  # folder with the ORIGINAL exact_solver.py (max-flow)
from exact_solver import exact_terminal  # noqa: E402


def milp_terminal(pl, w, A, v, c, p):
    K, N = A.shape
    arcs = [(i, j) for i in pl for j in range(N) if A[i, j] and w[j] > 0]
    loaded = [j for j in range(N) if w[j] > 0]
    nx, ny = len(arcs), len(loaded)
    obj = np.zeros(nx + ny)
    for k, j in enumerate(loaded):
        obj[nx + k] = -v[j] * p ** w[j]
    rows, lb, ub = [], [], []
    for i in pl:  # capacity
        r = np.zeros(nx + ny)
        for a, (ii, j) in enumerate(arcs):
            if ii == i:
                r[a] = 1
        rows.append(r); lb.append(-np.inf); ub.append(c)
    for k, j in enumerate(loaded):  # exact delivery: sum_i x_ij - w_j y_j = 0
        r = np.zeros(nx + ny)
        for a, (ii, jj) in enumerate(arcs):
            if jj == j:
                r[a] = 1
        r[nx + k] = -w[j]
        rows.append(r); lb.append(0); ub.append(0)
    bounds = Bounds(np.zeros(nx + ny), np.r_[np.full(nx, np.inf), np.ones(ny)])
    res = milp(obj, constraints=LinearConstraint(np.array(rows), lb, ub),
               integrality=np.ones(nx + ny), bounds=bounds)
    base = sum(v[j] for j in range(N) if w[j] == 0)
    return base - res.fun


rng = np.random.default_rng(2026)
W = compositions(6, 12)
out = {"cases": 0, "max_abs_diff_maxflow": 0.0, "max_abs_diff_milp": 0.0, "by_m": {}}
t0 = time.time()
for m in (2, 3, 4):
    for c in (1, 2, 3):
        for dens in ("sparse", "medium", "dense"):
            for prio in ("uniform", "skewed"):
                inst = make_instance(int(rng.integers(1e9)), dens, prio, c)
                A, v = inst["A"], inst["v"]
                P = placements(12, m)
                covmask = np.array([sum(1 << i for i in range(12) if A[i, j]) for j in range(12)], np.int64)
                Dfake = np.where(A == 1, 0.0, 2.0)  # original code: covered iff D <= r
                for _ in range(15):
                    pl = P[rng.integers(len(P))]
                    w = W[rng.integers(len(W))]
                    dm = sum(1 << int(i) for i in pl)
                    a = terminal(dm, w, covmask, v, c, inst["p"])
                    b = exact_terminal(list(w), tuple(int(i) for i in pl), Dfake, v, c, inst["p"], 1.0, 12)
                    d = milp_terminal([int(i) for i in pl], w, A, v, c, inst["p"])
                    out["cases"] += 1
                    out["max_abs_diff_maxflow"] = max(out["max_abs_diff_maxflow"], abs(a - b))
                    out["max_abs_diff_milp"] = max(out["max_abs_diff_milp"], abs(a - d))
                    out["by_m"][str(m)] = out["by_m"].get(str(m), 0) + 1
out["seconds"] = time.time() - t0
print(json.dumps(out, indent=1))
json.dump(out, open("validation.json", "w"), indent=1)
