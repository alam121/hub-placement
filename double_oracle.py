"""
Double-oracle solver for the single-stage zero-sum IADS game, as a stronger
baseline than full enumeration. It maintains small restricted strategy sets,
solves the restricted game by LP, and grows the sets by exact best responses
until neither player can improve — at which point the restricted equilibrium is
a Nash equilibrium of the full game. Utilities come from the exact max-flow
terminal solver. We track iterations, final support, and the number of distinct
strategy-pair utilities evaluated (the oracle's true work) vs full enumeration.
"""
import numpy as np, itertools
from exact_solver import solve_exact
from game_lp import solve_matrix_game
from vectorized_solver import compositions_array


def double_oracle(U, verbose=True):
    m, n = U.shape
    evaluated = set()
    def Q(i, k):                     # lazy, counted access to a utility
        evaluated.add((i, k)); return U[i, k]

    R = [0]                          # restricted defender rows (start arbitrary)
    C = [0]                          # restricted attacker cols
    iters = 0
    while True:
        iters += 1
        sub = np.array([[Q(i, k) for k in C] for i in R])
        g = solve_matrix_game(sub)
        x = np.zeros(m); x[R] = g['x']
        y = np.zeros(n); y[C] = g['y']
        val = g['value']

        # attacker best response: minimize expected utility over ALL columns
        exp_col = np.array([sum(x[i] * Q(i, k) for i in R) for k in range(n)])
        k_star = int(np.argmin(exp_col)); att_val = exp_col[k_star]
        # defender best response: maximize expected utility over ALL rows
        exp_row = np.array([sum(y[k] * Q(i, k) for k in C) for i in range(m)])
        i_star = int(np.argmax(exp_row)); def_val = exp_row[i_star]

        added = False
        if att_val < val - 1e-7 and k_star not in C:
            C.append(k_star); added = True
        if def_val > val + 1e-7 and i_star not in R:
            R.append(i_star); added = True
        if verbose:
            print(f"  iter {iters:2d}: value={val:.4f}  |R|={len(R)} |C|={len(C)}  "
                  f"att_BR={att_val:.4f} def_BR={def_val:.4f}")
        if not added:
            break
    return dict(value=val, iters=iters, nR=len(R), nC=len(C),
                support_def=int((g['x'] > 1e-6).sum()), support_att=int((g['y'] > 1e-6).sum()),
                evaluated=len(evaluated), full=m * n)


if __name__ == "__main__":
    D6 = [[0,10,8,4,14,11],[10,0,8,14,4,11],[8,8,0,11,11,18],
          [4,14,11,0,10,7],[14,4,11,10,0,7],[11,11,18,7,7,0]]
    U = solve_exact(v=[1,1,1,5,3,10], m=2, n=10, c=4, p=0.7, r=9, D=D6)['U']
    full = solve_matrix_game(U)['value']
    print(f"Full-enumeration LP value: {full:.4f}  (matrix {U.shape[0]}x{U.shape[1]} = {U.size} pairs)")
    print("Double-oracle:")
    r = double_oracle(U)
    print(f"\nDouble-oracle value = {r['value']:.4f}  (exact = {full:.4f}, gap = {abs(r['value']-full):.2e})")
    print(f"iterations = {r['iters']},  final restricted game {r['nR']}x{r['nC']},  "
          f"equilibrium support {r['support_def']} def x {r['support_att']} att")
    print(f"distinct utility evaluations = {r['evaluated']} of {r['full']} "
          f"({100*r['evaluated']/r['full']:.1f}% of full matrix)")
