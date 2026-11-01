"""Exact expected value under concurrent Nav2 execution.
For every (placement, attack) pair the policy can produce, Gazebo gives each dispatched leg an on-time indicator.
Value of a pair = unloaded zones + sum over served zones of v_j * p^{w_j} * 1{all legs to j on time}
(success draws integrated analytically). Policy value = sum_pairs prob * value. With every leg on time this
reproduces U(d,a), so the model's V_x(q) and P are recovered exactly. Usage: analyze_exact.py <mode> [layouts]"""
import json, sys, glob, os
import numpy as np

MODE = sys.argv[1]
B = f"/home/claude/gz/multi/exact/{MODE}"
lays = sys.argv[2:] or sorted(os.path.basename(os.path.dirname(p)) for p in glob.glob(f"{B}/*/pairs.json") if "willow" not in p)


def pair_value(cfg, pr, on):
    v, p, w = cfg["v"], cfg["p"], pr["attack"]
    val = sum(v[j] for j in range(len(w)) if w[j] == 0)
    for j in pr["served"]:
        legs = [i for i, l in enumerate(pr["route"]) if l["zone"] == j]
        if all(on[i] for i in legs):
            val += v[j] * p ** w[j]
    return val


rows, legs_all, disp = [], [], []
failed = {}
for L in lays:
    cfg = json.load(open(f"{B}/{L}/pairs.json"))
    rp = f"{B}/{L}/gazebo_results.json"
    res = json.load(open(rp)) if os.path.exists(rp) else []
    assert res or not any(p["route"] for p in cfg["pairs"]), L
    reps = sorted(set(r["rep"] for r in res)) or [0]
    out = dict(layout=L, pairs=len(cfg["pairs"]), reps=len(reps), P=cfg["P"], Vx=cfg["Vx"])
    out["model_gain"] = 100 * (cfg["Vx"] - cfg["P"]) / cfg["P"]
    for rep in reps:
        rr = {r["pair"]: r for r in res if r["rep"] == rep}
        for pi, pr in enumerate(cfg["pairs"]):      # no-mover pairs need no execution: value is exact
            if pi not in rr and not pr["route"]:
                rr[pi] = dict(pair=pi, rep=rep, legs=[], min_pair_dist=None)
        if len(rr) < len(cfg["pairs"]):
            continue
        Vla = Vfx = Mla = Mfx = 0.0
        for pi, pr in enumerate(cfg["pairs"]):
            on = [l["on_time"] for l in rr[pi]["legs"]]
            val, mval = pair_value(cfg, pr, on), pair_value(cfg, pr, [True] * len(pr["route"]))
            assert abs(mval - pr["model_value"]) < 1e-9, (L, pi, mval, pr["model_value"])
            Vla += pr["prob_la"] * val; Vfx += pr["prob_fixed"] * val
            Mla += pr["prob_la"] * mval; Mfx += pr["prob_fixed"] * mval
            if rep == reps[0] and rr[pi]["legs"]:
                d = rr[pi]
                disp.append(dict(layout=L, movers=len(d["legs"]), overlap_s=d.get("overlap_s", 0.0), min_d=d["min_pair_dist"],
                                 relevant=pr["prob_la"] + pr["prob_fixed"] > 0))
                for l, rl in zip(d["legs"], pr["route"]):
                    legs_all.append(dict(layout=L, concurrent=len(d["legs"]) >= 2, offset=rl.get("offset_m", 0.0), **l))
                    if not l["on_time"]:
                        failed.setdefault(L, []).append([l["dock"], l["zone"]])
        assert abs(Mla - cfg["Vx"]) < 1e-6 and abs(Mfx - cfg["P"]) < 1e-6
        out.setdefault("realized_la", []).append(Vla); out.setdefault("realized_fixed", []).append(Vfx)
        out.setdefault("realized_gain", []).append(100 * (Vla - Vfx) / Vfx)
    rows.append(out)

ok = [l for l in legs_all if l["status"] == "succeeded"]
err = np.array([l["arrival"] - l["model_time"] for l in ok])
conc = [d for d in disp if d["movers"] >= 2]
mg = np.array([r["model_gain"] for r in rows]); rg = np.array([np.mean(r["realized_gain"]) for r in rows])
from scipy.stats import t as tdist
ci = lambda d: [float(d.mean()), float(tdist.ppf(0.975, len(d) - 1) * d.std(ddof=1) / np.sqrt(len(d)))] if len(d) > 1 else [float(d.mean()), 0.0]
summ = dict(mode=MODE, layouts=len(rows), dispatches=len(disp), concurrent_dispatches=len(conc),
            concurrent_3=sum(d["movers"] == 3 for d in disp), overlap_s_total=float(sum(d["overlap_s"] for d in disp)),
            legs=len(legs_all), legs_concurrent=sum(l["concurrent"] for l in legs_all),
            succeeded=len(ok), aborted=sum(l["status"] == "aborted" for l in legs_all),
            timeout=sum(l["status"] == "timeout" for l in legs_all), late=sum(l["status"] == "succeeded" and not l["on_time"] for l in legs_all),
            on_time=sum(l["on_time"] for l in legs_all),
            arr_err_mean=float(err.mean()) if len(err) else None, arr_err_p95=float(np.percentile(np.abs(err), 95)) if len(err) else None,
            arr_err_conc_mean=float(np.mean([l["arrival"] - l["model_time"] for l in ok if l["concurrent"]])) if ok else None,
            min_inter_robot=float(min(d["min_d"] for d in conc)) if conc else None,
            arr_err_shared_p95=None,
            model_gain=ci(mg), realized_gain=ci(rg),
            layouts_realized_positive=int((rg > 1e-9).sum()), layouts_model_positive=int((mg > 1e-9).sum()),
            layouts_realized_eq_model=int(sum(abs(a - b) < 1e-6 for a, b in zip(rg, mg))),
            mean_P=float(np.mean([r["P"] for r in rows])),
            mean_realized_fixed=float(np.mean([np.mean(r["realized_fixed"]) for r in rows])))
json.dump(dict(summary=summ, layouts=rows, failed_arcs=failed, legs=legs_all), open(f"{B}/summary{'_willow' if all('willow' in L for L in lays) else ''}.json", "w"), indent=1, default=float)
print(json.dumps(summ, indent=1))
for r in rows:
    print(r["layout"], "model %.1f%%" % r["model_gain"], "realized", [round(g, 1) for g in r["realized_gain"]],
          "P %.2f fixed_real %s" % (r["P"], [round(x, 2) for x in r["realized_fixed"]]), "failed", failed.get(r["layout"], []))
