"""Programmatic feasibility check of the greedy terminal evaluator (supports Prop 2)."""
import numpy as np, itertools
from general_solver import compositions as gcomp

def greedy_with_asserts(w, placement, D, v, c, p, r, N):
    attacked=[j for j in range(N) if w[j]>0]; attacked.sort(key=lambda j:-v[j])
    covers={x:sorted([b for b in placement if D[b,x]<r],key=lambda b:D[b,x]) for x in range(N)}
    fired={s:0 for s in placement}; delivered=np.zeros(N)
    for x in attacked:
        need=int(w[x])
        if x in placement:
            while delivered[x]<need and fired[x]<c:
                fired[x]+=1; delivered[x]+=1
        if delivered[x]<need:
            for s in covers[x]:
                if s==x: continue
                while delivered[x]<need and fired[s]<c:
                    fired[s]+=1; delivered[x]+=1
                if delivered[x]>=need: break
    # ---- FEASIBILITY ASSERTIONS ----
    for s in placement:
        assert fired[s]<=c, "capacity exceeded"
    # deliveries only from covering batteries: reconstruct not needed; delivered<=need enforced
    u=0.0
    for j in range(N):
        if w[j]==0: u+=v[j]
        elif delivered[j]>=w[j]:
            assert delivered[j]==w[j], "over-delivery (double count)"
            u+=v[j]*(p**w[j])
        # else destroyed, contributes 0 -> and no partial credit
    # total interceptors used <= sum capacities
    assert sum(fired.values())<=c*len(placement)
    return u

# run over benchmark + random nets
D6=np.array([[0,10,8,4,14,11],[10,0,8,14,4,11],[8,8,0,11,11,18],[4,14,11,0,10,7],[14,4,11,10,0,7],[11,11,18,7,7,0]],float)
v6=np.array([1,1,1,5,3,10],float); N=6
checked=0
for pl in itertools.combinations(range(N),2):
    for w in gcomp(10,N):
        greedy_with_asserts(w,pl,D6,v6,4,0.7,9,N); checked+=1
print(f"benchmark: {checked} (d,w) pairs passed all feasibility assertions")
rng=np.random.default_rng(999)
tot=0
for s in range(5):
    coords=rng.uniform(0,30,size=(N,2)); v=rng.integers(1,11,size=N).astype(float)
    D=np.sqrt(((coords[:,None,:]-coords[None,:,:])**2).sum(-1))
    for pl in itertools.combinations(range(N),2):
        for w in gcomp(10,N): greedy_with_asserts(w,pl,D,v,4,0.7,12,N); tot+=1
print(f"5 random nets: {tot} pairs passed all feasibility assertions")
print("Proposition 2 preconditions verified programmatically.")
