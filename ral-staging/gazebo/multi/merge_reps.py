"""Merge the verified round (rep 0) with its two repetitions (verified_rep, reps 0-1 -> 1-2) into exact/verified_all,
then report run-to-run variability: per-leg arrival spread, on-time flips across repetitions, per-layout gain spread."""
import json, os, glob, shutil, collections
import numpy as np

B = "/home/claude/gz/multi/exact"
OUT = f"{B}/verified_all"
var = dict(legs=[], flips=0, legs_with_reps=0, layouts={})
for d in sorted(glob.glob(f"{B}/verified/*/")):
    L = os.path.basename(d.rstrip("/"))
    if L.startswith("willow"):
        continue
    os.makedirs(f"{OUT}/{L}", exist_ok=True)
    shutil.copy(f"{d}/pairs.json", f"{OUT}/{L}/pairs.json")
    res = json.load(open(f"{d}/gazebo_results.json")) if os.path.exists(f"{d}/gazebo_results.json") else []
    rp = f"{B}/verified_rep/{L}/gazebo_results.json"
    extra = json.load(open(rp)) if os.path.exists(rp) else []
    for r in extra:
        r = dict(r, rep=r["rep"] + 1); res.append(r)
    if res:
        json.dump(res, open(f"{OUT}/{L}/gazebo_results.json", "w"), indent=1)
    by = collections.defaultdict(list)
    for r in res:
        for l in r["legs"]:
            by[(r["pair"], l["robot"])].append(l)
    for k, ls in by.items():
        if len(ls) < 2:
            continue
        ok = [l for l in ls if l["status"] == "succeeded"]
        var["legs_with_reps"] += 1
        if len(set(l["on_time"] for l in ls)) > 1:
            var["flips"] += 1
        if len(ok) >= 2:
            a = np.array([l["arrival"] for l in ok])
            var["legs"].append(dict(layout=L, pair=k[0], robot=k[1], n=len(ok), sd=float(a.std(ddof=1)), range=float(a.max() - a.min()),
                                    slack=ls[0]["deadline"] - ls[0]["model_time"]))
sd = np.array([l["sd"] for l in var["legs"]]); rg = np.array([l["range"] for l in var["legs"]])
summ = dict(legs_with_reps=var["legs_with_reps"], on_time_flips=var["flips"], legs_timed=len(sd),
            sd_median=float(np.median(sd)), sd_p95=float(np.percentile(sd, 95)), range_max=float(rg.max()),
            range_median=float(np.median(rg)))
json.dump(dict(summary=summ, legs=var["legs"]), open(f"{OUT}/variability.json", "w"), indent=1)
print(json.dumps(summ, indent=1))
