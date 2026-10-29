"""Lemma 2 with strictly positive priorities, verified exactly (evaluator + full attack enumeration).
Sites {1,2,3,4} (0-indexed 0..3), m = 2 docks, c = 1, n = 2 alarms, p = 0.9.
Zone A (v=10) reachable only from sites 1,2; zone B (v=1) reachable only from sites 3,4.
x : {1,2} or {3,4} w.p. 1/2;   x': {1,3} or {2,4} w.p. 1/2.  Both open every site w.p. 1/2."""
import json, itertools, numpy as np
from evaluator import terminal, compositions
A = np.array([[1, 0], [1, 0], [0, 1], [0, 1]]); v = np.array([10.0, 1.0]); c, p, n = 1, 0.9, 2
cov = np.array([sum(1 << i for i in range(4) if A[i, j]) for j in range(2)], np.int64)
W = compositions(n, 2)
mask = lambda pl: sum(1 << i for i in pl)
pols = {"x": [((0, 1), .5), ((2, 3), .5)], "x_prime": [((0, 2), .5), ((1, 3), .5)]}
out = {}
for name, pol in pols.items():
    rows = {}
    for w in W:
        rows[str(tuple(int(a) for a in w))] = {str(tuple(i + 1 for i in pl)): terminal(mask(pl), w, cov, v, c, p) for pl, _ in pol}
    exp = {k: sum(pr * terminal(mask(pl), np.array(eval(k)), cov, v, c, p) for pl, pr in pol) for k in rows}
    marg = [sum(pr for pl, pr in pol if i in pl) for i in range(4)]
    out[name] = dict(payoffs=rows, expected=exp, z=min(exp.values()), worst_attack=min(exp, key=exp.get), marginals=marg)
    print(name, "marginals", marg, "expected by attack", {k: round(e, 3) for k, e in exp.items()}, "z =", round(out[name]["z"], 3))
json.dump(out, open("lemma2_example.json", "w"), indent=1)
