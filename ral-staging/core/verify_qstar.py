"""Independent check of q*: bracket it with the re-optimized V*(q) LP on random instances."""
import json, numpy as np
from evaluator import build
from instances import make_instance
from leakage import solve_q
R=[json.loads(l) for l in open("results.jsonl")]
rng=np.random.default_rng(1)
pick=[R[i] for i in rng.choice(len(R),40,replace=False) if R[i]["qstar"]>0.02]
bad=0; n=0
for r in pick:
    inst=make_instance(r["seed"],r["density"],r["priority"],r["c"]); _,_,U=build(inst,r["m"],6)
    P=U.min(1).max(); qs=r["qstar"]; tol=1e-7*max(1,P)
    below=solve_q(U,max(qs-0.01,0))["value"]>P+tol
    above=True if qs>=0.999 else solve_q(U,min(qs+0.01,1))["value"]<=P+1e-6*max(1,P)
    n+=1; bad+= not(below and above)
    if not(below and above): print("MISMATCH",r["m"],r["c"],r["density"],r["priority"],r["s"],qs)
print(json.dumps({"checked":n,"mismatches":bad}))
json.dump({"checked":n,"mismatches":bad},open("verify_qstar.json","w"))
