"""
Closed-loop shift simulator for randomized robot staging on occupancy-grid maps.

Per shift:
  1. Draw staging placement d ~ x (policy). Docks are matched to the previous shift's docks
     (Hungarian, path length); robots relocate at nominal speed. Relocation time tau = slowest dock.
  2. Attack time t_a ~ U(0, shift). The attacker sees the realized staging if t_a < tau (robots
     visibly in transit) or, independently, with probability q (surveillance). An observing attacker
     plays argmin_a U[d, a]; otherwise the best response to the known policy, argmin_a sum_d x_d U[d, a].
  3. Defender plans the optimal terminal response on the nominal model (subset + flow), then each
     assigned robot drives its grid shortest path with a per-trip speed factor (lognormal) from its
     current position (dock, or mid-relocation upper bound via either path endpoint). A request is
     served if arrival + service time <= deadline and the task succeeds (prob p). A zone's value counts
     only if all its requests are served; unloaded zones keep their value.
Model-vs-sim gaps come from speed variation, mid-relocation positions, and the deadline.
"""
import heapq, itertools
import numpy as np
import networkx as nx
from scipy.optimize import linear_sum_assignment
from evaluator import build, terminal

SQ2 = np.sqrt(2.0)


# ---------------------------------------------------------------- maps
def make_map(kind, seed=0, W=120, H=80):
    rng = np.random.default_rng(seed)
    g = np.zeros((H, W), bool)  # True = obstacle
    g[0, :] = g[-1, :] = g[:, 0] = g[:, -1] = True
    if kind == "warehouse":
        for y in range(8, H - 8, 7):          # shelf rows, 2 m deep, with cross aisles
            for x0 in range(6, W - 6, 28):
                g[y:y + 2, x0:x0 + 22] = True
    elif kind == "office":
        for y in (26, 54):                     # two corridors split by room walls
            g[y, :] = True
        for x in range(20, W, 20):
            g[:, x] = True
        g[38:42, 1:-1] = False                  # central corridor
        for y in (26, 54):
            for x in range(10, W, 20):
                g[y, x - 1:x + 2] = False       # doors to rooms
        for x in range(20, W, 20):
            for y in (13, 40, 67):
                g[y - 1:y + 2, x] = False
    elif kind == "campus":
        for _ in range(14):                     # buildings
            w, h = rng.integers(8, 20), rng.integers(6, 14)
            x, y = rng.integers(3, W - w - 3), rng.integers(3, H - h - 3)
            g[y:y + h, x:x + w] = True
    # keep largest free component
    free = ~g
    lab = -np.ones_like(g, int); comp = 0; sizes = []
    for sy, sx in zip(*np.where(free)):
        if lab[sy, sx] >= 0:
            continue
        stack = [(sy, sx)]; lab[sy, sx] = comp; n = 0
        while stack:
            y, x = stack.pop(); n += 1
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                yy, xx = y + dy, x + dx
                if free[yy, xx] and lab[yy, xx] < 0:
                    lab[yy, xx] = comp; stack.append((yy, xx))
        sizes.append(n); comp += 1
    big = int(np.argmax(sizes))
    return lab != big  # obstacle mask (everything outside the main free component)


def dijkstra(obst, src):
    H, W = obst.shape
    dist = np.full((H, W), np.inf); dist[src] = 0.0
    pq = [(0.0, src)]
    nb = [(1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0), (1, 1, SQ2), (1, -1, SQ2), (-1, 1, SQ2), (-1, -1, SQ2)]
    while pq:
        d, (y, x) = heapq.heappop(pq)
        if d > dist[y, x]:
            continue
        for dy, dx, c in nb:
            yy, xx = y + dy, x + dx
            if obst[yy, xx]:
                continue
            if dy and dx and (obst[y + dy, x] or obst[y, x + dx]):
                continue  # no corner cutting
            nd = d + c
            if nd < dist[yy, xx]:
                dist[yy, xx] = nd; heapq.heappush(pq, (nd, (yy, xx)))
    return dist


