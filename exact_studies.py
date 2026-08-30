"""
Exact parameter studies on the six-city benchmark.
Uses the exact max-flow terminal solver + LP mixed-strategy game value.
Feasibility (which subsets of attacked cities can be fully intercepted) is
independent of p, so we precompute the feasible-subset structure once per c and
sweep p cheaply.
"""
import numpy as np, itertools, json
from exact_solver import feasible
from game_lp import solve_matrix_game
from vectorized_solver import compositions_array

D6 = np.array([[0,10,8,4,14,11],[10,0,8,14,4,11],[8,8,0,11,11,18],
               [4,14,11,0,10,7],[14,4,11,10,0,7],[11,11,18,7,7,0]], float)
V6 = np.array([1,1,1,5,3,10], float)
N = 6
Sd = list(itertools.combinations(range(N), 2))
Sa = compositions_array(10, N)


def feasible_structure(c, r=9):
    """For each (placement, w): list of feasible defendable city-subsets."""
    struct = []  # struct[i][k] = (base_cities_notattacked, [feasible subsets as tuples])
    for pl in Sd:
        covers_city = {j: [b for b in pl if D6[b, j] <= r] for j in range(N)}
        row = []
        for k in range(len(Sa)):
            w = [int(x) for x in Sa[k]]
            attacked = [j for j in range(N) if w[j] > 0]
            notatt = [j for j in range(N) if w[j] == 0]
            defendable = [j for j in attacked if len(covers_city[j]) * c >= w[j]]
            feas = []
            for kk in range(len(defendable) + 1):
                for S in itertools.combinations(defendable, kk):
                    if feasible(set(S), w, list(pl), covers_city, c):
                        feas.append(S)
            row.append((notatt, feas))
        struct.append(row)
    return struct


def value_matrix(struct, p):
    U = np.empty((len(Sd), len(Sa)))
    pw = p ** Sa.astype(float)           # p^{w_j}
    for i in range(len(Sd)):
        for k in range(len(Sa)):
            notatt, feas = struct[i][k]
            base = V6[notatt].sum()
            best = 0.0
            for S in feas:
                val = sum(V6[j] * pw[k, j] for j in S)
                if val > best:
                    best = val
            U[i, k] = base + best
    return U


def mixed_value(struct, p):
    return solve_matrix_game(value_matrix(struct, p))


if __name__ == "__main__":
    import sys
    what = sys.argv[1]
    out = {}
    if what == "psweep":
        st = feasible_structure(c=4)
        rows = []
        for p in np.round(np.arange(0.1, 1.001, 0.1), 2):
            res = mixed_value(st, p)
            # attacker concentration: modal equilibrium strike, max AMs at one city
            j = int(np.argmax(res['y'])); modal = list(Sa[j]); maxc = int(max(modal))
            rows.append(dict(p=float(p), value=round(res['value'], 4),
                             maximin=round(res['pure_maximin'], 4),
                             minimax=round(res['pure_minimax'], 4),
                             max_concentration=maxc))
            print(f"p={p:.1f}  mixed_value={res['value']:.3f}  (maximin {res['pure_maximin']:.3f}, "
                  f"minimax {res['pure_minimax']:.3f})  attacker max AMs/city={maxc}", flush=True)
        json.dump(rows, open("study_psweep.json", "w"), indent=2)
    elif what == "csweep":
        rows = []
        for c in range(2, 11):
            st = feasible_structure(c=c)
            res = mixed_value(st, 0.7)
            rows.append(dict(c=c, value=round(res['value'], 4)))
            print(f"c={c:2d}  mixed_value(p=0.7)={res['value']:.3f}", flush=True)
        json.dump(rows, open("study_csweep.json", "w"), indent=2)
    elif what == "cfamily":
        cval = int(sys.argv[2])
        st = feasible_structure(c=cval)
        rows = []
        for p in np.round(np.arange(0.1, 0.901, 0.1), 2):
            res = mixed_value(st, p)
            rows.append(dict(c=cval, p=float(p), value=round(res['value'], 4)))
            print(f"c={cval} p={p:.1f}  value={res['value']:.3f}", flush=True)
        path = "study_cfamily.json"
        allrows = json.load(open(path)) if __import__('os').path.exists(path) else []
        allrows = [x for x in allrows if x['c'] != cval] + rows
        json.dump(allrows, open(path, "w"), indent=2)
