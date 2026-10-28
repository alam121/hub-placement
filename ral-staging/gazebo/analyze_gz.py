"""Compare Gazebo/Nav2 travel times with the paper's grid travel-time model, then re-evaluate the
paper's policies when reachability is rebuilt from Nav2-calibrated times."""
import sys, json
import numpy as np
sys.path.insert(0, "/home/claude/ral")
from sim import scenario
from evaluator import build
from leakage import solve_q, q_star

SPEED, SERVICE = 1.5, 30.0
meta = json.load(open("/home/claude/gz/maps/meta.json"))
legs = []
for m in ("warehouse", "office", "campus"):
    try:
        legs += json.load(open(f"/home/claude/gz/results/{m}.json"))["legs"]
    except FileNotFoundError:
        pass
bad_start = set()
for i, l in enumerate(legs):
    if l["status"] != "succeeded" and i + 1 < len(legs) and legs[i + 1]["map"] == l["map"]:
        bad_start.add(i + 1)  # next leg did not start from its intended node
ok = [l for i, l in enumerate(legs) if l["status"] == "succeeded" and i not in bad_start]
out = {"legs_total": len(legs), "legs_succeeded": sum(l["status"] == "succeeded" for l in legs), "legs_used": len(ok), "excluded_after_failure": len(bad_start),
       "status_counts": {s: sum(l["status"] == s for l in legs) for s in set(l["status"] for l in legs)}}

resp = [l for l in ok if l["kind"] == "response"]
x = np.array([l["model_len"] / SPEED for l in resp]); y = np.array([l["sim_time"] for l in resp])
A = np.vstack([x, np.ones_like(x)]).T
(alpha, beta), *_ = np.linalg.lstsq(A, y, rcond=None)
pred = alpha * x + beta
out["response_fit"] = dict(n=len(resp), alpha=alpha, beta=beta,
                           r2=1 - ((y - pred) ** 2).sum() / ((y - y.mean()) ** 2).sum(),
                           median_ratio_nav2_over_model=float(np.median(y / x)),
                           mape_uncalibrated=float(np.mean(np.abs(y - x) / y)),
                           mape_calibrated=float(np.mean(np.abs(y - pred) / y)),
                           nav2_eff_speed_mean=float(np.mean([l["model_len"] / l["sim_time"] for l in resp])),
                           odom_over_model_len=float(np.median([l["odom_dist"] / l["model_len"] for l in resp])))
# reachability agreement on measured pairs (same deadline as the paper's map)
SC0 = {k: scenario(k, 700, density=0.20, priority="skewed", c=1) for k in ("warehouse", "office", "campus")}
agree = []; conf = {"tp": 0, "tn": 0, "fp": 0, "fn": 0}
for l in resp:
    i, j = (l["frm"][1], l["to"][1]) if l["frm"][0] == "s" else (l["to"][1], l["frm"][1])
    dl = SC0[l["map"]]["dl_mat"][i, j]
    m_r = l["model_len"] / SPEED + SERVICE <= dl + 1e-9
    n_r = l["sim_time"] + SERVICE <= dl + 1e-9
    agree.append(m_r == n_r)
    conf[("t" if m_r == n_r else "f") + ("p" if m_r else "n")] += 1
out["reachability_agreement"] = dict(rate=float(np.mean(agree)), **conf)
rel = [l for l in ok if l["kind"] == "relocation"]
if rel:
    out["relocation"] = dict(n=len(rel), median_ratio=float(np.median([l["sim_time"] / (l["model_len"] / SPEED) for l in rel])),
                             mean_time=float(np.mean([l["sim_time"] for l in rel])))

# re-evaluation under calibrated reachability: all 15 sparse layouts, m=3, c=1, skewed
def calibrated_A(sc):
    t_cal = alpha * sc["Dsz"] / SPEED + beta + SERVICE
    A = (t_cal <= sc["deadline"]).astype(np.int64)
    for j in range(A.shape[1]):
        if A[:, j].sum() == 0:
            A[int(np.argmin(t_cal[:, j])), j] = 1
    return A

rows = []
for kind in ("warehouse", "office", "campus"):
    for layout in range(5):
        sc = scenario(kind, 700 + layout, density=0.20, priority="skewed", c=1)
        A1 = calibrated_A(sc)
        _, _, U0 = build(dict(A=sc["A"], v=sc["v"], c=1, p=0.7), 3, 6)
        _, _, U1 = build(dict(A=A1, v=sc["v"], c=1, p=0.7), 3, 6)
        fixed0 = np.zeros(len(U0)); fixed0[int(np.argmax(U0.min(1)))] = 1
        r = dict(map=kind, layout=layout, arc_agreement=float((A1 == sc["A"]).mean()),
                 density_model=float(sc["A"].mean()), density_nav2=float(A1.mean()))
        for q in (0.0, 0.25, 0.5):
            V = lambda U, xx: (1 - q) * float((U.T @ xx).min()) + q * float(xx @ U.min(1))
            x0 = solve_q(U0, q)["x"]
            P1 = float(U1.min(1).max())
            r[f"model_gain_{q}"] = 100 * (V(U0, x0) - V(U0, fixed0)) / V(U0, fixed0)
            r[f"transfer_gain_{q}"] = 100 * (V(U1, x0) - V(U1, fixed0)) / V(U1, fixed0)
            r[f"reopt_gain_{q}"] = 100 * (solve_q(U1, q)["value"] - P1) / P1
        r["qstar_model"] = q_star(U0, float(U0.min(1).max()))[0]
        r["qstar_nav2"] = q_star(U1, float(U1.min(1).max()))[0]
        rows.append(r)
def mci(k):
    d = np.array([r[k] for r in rows]); return [float(d.mean()), float(1.96 * d.std(ddof=1) / np.sqrt(len(d))), int((d > 0).sum())]
reeval = {"n_layouts": len(rows), "arc_agreement": float(np.mean([r["arc_agreement"] for r in rows])),
          "identical_reachability_layouts": int(sum(r["arc_agreement"] == 1.0 for r in rows)),
          **{k: mci(k) for k in rows[0] if k.startswith(("model_gain", "transfer_gain", "reopt_gain", "qstar"))},
          "rows": rows}
out["reevaluation"] = reeval
print(json.dumps(out, indent=1, default=float))
json.dump(out, open("/home/claude/gz/gz_summary.json", "w"), indent=1, default=float)
