"""Run the pre-registered grid. Results appended per instance to results.jsonl (resumable)."""
import json, os, sys, time
import numpy as np
from multiprocessing import Pool
from evaluator import build
from instances import make_instance
from leakage import solve_q, q_star

N_REQ = 6
DENS = ["sparse", "medium", "dense"]
PRIO = ["uniform", "skewed"]
OUT = "results.jsonl"


def job(args):
    m, c, dens, prio, s = args
    seed = 50000 + 1000 * DENS.index(dens) + 100 * PRIO.index(prio) + s
    inst = make_instance(seed, dens, prio, c)
    t0 = time.time()
    Pl, W, U = build(inst, m, N_REQ)
    mvec = U.min(1)
    P = float(mvec.max())
    r0 = solve_q(U, 0.0, mvec)
    res = dict(m=m, c=c, density=dens, priority=prio, s=s, seed=seed, P=P,
               V0=r0["value"], z0=r0["z"], b0=r0["b"], n_place=len(Pl),
               support0=int((r0["x"] > 1e-6).sum()))
    for q in (0.25, 0.5, 0.75):
        res[f"V{q}"] = solve_q(U, q, mvec)["value"]
    qs, tie, ntied = q_star(U, P, mvec)
    res.update(qstar=qs, tie_case=tie, n_tied_best=ntied)
    res["q_lb"] = ((r0["z"] - P) / (r0["z"] - r0["b"])) if (r0["z"] - P) > 1e-9 and (r0["z"] - r0["b"]) > 1e-12 else 0.0
    res["sec"] = time.time() - t0
    return res


if __name__ == "__main__":
    done = set()
    if os.path.exists(OUT):
        for line in open(OUT):
            d = json.loads(line)
            done.add((d["m"], d["c"], d["density"], d["priority"], d["s"]))
    jobs = [(m, c, d, p, s) for m in (2, 3, 4) for c in (1, 2, 3) for d in DENS for p in PRIO
            for s in range(10) if (m, c, d, p, s) not in done]
    print(len(jobs), "jobs", flush=True)
    with Pool(int(sys.argv[1]) if len(sys.argv) > 1 else 2) as pool, open(OUT, "a") as f:
        for i, r in enumerate(pool.imap_unordered(job, jobs)):
            f.write(json.dumps(r) + "\n"); f.flush()
            if i % 20 == 0:
                print(i, r["m"], r["c"], r["density"], r["priority"], round(r["sec"], 1), flush=True)
