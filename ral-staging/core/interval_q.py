"""Uncertain leakage q in [ql, qh] (15 sparse layouts, m=3, c=1).
V_x(q) = (1-q) z(x) + q b(x) is linear and non-increasing in q (b <= z), so the max-min policy over the interval is x*(qh).
Regret V*(q) - V_x(q) is convex in q (V* convex, V_x linear), so its maximum over the interval is at an endpoint:
the minimax-regret policy is one LP:  min r  s.t.  z <= U[:,a].x (all a),  r >= V*(qk) - (1-qk) z - qk mu.x  (k = l, h)."""
import json
import numpy as np
from scipy.optimize import linprog
from scipy.sparse import csr_matrix, hstack, vstack, identity
from sim import scenario, Sim
from leakage import solve_q

QL, QH = 0.2, 0.5


def Vx(U, mu, x, q):
    return (1 - q) * float((U.T @ x).min()) + q * float(x @ mu)


def minimax_regret(U, mu, Vl, Vh):
    D, A = U.shape                     # variables: x (D), z, r
    c = np.r_[np.zeros(D), 0.0, 1.0]
    # z - U[:,a].x <= 0
    G1 = hstack([csr_matrix(-U.T), csr_matrix(np.ones((A, 1))), csr_matrix((A, 1))])
    rows = []; rhs = []
    for q, V in ((QL, Vl), (QH, Vh)):  # V - (1-q) z - q mu.x - r <= 0
        rows.append(np.r_[-q * mu, -(1 - q), -1.0]); rhs.append(-V)
    G = vstack([G1, csr_matrix(np.array(rows))]).tocsr()
    b = np.r_[np.zeros(A), rhs]
    res = linprog(c, A_ub=G, b_ub=b, A_eq=np.r_[np.ones(D), 0, 0][None, :], b_eq=[1.0],
                  bounds=[(0, None)] * D + [(None, None), (None, None)], method="highs")
    x = np.clip(res.x[:D], 0, None); return x / x.sum()


rows = []
for kind in ("warehouse", "office", "campus"):
    for lay in range(5):
        sc = scenario(kind, 700 + lay, density=0.20, priority="skewed", c=1); s = Sim(sc, 3)
        U, mu = s.U, s.mvec; P = float(mu.max())
        fixed = np.zeros(len(U)); fixed[int(np.argmax(mu))] = 1
        Vs = {q: solve_q(U, q, mu) for q in (0.0, QL, 0.35, QH)}
        pols = {"fixed": fixed, "x*(0)": Vs[0.0]["x"], "x*(mid)": Vs[0.35]["x"], "x*(qh)": Vs[QH]["x"]}
        pols["minimax-regret"] = minimax_regret(U, mu, Vs[QL]["value"], Vs[QH]["value"])
        r = dict(map=kind, layout=lay, P=P, Vl=Vs[QL]["value"], Vh=Vs[QH]["value"])
        for name, x in pols.items():
            vl, vh = Vx(U, mu, x, QL), Vx(U, mu, x, QH)
            r[name] = dict(worst_gain=100 * (min(vl, vh) - P) / P,
                           max_regret=100 * max((Vs[QL]["value"] - vl) / Vs[QL]["value"], (Vs[QH]["value"] - vh) / Vs[QH]["value"]))
        rows.append(r)
summ = {}
for name in ("fixed", "x*(0)", "x*(mid)", "x*(qh)", "minimax-regret"):
    wg = np.array([r[name]["worst_gain"] for r in rows]); mr = np.array([r[name]["max_regret"] for r in rows])
    t = 2.145 / np.sqrt(len(rows))
    summ[name] = dict(worst_gain=[float(wg.mean()), float(t * wg.std(ddof=1))], max_regret_mean=float(mr.mean()), max_regret_max=float(mr.max()),
                      worst_below_fixed=int((wg < -1e-9).sum()))
json.dump(dict(interval=[QL, QH], summary=summ, rows=rows), open("interval_q.json", "w"), indent=1)
print(json.dumps(summ, indent=1))