def sample_points(obst, k, rng, min_sep=8.0, avoid=()):
    free = np.argwhere(~obst)
    pts = list(avoid); out = []
    while len(out) < k:
        y, x = free[rng.integers(len(free))]
        if all((y - a) ** 2 + (x - b) ** 2 >= min_sep ** 2 for a, b in pts):
            pts.append((y, x)); out.append((int(y), int(x)))
    return out


def scenario(kind, seed, K=12, N=12, speed=1.5, service=30.0, density=0.20, priority="skewed", c=2, min_sep=8.0):
    """Builds sites, zones, path distances, and a deadline giving the target reachability density."""
    rng = np.random.default_rng(seed)
    obst = make_map(kind, seed)
    sites = sample_points(obst, K, rng, min_sep=min_sep)
    zones = sample_points(obst, N, rng, min_sep=min_sep, avoid=sites)
    dmaps = [dijkstra(obst, s) for s in sites]
    Dsz = np.array([[dm[z] for z in zones] for dm in dmaps])          # site->zone path length (m)
    Dss = np.array([[dm[s] for s in sites] for dm in dmaps])          # site->site
    ttime = Dsz / speed + service
    deadline = float(np.quantile(ttime, density))
    A = (ttime <= deadline).astype(np.int64)
    dl_mat = np.full((K, N), deadline)          # per-arc deadline used by the simulator
    for j in range(N):
        if A[:, j].sum() == 0:                  # zone unreachable: allow its single nearest site only
            i = int(np.argmin(ttime[:, j]))
            A[i, j] = 1
            dl_mat[i, j] = float(ttime[i, j])
    if priority == "uniform":
        v = np.ones(N)
    else:  # "skewed" == "zipf:1"; "zipf:a" gives v = 10 / rank^a (a = 0 is uniform but consumes the same RNG draws)
        a = 1.0 if priority == "skewed" else float(priority.split(":")[1])
        v = 10.0 / np.arange(1, N + 1) ** a; rng.shuffle(v)
    return dict(kind=kind, obst=obst, sites=sites, zones=zones, Dsz=Dsz, Dss=Dss, A=A, v=v, c=c,
                p=0.7, speed=speed, service=service, deadline=deadline, dl_mat=dl_mat, seed=seed)


# ---------------------------------------------------------------- terminal plan with explicit routing
def plan(sc, placement, w):
    """Optimal served subset and dock->zone robot counts for (placement, w), nominal model."""
    A, v, c, p = sc["A"], sc["v"], sc["c"], sc["p"]
    loaded = [j for j in range(len(w)) if w[j] > 0]
    best, bestS = -1.0, ()
    for k in range(len(loaded) + 1):
        for S in itertools.combinations(loaded, k):
            val = sum(v[j] * p ** w[j] for j in S)
            if val <= best:
                continue
            G = nx.DiGraph()
            for i in placement:
                G.add_edge("s", ("d", i), capacity=c)
                for j in S:
                    if A[i, j]:
                        G.add_edge(("d", i), ("z", j), capacity=c)
            for j in S:
                G.add_edge(("z", j), "t", capacity=int(w[j]))
            need = sum(w[j] for j in S)
            if need == 0 or ("s" in G and "t" in G and nx.maximum_flow_value(G, "s", "t") == need):
                best, bestS = val, S
    route = []
    if bestS:
        G = nx.DiGraph()
        for i in placement:
            G.add_edge("s", ("d", i), capacity=c)
            for j in bestS:
                if A[i, j]:
                    G.add_edge(("d", i), ("z", j), capacity=c)
        for j in bestS:
            G.add_edge(("z", j), "t", capacity=int(w[j]))
        _, F = nx.maximum_flow(G, "s", "t")
        for i in placement:
            for (kind, j), f in F.get(("d", i), {}).items():
                route += [(i, j)] * int(round(f))
    return bestS, route


