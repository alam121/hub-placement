"""Matrix-free exact solver for the leakage-aware staging game (large attack spaces).

Game with payoff U'(d,w) = (1-q) U(d,w) + q mu_d  (mu_d = min_w U(d,w)); V*(q) is its value.
 * Attacker best response: exact depth-first branch-and-bound over demand compositions (zones in
   value-descending order). Admissible bound at a node with fixed zones F and `rem` alarms left:
     sum_d x_d [ sum_{j in F, w_j=0} v_j  +  best jointly feasible subset of loaded fixed zones under d ]
     + (sum of unfixed values) - (top-`rem` unfixed values)          [joint-recourse bound, k = all]
   Loaded unfixed zones contribute >= 0 and cannot invalidate a feasible service of fixed zones.
 * Defender side: all placements are rows; U is evaluated for every placement on every generated attack.
   For q>0 the rows need mu_d; we keep upper bounds mu_bar_d (min over generated attacks) and compute
   exact mu_d lazily (pure-placement B&B) whenever a row could be the defender's best response.
 * Termination: attacker BR value and LP value agree to tolerance and every row in the LP uses exact mu
   for rows with positive weight or best-response potential -> exact value up to LP tolerance.
"""
import numpy as np
from numba import njit
from scipy.optimize import linprog
from evaluator import terminal

TOL = 1e-7


@njit(cache=True)
def _popc(x):
    c = 0
    while x:
        x &= x - 1
        c += 1
    return c


@njit(cache=True)
def _fixed_best(dmask, lz, lw, L, covmask, v, c, p):
    """Best jointly feasible subset value among the L loaded fixed zones (Gale condition)."""
    if L == 0:
        return 0.0
    nsub = 1 << L
    ok = np.ones(nsub, np.bool_)
    val = np.zeros(nsub)
    for T in range(1, nsub):
        need = 0; nb = 0; vv = 0.0
        for t in range(L):
            if (T >> t) & 1:
                need += lw[t]; nb |= covmask[lz[t]] & dmask; vv += v[lz[t]] * p ** lw[t]
        val[T] = vv
        ok[T] = need <= c * _popc(nb)
    for t in range(L):
        bit = 1 << t
        for S in range(nsub):
            if (S & bit) and not ok[S ^ bit]:
                ok[S] = False
    best = 0.0
    for S in range(nsub):
        if ok[S] and val[S] > best:
            best = val[S]
    return best


@njit(cache=True)
def attacker_br(dms, xw, covmask, v, c, p, n, order, incumbent):
    """Exact min_w sum_s xw[s] U(dms[s], w). Zones visited in `order` (value-descending).
    Returns (value, w, nodes). `incumbent` is a known achievable value (warm start)."""
    N = v.shape[0]
    S = dms.shape[0]
    vo = v[order]
    suffix = np.zeros(N + 1)
    for t in range(N - 1, -1, -1):
        suffix[t] = suffix[t + 1] + vo[t]
    best = incumbent
    bestw = -np.ones(N, np.int64)
    w = np.zeros(N, np.int64)
    lz = np.zeros(n + 1, np.int64); lw = np.zeros(n + 1, np.int64)
    # explicit DFS stack: at depth t we try a = amax..0
    nexta = np.zeros(N + 1, np.int64)
    rems = np.zeros(N + 1, np.int64)
    zb = np.zeros(N + 1)
    Ls = np.zeros(N + 1, np.int64)
    nodes = 0
    t = 0
    rems[0] = n; zb[0] = 0.0; Ls[0] = 0
    nexta[0] = n
    while t >= 0:
        if nexta[t] < 0:
            t -= 1
            continue
        a = nexta[t]
        nexta[t] -= 1
        rem = rems[t]
        if t == N - 1 and a != rem:
            continue  # last zone must take all remaining alarms
        if a > rem:
            continue
        j = order[t]
        w[j] = a
        L = Ls[t]
        nzb = zb[t]
        if a == 0:
            nzb += v[j]
        else:
            lz[L] = j; lw[L] = a; L += 1
        nrem = rem - a
        nodes += 1
        # bound
        fb = 0.0
        for s in range(S):
            fb += xw[s] * _fixed_best(dms[s], lz, lw, L, covmask, v, c, p)
        k = t + 1 + nrem
        tail = suffix[k] if k <= N else 0.0
        lb = nzb + fb + tail
        if lb >= best - 1e-12:
            continue
        if nrem == 0:  # leaf: all remaining zones unloaded -> bound is exact
            best = lb
            for i in range(N):
                bestw[i] = 0
            for i in range(t + 1):
                bestw[order[i]] = w[order[i]]
            continue
        if t + 1 >= N:
            continue
        # descend
        t += 1
        rems[t] = nrem; zb[t] = nzb; Ls[t] = L; nexta[t] = nrem
        for i in range(t, N):
            w[order[i]] = 0
    return best, bestw, nodes


@njit(cache=True)
def column(dmasks, w, covmask, v, c, p):
    out = np.empty(dmasks.shape[0])
    for i in range(dmasks.shape[0]):
        out[i] = terminal(dmasks[i], w, covmask, v, c, p)
    return out


