"""Leakage-aware staging LPs on an exact payoff matrix U (placements x attacks), defender maximizes.

V_x(q) = (1-q) min_a sum_d x_d U[d,a] + q sum_d x_d m_d,   m_d = min_a U[d,a]
V*(q)  = max_x V_x(q)             (LP, solved by constraint generation over attacks)
q*     = sup{q : V*(q) > P}       (one linear-fractional program, Charnes-Cooper transform)
"""
import numpy as np
from scipy.optimize import linprog

TOL = 1e-9


def _cg(U, obj_x, obj_z, extra_eq=None, s_col=False, s_cap=1e8):
    """Generic constraint generation for: max obj_x.x + obj_z z [+ s terms]
    s.t. z <= U[:,a].x for all a, plus extra equalities. Variables: x (D), z, [s]."""
    D, A = U.shape
    active = set(np.argmin(U, axis=1).tolist())
    active.update(np.argsort(U.max(0))[:20].tolist())
    while True:
        act = np.array(sorted(active))
        nv = D + 1 + (1 if s_col else 0)
        c = np.zeros(nv)
        c[:D] = -obj_x
        c[D] = -obj_z[0]
        if s_col:
            c[D + 1] = -obj_z[1]
        Aub = np.zeros((len(act), nv))
        Aub[:, :D] = -U[:, act].T
        Aub[:, D] = 1.0
        Aeq, beq = extra_eq
        bounds = [(0, None)] * D + [(None, None)] + ([(0, s_cap)] if s_col else [])
        r = linprog(c, A_ub=Aub, b_ub=np.zeros(len(act)), A_eq=Aeq, b_eq=beq,
                    bounds=bounds, method="highs")
        if r.status != 0:
            raise RuntimeError(r.message)
        x, z = r.x[:D], r.x[D]
        g = U.T @ x
        viol = np.where(g < z - 1e-9 * max(1.0, abs(z)))[0]
        viol = [a for a in viol if a not in active]
        if not viol:
            return r.x, -r.fun
        order = np.argsort(g[viol])[:300]
        active.update(np.array(viol)[order].tolist())


def solve_q(U, q, mvec=None):
    D = U.shape[0]
    mvec = U.min(1) if mvec is None else mvec
    Aeq = np.r_[np.ones(D), 0.0][None, :]
    sol, val = _cg(U, q * mvec, [1 - q], extra_eq=(Aeq, np.array([1.0])))
    x = np.clip(sol[:D], 0, None); x /= x.sum()
    z = float((U.T @ x).min())
    return dict(value=(1 - q) * z + q * float(x @ mvec), x=x, z=z, b=float(x @ mvec))


def q_star(U, P, mvec=None):
    """Returns (q*, tie_case). tie_case: mixing among tied best placements beats P -> q* = 1."""
    D = U.shape[0]
    mvec = U.min(1) if mvec is None else mvec
    tied = np.where(mvec >= P - 1e-9)[0]
    if len(tied) > 1:
        sub = solve_q(U[tied], 0.0)
        if sub["z"] > P + 1e-7 * max(1, P):
            return 1.0, True, len(tied)
    # Charnes-Cooper: y = s x, zeta = s z; max zeta - P s ; P s - mvec.y = 1 ; sum y = s
    Aeq = np.zeros((2, D + 2))
    Aeq[0, :D] = -mvec; Aeq[0, D + 1] = P          # P s - m.y = 1
    Aeq[1, :D] = 1.0;   Aeq[1, D + 1] = -1.0       # sum y - s = 0
    sol, val = _cg(U, np.zeros(D), [1.0, -P], extra_eq=(Aeq, np.array([1.0, 0.0])), s_col=True)
    t = max(val, 0.0)
    return t / (1 + t), False, len(tied)