# ---------------------------------------------------------------- shift loop
class Sim:
    def __init__(self, sc, m, n=6):
        self.sc, self.m, self.n = sc, m, n
        self.P, self.W, self.U = build(dict(A=sc["A"], v=sc["v"], c=sc["c"], p=sc["p"]), m, n)
        self.mvec = self.U.min(1)
        self.obs_attack = np.argmin(self.U, axis=1)
        self._plan_cache = {}

    def get_plan(self, di, ai):
        key = (di, ai)
        if key not in self._plan_cache:
            self._plan_cache[key] = plan(self.sc, tuple(int(i) for i in self.P[di]), self.W[ai])
        return self._plan_cache[key]

    def run(self, x, q, shifts, seed, shift_len=8 * 3600.0, speed_sd=0.15):
        """Common random numbers: every policy evaluated with the same `seed` sees the same per-shift
        uniforms (placement draw, attack time, surveillance) and the same per-robot-slot speed/success
        draws, so policy comparisons are paired."""
        sc = self.sc
        x = np.asarray(x, float); x = x / x.sum()
        cdf = np.cumsum(x)
        R = int(self.m * sc["c"])
        g = np.random.default_rng(seed)
        U_place, U_time, U_obs = g.random(shifts), g.random(shifts), g.random(shifts)
        SPD = g.lognormal(0.0, speed_sd, (shifts, R)); SUC = g.random((shifts, R))
        blind_attack = int(np.argmin(self.U.T @ x))
        prev = None
        vals, relocs, taus, observed = [], [], [], 0
        for sh in range(shifts):
            di = int(min(np.searchsorted(cdf, U_place[sh] * cdf[-1], side='right'), len(x) - 1))
            pl = [int(i) for i in self.P[di]]
            # relocation: match previous docks to new docks
            origin = {i: (i, i, 0.0) for i in pl}
            tau = 0.0; dist_total = 0.0
            if prev is not None and prev != pl:
                C = np.array([[sc["Dss"][a, b] for b in pl] for a in prev])
                ri, ci = linear_sum_assignment(C)
                for a_, b_ in zip(ri, ci):
                    a, b = prev[a_], pl[b_]
                    origin[b] = (a, b, sc["Dss"][a, b])
                    dist_total += sc["c"] * sc["Dss"][a, b]
                    tau = max(tau, sc["Dss"][a, b] / sc["speed"])
            prev = pl
            t_a = U_time[sh] * shift_len
            in_transit = t_a < tau
            sees = in_transit or (U_obs[sh] < q)
            observed += sees
            ai = int(self.obs_attack[di]) if sees else blind_attack
            w = self.W[ai]
            S, route = self.get_plan(di, ai)
            ok = {j: 0 for j in S}
            for slot, (i, j) in enumerate(route):
                a, b, dab = origin[i]
                if in_transit and dab > 0:
                    frac = min(1.0, t_a * sc["speed"] / dab)  # fraction of relocation completed
                    d = min(frac * dab + sc["Dsz"][a, j], (1 - frac) * dab + sc["Dsz"][b, j])
                else:
                    d = sc["Dsz"][i, j]
                t = d / (sc["speed"] * SPD[sh, slot]) + sc["service"]
                if t <= sc["dl_mat"][i, j] and SUC[sh, slot] < sc["p"]:
                    ok[j] += 1
            val = sum(sc["v"][j] for j in range(len(w)) if w[j] == 0)
            val += sum(sc["v"][j] for j in S if ok[j] == w[j])
            vals.append(val); relocs.append(dist_total); taus.append(tau)
        vals = np.array(vals)
        return dict(mean=float(vals.mean()), se=float(vals.std(ddof=1) / np.sqrt(len(vals))),
                    reloc_m=float(np.mean(relocs)), tau_s=float(np.mean(taus)),
                    observed_frac=observed / shifts)
