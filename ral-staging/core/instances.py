"""Pre-registered instance generator (see PREREGISTRATION.md). Do not tune after seeing results."""
import numpy as np

DENSITY = {"sparse": 0.20, "medium": 0.35, "dense": 0.60}


def make_instance(seed, density, priority, c, K=12, N=12, p=0.7):
    rng = np.random.default_rng(seed)
    sites = rng.uniform(0, 100, (K, 2))
    zones = rng.uniform(0, 100, (N, 2))
    D = np.sqrt(((sites[:, None, :] - zones[None, :, :]) ** 2).sum(-1))
    r = np.quantile(D, DENSITY[density])
    A = (D <= r).astype(np.int64)
    for j in range(N):  # every zone reachable from at least one site
        if A[:, j].sum() == 0:
            A[np.argmin(D[:, j]), j] = 1
    if priority == "uniform":
        v = np.ones(N)
    else:  # skewed: Zipf-like 10/rank, randomly assigned to zones
        v = 10.0 / np.arange(1, N + 1)
        rng.shuffle(v)
    return dict(A=A, v=v, c=c, p=p, sites=sites, zones=zones, D=D, r=r, seed=seed,
                density=density, priority=priority)
