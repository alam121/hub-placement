"""Fig. 5 follow-up: navigation-model discrepancy near the response deadline.
(a) Measured legs whose model slack |t_model + service - deadline| <= 10 s: errors and classification flips.
(b) Across all 15 sparse layouts: share of site-zone pairs whose model slack is smaller than the 95th percentile
    of |Nav2 - model| time error (pairs whose reachability could plausibly flip)."""
import sys, json
import numpy as np
sys.path.insert(0, "/home/claude/ral")
from sim import scenario
SPEED, SERVICE = 1.5, 30.0
legs = []
for m in ("warehouse", "office", "campus"):
    L = json.load(open(f"/home/claude/gz/results/{m}.json"))["legs"]
    bad = {i + 1 for i, l in enumerate(L) if l["status"] != "succeeded"}
    legs += [dict(l, map=m) for i, l in enumerate(L) if l["status"] == "succeeded" and i not in bad and l["kind"] == "response"]
SC = {k: scenario(k, 700, density=0.20, priority="skewed", c=1) for k in ("warehouse", "office", "campus")}
rows = []
for l in legs:
    i, j = (l["frm"][1], l["to"][1]) if l["frm"][0] == "s" else (l["to"][1], l["frm"][1])
    dl = SC[l["map"]]["dl_mat"][i, j]; tm = l["model_len"] / SPEED
    rows.append(dict(slack=dl - (tm + SERVICE), err=l["sim_time"] - tm, rel=(l["sim_time"] - tm) / tm,
                     flip=bool((tm + SERVICE <= dl) != (l["sim_time"] + SERVICE <= dl))))
err = np.array([r["err"] for r in rows]); absr = np.abs([r["rel"] for r in rows])
near = [r for r in rows if abs(r["slack"]) <= 10]
p95 = float(np.percentile(np.abs(err), 95))
out = dict(n_legs=len(rows), abs_err_s_median=float(np.median(np.abs(err))), abs_err_s_p95=p95, abs_err_s_max=float(np.abs(err).max()),
           signed_err_s_mean=float(err.mean()), near_n=len(near), near_abs_err_s_median=float(np.median([abs(r["err"]) for r in near])) if near else None,
           near_flips=int(sum(r["flip"] for r in near)), all_flips=int(sum(r["flip"] for r in rows)))
tot = vuln = vuln_arcs = 0
for k in ("warehouse", "office", "campus"):
    for lay in range(5):
        sc = scenario(k, 700 + lay, density=0.20, priority="skewed", c=1)
        slack = sc["dl_mat"] - (sc["Dsz"] / SPEED + SERVICE)
        tot += slack.size; vuln += int((np.abs(slack) < p95).sum()); vuln_arcs += int(((np.abs(slack) < p95) & (sc["A"] == 1)).sum())
out.update(pairs_total=tot, pairs_within_p95=vuln, share_within_p95=vuln / tot, reachable_arcs_within_p95=vuln_arcs)
# pessimistic check: tighten every deadline by the p95 error; evaluate grid-model policies on the tightened reachability
from evaluator import build
from leakage import solve_q
g = {0.0: [], 0.25: [], 0.5: []}; reo = {0.0: [], 0.25: [], 0.5: []}
for k in ("warehouse", "office", "campus"):
    for lay in range(5):
        sc = scenario(k, 700 + lay, density=0.20, priority="skewed", c=1)
        A1 = ((sc["Dsz"] / SPEED + SERVICE) <= sc["dl_mat"] - p95).astype(np.int64)
        for j in range(A1.shape[1]):
            if A1[:, j].sum() == 0: A1[int(np.argmin(sc["Dsz"][:, j])), j] = 1
        _, _, U0 = build(dict(A=sc["A"], v=sc["v"], c=1, p=0.7), 3, 6); _, _, U1 = build(dict(A=A1, v=sc["v"], c=1, p=0.7), 3, 6)
        f0 = np.zeros(len(U0)); f0[int(np.argmax(U0.min(1)))] = 1
        for q in g:
            V = lambda U, x: (1 - q) * float((U.T @ x).min()) + q * float(x @ U.min(1))
            x0 = solve_q(U0, q)["x"]; g[q].append(100 * (V(U1, x0) - V(U1, f0)) / V(U1, f0))
            P1 = float(U1.min(1).max()); reo[q].append(100 * (solve_q(U1, q)["value"] - P1) / P1)
for q in g:
    d = np.array(g[q]); r = np.array(reo[q])
    out[f"tight_transfer_gain_{q}"] = [float(d.mean()), float(1.96 * d.std(ddof=1) / np.sqrt(len(d))), int((d > 0).sum())]
    out[f"tight_reopt_gain_{q}"] = [float(r.mean()), float(1.96 * r.std(ddof=1) / np.sqrt(len(r)))]
print(json.dumps(out, indent=1)); json.dump(dict(summary=out, legs=rows), open("near_deadline.json", "w"), indent=1, default=float)
