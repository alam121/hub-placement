"""Multi-instance computational study of the matrix-free best-response double oracle.
Reports mean/std of time, iterations, support, and evaluation fraction, and verifies
exactness against full enumeration where affordable."""
import numpy as np, time, json, itertools
from math import comb
import br_oracle2 as B
from exact_solver import solve_exact
from game_lp import solve_matrix_game

m,n,c,p,r = 2,10,4,0.7,12.0
# (N, #instances, verify_full_enum?)
plan = [(6,10,True),(8,8,True),(10,8,False),(12,3,False)]
allrows=[]
for N,cnt,verify in plan:
    rows=[]
    for s in range(cnt):
        rng=np.random.default_rng(70000+100*N+s)
        coords=rng.uniform(0,30,size=(N,2)); v=rng.integers(1,11,size=N).astype(float)
        D=np.sqrt(((coords[:,None,:]-coords[None,:,:])**2).sum(-1))
        t0=time.time(); res=B.double_oracle_oracle(v,D,N,m=m,n=n,c=c,p=p,r=r,verbose=False); dt=time.time()-t0
        ok=None
        if verify:
            U=solve_exact(coords=coords.tolist(),v=v,m=m,n=n,c=c,p=p,r=r)['U']
            exval=solve_matrix_game(U)['value']; ok=abs(exval-res['value'])<1e-4
        fm=comb(N,m)*comb(N+n-1,n)
        row=dict(N=N,seed=70000+100*N+s,value=round(res['value'],4),iters=res['iters'],
                 supp_def=res['support_def'],supp_att=res['support_att'],
                 att_evals=res['att_evals'],time=round(dt,2),frac=round((res['att_evals']+res['def_evals'])/fm,4),
                 exact_match=ok)
        rows.append(row); allrows.append(row)
        print(f"N={N} s{s}: val={row['value']:.4f} t={row['time']:.1f}s it={row['iters']} "
              f"supp={row['supp_def']}x{row['supp_att']} frac={100*row['frac']:.2f}% match={ok}",flush=True)
    T=np.array([x['time'] for x in rows]); I=np.array([x['iters'] for x in rows])
    SD=np.array([x['supp_def'] for x in rows]); SA=np.array([x['supp_att'] for x in rows])
    FR=np.array([x['frac'] for x in rows])
    print(f"  == N={N} (n={cnt}): time {T.mean():.1f}+/-{T.std():.1f}s  iters {I.mean():.1f}+/-{I.std():.1f}  "
          f"support {SD.mean():.1f}x{SA.mean():.1f}  matrix-touched {100*FR.mean():.2f}%  "
          f"all_exact={all(x['exact_match'] for x in rows) if verify else 'n/a'}",flush=True)
json.dump(allrows,open("study_results.json","w"),indent=2)
print("saved study_results.json")
