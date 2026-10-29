"""Check the matrix-free solver against the full-matrix results (results.jsonl) on random grid instances."""
import json, time, numpy as np
from instances import make_instance
from evaluator import placements
from scale_solver import Solver
R=[json.loads(l) for l in open("results.jsonl")]
rng=np.random.default_rng(5); pick=[R[i] for i in rng.choice(len(R),24,replace=False)]
worst=0.0; rows=[]
for r in pick:
    inst=make_instance(r["seed"],r["density"],r["priority"],r["c"])
    S=Solver(inst["A"],inst["v"],r["c"],0.7,r["m"],6,[list(p) for p in placements(12,r["m"])]); S.init()
    t=time.time(); out={}
    for q,key in ((0.0,"V0"),(0.25,"V0.25"),(0.5,"V0.5")):
        res=S.solve(q); d=abs(res["value"]-r[key]); worst=max(worst,d); out[key]=d
    dP=abs(res["P"]-r["P"]); worst=max(worst,dP)
    rows.append(dict(m=r["m"],c=r["c"],dens=r["density"],sec=time.time()-t,attacks=len(S.W),**out,dP=dP))
    print(rows[-1],flush=True)
print("MAX ABS DIFF",worst)
json.dump(dict(cases=len(rows),max_abs_diff=worst,rows=rows),open("validate_scale.json","w"),indent=1)
