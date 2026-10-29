import json, numpy as np
S=json.load(open("sim_results.json"))
def rel(r):
    b=[x for x in S if x["regime"]==r["regime"] and x["q"]==r["q"] and x["policy"]=="fixed_maximin" and x["map"]==r["map"] and x["layout"]==r["layout"]][0]
    return 100*(r["mean"]-b["mean"])/b["mean"]
out=[]
for reg in ("sparse","dense"):
  for q in (0.0,0.25,0.5):
    for p in ("mexclp","uniform_random","concealed_q0","leakage_aware"):
        g=[r for r in S if r["regime"]==reg and r["q"]==q and r["policy"]==p]
        d=np.array([rel(r) for r in g])
        row=dict(regime=reg,q=q,policy=p,mean=d.mean(),ci=1.96*d.std(ddof=1)/np.sqrt(len(d)),wins=int((d>0).sum()),
                 reloc=np.mean([r["reloc_m"] for r in g]),tau=np.mean([r["tau_s"] for r in g]),obs=np.mean([r["observed_frac"] for r in g]))
        out.append(row); print(f"{reg} q={q} {p:15s} {row['mean']:6.2f}+-{row['ci']:5.2f} wins {row['wins']}/15 reloc {row['reloc']:5.1f} tau {row['tau']:4.1f} obs {row['obs']:.3f}")
m=np.array([r["model"] for r in S]); s=np.array([r["mean"] for r in S])
print("corr", np.corrcoef(m,s)[0,1].round(3), "mean gap %", (100*(s-m)/m).mean().round(2))
json.dump(out,open("sim_summary.json","w"),indent=1)
