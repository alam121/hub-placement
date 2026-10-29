"""R1: policy-dependent relocation exposure.

Physical model (as in the simulator): configurations are re-drawn i.i.d. each shift of length H; robots
relocate along shortest paths (docks matched by min total distance); relocation lasts
tau(d,d') = max matched path length / speed; an attack uniformly timed in the shift that lands during
relocation sees the destination configuration. Hence the effective observation probability depends on x:
    q_eff(x) = q + (1-q) * E_x[tau]/H,   E_x[tau] = sum_{d,d'} x_d x_d' tau(d,d')
and the end-to-end value is V_end(x) = (1-q_eff(x)) z(x) + q_eff(x) b(x)   (quadratic in x, not an LP).
Exposure-aware policy: best V_end among the exogenous optima x*(q') for q' on a grid in [0,1]
(an exact evaluation of each candidate; a lower bound on the end-to-end optimum).
Outputs per (layout, q, H): exogenous policy's V_end, exposure-aware V_end, P, exposure, and the
end-to-end threshold q*_end(H). Also a closed-loop check with H = 15 min."""
import json, zlib
import numpy as np
from multiprocessing import Pool
from scipy.optimize import linear_sum_assignment
from sim import scenario, Sim
from leakage import solve_q

HS = {"8h": 8 * 3600.0, "1h": 3600.0, "15min": 900.0, "5min": 300.0, "2min": 120.0}
QS = [0.0, 0.25, 0.5]
QGRID = sorted(set(np.round(np.arange(0.0, 1.0001, 0.02), 2).tolist()) | {0.25, 0.75})


def tau_fn(sc, P):
    cache = {}
    def tau(a, b):
        if a == b: return 0.0
        k = (min(a, b), max(a, b))
        if k not in cache:
            C = sc["Dss"][np.ix_(P[a], P[b])]
            r, c = linear_sum_assignment(C)
            cache[k] = float(C[r, c].max()) / sc["speed"]
        return cache[k]
    return tau


def job(args):
    kind, layout = args
    sc = scenario(kind, 700 + layout, density=0.20, priority="skewed", c=1)
    s = Sim(sc, 3); U, mvec = s.U, s.mvec; P = float(mvec.max())
    tau = tau_fn(sc, s.P)
    cands = {float(qq): solve_q(U, float(qq), mvec)["x"] for qq in QGRID}
    stats = {}
    for qq, x in cands.items():
        S = np.where(x > 1e-9)[0]
        Et = sum(x[a] * x[b] * tau(a, b) for a in S for b in S)
        stats[qq] = dict(z=float((U.T @ x).min()), b=float(x @ mvec), Et=Et, supp=len(S))
    def vend(st, q, H):
        qe = q + (1 - q) * st["Et"] / H
        return (1 - qe) * st["z"] + qe * st["b"], qe
    rows = []
    for Hn, H in HS.items():
        for q in QS:
            ex, qe_ex = vend(stats[float(q)], q, H)
            best_q, (best, qe_b) = max(((qq, vend(st, q, H)) for qq, st in stats.items()), key=lambda t: t[1][0])
            rows.append(dict(map=kind, layout=layout, H=Hn, q=q, P=P,
                             exo_gain=100 * (ex - P) / P, aware_gain=100 * (max(best, P) - P) / P,
                             exo_below_fixed=bool(ex < P - 1e-9), qeff_exo=qe_ex, exposure_exo=stats[float(q)]["Et"] / H,
                             Et_exo=stats[float(q)]["Et"], design_q=best_q))
        # end-to-end threshold: largest q on a fine grid with best candidate strictly above P
        qend = 0.0
        for q in np.arange(0, 1.0001, 0.01):
            if max(vend(st, q, H)[0] for st in stats.values()) > P + 1e-7 * P:
                qend = float(q)
        rows.append(dict(map=kind, layout=layout, H=Hn, q="threshold", qstar_end=qend))
    # closed-loop check at H = 15 min, q = 0.25: fixed vs exogenous x*(q) vs exposure-aware
    H = HS["15min"]; q = 0.25
    best_q = max(stats, key=lambda qq: vend(stats[qq], q, H)[0])
    fixed = np.zeros(len(U)); fixed[int(np.argmax(mvec))] = 1
    seed = zlib.crc32(f"{kind}|{layout}|reloc15".encode())
    cl = {}
    for name, x in (("fixed", fixed), ("exogenous", cands[q]), ("aware", cands[best_q])):
        cl[name] = s.run(x, q, 2000, seed, shift_len=H)
    rows.append(dict(map=kind, layout=layout, H="15min", q="closed_loop", design_q=best_q,
                     **{f"{k}_mean": v["mean"] for k, v in cl.items()},
                     **{f"{k}_obs": v["observed_frac"] for k, v in cl.items()}))
    return rows


if __name__ == "__main__":
    jobs = [(k, l) for k in ("warehouse", "office", "campus") for l in range(5)]
    with Pool(2) as pool:
        rows = [r for rr in pool.map(job, jobs) for r in rr]
    json.dump(rows, open("relocation_study.json", "w"), indent=1)
    ci = lambda d: (np.mean(d), 1.96 * np.std(d, ddof=1) / np.sqrt(len(d)))
    print(f"{'H':>6} {'q':>5} {'exposure%':>9} {'exo gain':>14} {'aware gain':>14} {'exo<fixed':>9}")
    for Hn in HS:
        for q in QS:
            g = [r for r in rows if r["H"] == Hn and r["q"] == q]
            e, a = ci([r["exo_gain"] for r in g]), ci([r["aware_gain"] for r in g])
            print(f"{Hn:>6} {q:>5} {100*np.mean([r['exposure_exo'] for r in g]):9.2f} {e[0]:7.2f}+-{e[1]:5.2f} {a[0]:7.2f}+-{a[1]:5.2f} {sum(r['exo_below_fixed'] for r in g):>6}/15")
        t = [r["qstar_end"] for r in rows if r["H"] == Hn and r["q"] == "threshold"]
        print(f"{Hn:>6} q*_end mean {np.mean(t):.3f}  range {min(t):.2f}-{max(t):.2f}")
    c = [r for r in rows if r["q"] == "closed_loop"]
    for k in ("exogenous", "aware"):
        d = [100 * (r[f"{k}_mean"] - r["fixed_mean"]) / r["fixed_mean"] for r in c]
        m, h = ci(d); print(f"closed loop H=15min q=0.25 {k}: {m:.2f}+-{h:.2f}% vs fixed, wins {sum(x > 0 for x in d)}/15, observed frac {np.mean([r[f'{k}_obs'] for r in c]):.3f}")
