"""
Exact zero-sum matrix-game solver via linear programming (scipy HiGHS).
A is (m x n): row player = defender = maximizer, column player = attacker = minimizer.
Returns the game value and both optimal mixed strategies.
"""
import numpy as np
from scipy.optimize import linprog


def solve_matrix_game(A):
    A = np.asarray(A, float)
    m, n = A.shape
    shift = A.min()                      # make entries >= 0 for numerical comfort (value shifts back)
    B = A - shift

    # Row player (maximizer): vars z = [x_1..x_m, v]; maximize v  <=>  minimize -v
    c = np.zeros(m + 1); c[-1] = -1.0
    # -sum_i B[i,j] x_i + v <= 0   for each column j
    A_ub = np.hstack([-B.T, np.ones((n, 1))])
    b_ub = np.zeros(n)
    A_eq = np.hstack([np.ones((1, m)), np.zeros((1, 1))])
    b_eq = np.array([1.0])
    bounds = [(0, 1)] * m + [(None, None)]
    r = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method='highs')
    x = r.x[:m]; value = r.x[-1] + shift

    # Column player (minimizer): vars z = [y_1..y_n, u]; minimize u
    c2 = np.zeros(n + 1); c2[-1] = 1.0
    # sum_j B[i,j] y_j - u <= 0   for each row i
    A_ub2 = np.hstack([B, -np.ones((m, 1))])
    b_ub2 = np.zeros(m)
    A_eq2 = np.hstack([np.ones((1, n)), np.zeros((1, 1))])
    b_eq2 = np.array([1.0])
    bounds2 = [(0, 1)] * n + [(None, None)]
    r2 = linprog(c2, A_ub=A_ub2, b_ub=b_ub2, A_eq=A_eq2, b_eq=b_eq2, bounds=bounds2, method='highs')
    y = r2.x[:n]

    return dict(value=float(value), x=x, y=y,
                pure_maximin=float(A.min(1).max()), pure_minimax=float(A.max(0).min()))


if __name__ == "__main__":
    from exact_solver import solve_exact
    D6 = [[0,10,8,4,14,11],[10,0,8,14,4,11],[8,8,0,11,11,18],
          [4,14,11,0,10,7],[14,4,11,10,0,7],[11,11,18,7,7,0]]
    v6 = [1,1,1,5,3,10]
    U = solve_exact(v=v6, m=2, n=10, c=4, p=0.7, r=9, D=D6)['U']
    res = solve_matrix_game(U)
    import itertools
    from vectorized_solver import compositions_array
    Sd = list(itertools.combinations(range(6), 2)); Sa = compositions_array(10, 6)
    print("EXACT terminal utilities, mixed-strategy equilibrium (LP):")
    print(f"  pure  maximin = {res['pure_maximin']:.4f}   pure minimax = {res['pure_minimax']:.4f}")
    print(f"  MIXED game value = {res['value']:.4f}")
    xs = res['x']; ys = res['y']
    print("  defender mixed support:")
    for i in np.where(xs > 1e-6)[0]:
        print(f"     P={xs[i]:.3f}  batteries at {tuple('ABCDEF'[k] for k in Sd[i])}")
    print("  attacker mixed support:")
    for j in np.where(ys > 1e-6)[0]:
        print(f"     P={ys[j]:.3f}  w = {list(Sa[j])}")