def _lp(Um, rows_val_shift=None):
    """Row player maximizes; returns value, x (rows), y (cols)."""
    m, k = Um.shape
    B = Um - Um.min()
    c = np.zeros(m + 1); c[-1] = -1.0
    A_ub = np.hstack([-B.T, np.ones((k, 1))])
    r = linprog(c, A_ub=A_ub, b_ub=np.zeros(k), A_eq=np.r_[np.ones(m), 0.0][None, :], b_eq=[1.0],
                bounds=[(0, None)] * m + [(None, None)], method="highs")
    x = np.clip(r.x[:m], 0, None); x /= x.sum()
    r2 = linprog(np.r_[np.zeros(k), 1.0], A_ub=np.hstack([B, -np.ones((m, 1))]), b_ub=np.zeros(m),
                 A_eq=np.r_[np.ones(k), 0.0][None, :], b_eq=[1.0], bounds=[(0, None)] * k + [(None, None)], method="highs")
    y = np.clip(r2.x[:k], 0, None); y /= y.sum()
    return r.x[-1] + Um.min(), x, y


class Solver:
    def __init__(self, A, v, c, p, m, n, placements):
        self.A, self.v, self.c, self.p, self.m, self.n = A, np.asarray(v, float), int(c), float(p), m, n
        self.P = placements
        K, N = A.shape
        self.dmasks = np.array([sum(1 << int(i) for i in pl) for pl in placements], np.int64)
        self.covmask = np.array([sum(1 << i for i in range(K) if A[i, j]) for j in range(N)], np.int64)
        self.order = np.argsort(-self.v, kind="stable").astype(np.int64)
        self.W = []          # generated attacks
        self.cols = []       # U over all placements for each generated attack
        self.mu = np.full(len(placements), np.nan)  # exact pure worst cases (lazy)
        self.nodes = 0; self.br_calls = 0

    def add_attack(self, w):
        key = tuple(int(a) for a in w)
        if key in {tuple(x) for x in self.W}:
            return False
        self.W.append(np.array(key, np.int64))
        self.cols.append(column(self.dmasks, self.W[-1], self.covmask, self.v, self.c, self.p))
        return True

    def Umat(self):
        return np.array(self.cols).T

    def br(self, idx, xw, incumbent):
        val, w, nodes = attacker_br(self.dmasks[idx], xw, self.covmask, self.v, self.c, self.p, self.n,
                                    self.order, incumbent)
        self.nodes += nodes; self.br_calls += 1
        return val, w

    def exact_mu(self, d):
        if np.isnan(self.mu[d]):
            U = self.Umat()
            inc = U[d].min() + 1e-9
            val, w = self.br(np.array([d]), np.array([1.0]), inc)
            if w[0] >= 0:
                self.add_attack(w)
                val = min(val, self.cols[-1][d])
            self.mu[d] = min(val, U[d].min())
        return self.mu[d]

    def init(self):
        # seed: greedy concentrated attacks on the top-value zones
        for k in range(1, self.n + 1):
            w = np.zeros(len(self.v), np.int64)
            top = self.order[:k]
            for i in range(self.n):
                w[top[i % k]] += 1
            self.add_attack(w)

    def pure_maximin(self):
        """P = max_d mu_d with lazy exact mu (upper bounds from generated attacks)."""
        while True:
            U = self.Umat()
            ub = np.where(np.isnan(self.mu), U.min(1), self.mu)
            d = int(np.argmax(ub))
            if not np.isnan(self.mu[d]):
                return float(self.mu[d]), d
            self.exact_mu(d)

    def solve(self, q, max_iter=500):
        P, _ = self.pure_maximin()
        for it in range(max_iter):
            U = self.Umat()
            mu_ub = np.where(np.isnan(self.mu), U.min(1), self.mu)
            Up = (1 - q) * U + q * mu_ub[:, None]
            val, x, y = _lp(Up)
            # rows with weight but inexact mu -> make exact, restart iteration
            need = [d for d in np.where(x > 1e-9)[0] if np.isnan(self.mu[d])] if q > 0 else []
            if need:
                for d in need:
                    self.exact_mu(d)
                continue
            supp = np.where(x > 1e-12)[0]
            inc = float((U[supp].T @ x[supp]).min()) + 1e-9
            bval, bw = self.br(supp, x[supp], inc)
            lb = (1 - q) * min(bval, inc - 1e-9) + q * float(x[supp] @ self.mu[supp] if q > 0 else 0.0)
            added = False
            if bw[0] >= 0 and bval < inc - 1e-9 - TOL * max(1, abs(val)):
                added = self.add_attack(bw)
            if not added:
                # attacker cannot improve: LP value is exact given rows' payoffs; verify defender side for q>0
                if q > 0:
                    pad = lambda yy, k: np.r_[yy, np.zeros(k - len(yy))]
                    U = self.Umat()
                    sc = (1 - q) * (U @ pad(y, U.shape[1]))
                    while True:
                        mu_ub = np.where(np.isnan(self.mu), U.min(1), self.mu)
                        d = int(np.argmax(sc + q * mu_ub))
                        if np.isnan(self.mu[d]):
                            self.exact_mu(d); U = self.Umat(); sc = (1 - q) * (U @ pad(y, U.shape[1])); continue
                        break
                    if sc[d] + q * self.mu[d] > val + TOL * max(1, abs(val)):
                        continue  # a better row exists with exact mu; LP will pick it next iteration
                return dict(value=float(val), P=P, x=x, iters=it + 1, attacks=len(self.W),
                            support=int((x > 1e-9).sum()), nodes=self.nodes, br_calls=self.br_calls)
        raise RuntimeError("no convergence")
