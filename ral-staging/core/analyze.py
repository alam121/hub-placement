"""Summarize results.jsonl per pre-registered cell; apply the pre-registered decision rule."""
import json
import numpy as np
from scipy import stats

R = [json.loads(l) for l in open("results.jsonl")]
for r in R:
    r["G0"] = 100 * (r["V0"] - r["P"]) / r["P"]
    for q in (0.25, 0.5, 0.75):
        r[f"G{q}"] = 100 * (r[f"V{q}"] - r["P"]) / r["P"]
    r["ratio"] = r["m"] * r["c"] / 6


def ci(x):
    x = np.asarray(x, float)
    if len(x) < 2 or x.std(ddof=1) == 0:
        return float(x.mean()), 0.0
    return float(x.mean()), float(stats.t.ppf(0.975, len(x) - 1) * x.std(ddof=1) / np.sqrt(len(x)))


cells = {}
for r in R:
    cells.setdefault((r["m"], r["c"], r["density"], r["priority"]), []).append(r)

rows = []
for key in sorted(cells, key=lambda k: (k[0], k[1], ["sparse", "medium", "dense"].index(k[2]), k[3])):
    g = cells[key]
    G0, h0 = ci([r["G0"] for r in g])
    qs, hq = ci([r["qstar"] for r in g])
    rows.append(dict(m=key[0], c=key[1], density=key[2], priority=key[3], n=len(g),
                     ratio=round(key[0] * key[1] / 6, 2), G0=G0, G0_ci=h0,
                     G25=np.mean([r["G0.25"] for r in g]), G50=np.mean([r["G0.5"] for r in g]),
                     G75=np.mean([r["G0.75"] for r in g]),
                     qstar=qs, qstar_ci=hq, q_lb=np.mean([r["q_lb"] for r in g]),
                     pos=sum(r["G0"] > 1e-6 for r in g), ties=sum(r["tie_case"] for r in g),
                     lb_valid=all(r["q_lb"] <= r["qstar"] + 1e-6 for r in g),
                     support=np.mean([r["support0"] for r in g])))

print(f"{'m':>2} {'c':>2} {'dens':>7} {'prio':>8} {'mc/n':>5} {'G0%':>7} {'+-':>6} {'G.25':>6} {'G.5':>6} {'G.75':>6} {'q*':>6} {'+-':>5} {'q_lb':>5} pos ties supp")
for x in rows:
    print(f"{x['m']:>2} {x['c']:>2} {x['density']:>7} {x['priority']:>8} {x['ratio']:>5} {x['G0']:7.2f} {x['G0_ci']:6.2f} "
          f"{x['G25']:6.2f} {x['G50']:6.2f} {x['G75']:6.2f} {x['qstar']:6.3f} {x['qstar_ci']:5.2f} {x['q_lb']:5.2f} "
          f"{x['pos']:>3} {x['ties']:>4} {x['support']:4.1f}")

print("\nq_lb <= q* in every instance:", all(x["lb_valid"] for x in rows))
passing = [x for x in rows if x["m"] >= 3 and x["ratio"] <= 1 and x["G0"] >= 5 and x["G0"] - x["G0_ci"] > 0 and x["qstar"] >= 0.25]
print("Pre-registered decision rule passing cells:", [(x["m"], x["c"], x["density"], x["priority"], round(x["G0"], 2), round(x["qstar"], 3)) for x in passing])
print("DECISION:", "CONTINUE" if passing else "STOP")
for m in (2, 3, 4):
    sub = [r for r in R if r["m"] == m]
    print(f"m={m}: mean G0 {np.mean([r['G0'] for r in sub]):.2f}%, share with gain {np.mean([r['G0']>1e-6 for r in sub]):.2f}, max G0 {max(r['G0'] for r in sub):.2f}%")
json.dump(rows, open("summary.json", "w"), indent=1, default=float)
