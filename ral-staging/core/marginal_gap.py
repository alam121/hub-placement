"""How much do per-site marginals leave undetermined?  For each grid instance with a concealment gain:
  * x*  : optimal concealed policy, value V0 = z(x*), marginals mu_i = P(site i open)
  * Certified spread: min over policies x' with the same marginals of z(x') is <= min over a candidate attack set W'
    of [min_{x'} sum_d x'_d U(d,w)] (one small LP per w). So  V0 - that number  is a certified LOWER bound on the
    worst-case loss of implementing the optimal marginals with an unlucky joint distribution.
  * Comb (systematic) sampling: the standard way to realise given marginals with exactly m open sites.
    Its exact value z(x_comb) is computed on the full payoff matrix.
Reports the loss relative to V0 and whether the same-marginal policy even beats the best fixed placement P."""
import json, itertools
import numpy as np
from scipy.optimize import linprog
from multiprocessing import Pool
from evaluator import build
from instances import make_instance
from leakage import solve_q


def comb_distribution(mu, m, placements):
    """Systematic sampling: u ~ U[0,1); site i chosen iff an integer+u falls in its cumulative interval."""
    cum = np.concatenate([[0.0], np.cumsum(mu)])
    bps = sorted(set([0.0] + [float(c - np.floor(c)) for c in cum[1:-1]] + [1.0]))
    index = {tuple(p): k for k, p in enumerate(placements)}
    x = np.zeros(len(placements))
    for a, b in zip(bps[:-1], bps[1:]):
        if b - a < 1e-12:
            continue
        u = (a + b) / 2
        chosen = tuple(i for i in range(len(mu)) if np.floor(cum[i + 1] - u) - np.floor(cum[i] - u) >= 1)
        if len(chosen) != m or chosen not in index:
            return None
        x[index[chosen]] += b - a
    return x


def job(r):
    inst = make_instance(r["seed"], r["density"], r["priority"], r["c"])
    Pl, W, U = build(inst, r["m"], 6)
    P = float(U.min(1).max())
    s = solve_q(U, 0.0)
    x, V0 = s["x"], s["z"]
    K = inst["A"].shape[0]
    M = np.zeros((K, len(Pl)))
    for k, pl in enumerate(Pl):
        M[pl, k] = 1.0
    mu = M @ x
    # candidate attacks: attacker equilibrium support proxy (lowest columns vs x) + each placement's worst attack
    g = U.T @ x
    cand = set(np.argsort(g)[:60].tolist()) | set(np.argmin(U, axis=1).tolist())
    worst = np.inf
    Aeq = np.vstack([M, np.ones((1, len(Pl)))]); beq = np.r_[mu, 1.0]
    for a in cand:
        res = linprog(U[:, a], A_eq=Aeq, b_eq=beq, bounds=[(0, None)] * len(Pl), method="highs")
        if res.status == 0:
            worst = min(worst, res.fun)
    xc = comb_distribution(np.clip(mu, 0, 1), r["m"], [list(p) for p in Pl])
    zc = float((U.T @ xc).min()) if xc is not None else np.nan
    return dict(m=r["m"], c=r["c"], density=r["density"], priority=r["priority"], s=r["s"], P=P, V0=V0,
                same_marginal_worst_ub=float(worst), comb=zc,
                spread_pct=100 * (V0 - worst) / V0, comb_loss_pct=100 * (V0 - zc) / V0,
                comb_vs_fixed_pct=100 * (zc - P) / P, gain_pct=100 * (V0 - P) / P,
                worst_below_fixed=bool(worst < P - 1e-9))


if __name__ == "__main__":
    R = [json.loads(l) for l in open("results.jsonl")]
    R = [r for r in R if (r["V0"] - r["P"]) > 1e-6 * r["P"]]
    with Pool(2) as pool:
        out = pool.map(job, R, chunksize=4)
    json.dump(out, open("marginal_gap.json", "w"), indent=1)
    sp = np.array([o["spread_pct"] for o in out]); cl = np.array([o["comb_loss_pct"] for o in out])
    cf = np.array([o["comb_vs_fixed_pct"] for o in out])
    print("instances with gain:", len(out))
    print("same-marginal certified spread > 0.1%:", int((sp > 0.1).sum()), " median spread %.2f%%  mean %.2f%%  max %.2f%%" % (np.median(sp), sp.mean(), sp.max()))
    print("same-marginal worst case below best FIXED placement:", int(sum(o["worst_below_fixed"] for o in out)))
    print("comb sampling: loss vs optimal median %.2f%% mean %.2f%%; strictly worse than optimal in %d; worse than best fixed in %d"
          % (np.nanmedian(cl), np.nanmean(cl), int((cl > 0.01).sum()), int((cf < -0.01).sum())))
    print("comb sampling keeps on average %.0f%% of the concealment gain" % (100 * np.nanmean((np.array([o['comb'] for o in out]) - np.array([o['P'] for o in out])) / (np.array([o['V0'] for o in out]) - np.array([o['P'] for o in out])))))
