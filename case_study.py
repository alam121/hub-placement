"""
Robotics case study: resilient inspection-hub placement on an industrial campus
under adversarial disruption. Reachability is the time budget travel/speed +
task_time <= T; a subsystem is restored only if ALL its required actions succeed
(value v_j p^{w_j}). We compare robust / greedy / coverage-max / random placement
and the concealed (relocatable) equilibrium, and report which zones are restored
under the worst-case workload.
"""
import numpy as np, itertools, json
from exact_solver import exact_terminal, feasible
from vectorized_solver import compositions_array
from game_lp import solve_matrix_game
from general_solver import eval_pair

# Industrial campus: name -> (x m, y m, priority v, task time s)
zones = {
    'Control room'      : (12,46,3,12),
    'Comms room'        : (32,49,3,12),
    'Inspection tower'  : (54,49,4,12),
    'Loading bay'       : (78,46,3,12),
    'Storage area'      : (95,44,2,12),
    'Transformer area'  : (50, 8,12,14),
    'Pump station'      : (24,10,2,12),
    'Pipeline junction' : (76,10,2,12),
}
names=list(zones); N=len(names)
Zc=np.array([[z[0],z[1]] for z in zones.values()],float)
v =np.array([z[2] for z in zones.values()],float)
tt=np.array([z[3] for z in zones.values()],float)
hubs=np.array([(20,43),(46,45),(72,44),(45,13),(55,13),(88,20)],float); H=len(hubs)
speed,T,m,n,c,p = 2.5, 20.0, 2, 7, 4, 0.85

def reach(speed,T):
    D=np.array([[np.hypot(*(hubs[i]-Zc[j]))/speed+tt[j] for j in range(N)] for i in range(H)])
    return D, D<=T

def util_matrix(D,R,c,p,exact=True):
    Dbig=np.where(R,D,1e9); Sd=list(itertools.combinations(range(H),m)); Sa=compositions_array(n,N)
    if exact:
        U=np.array([[exact_terminal(Sa[k],pl,Dbig,v,c,p,T,N) for k in range(len(Sa))] for pl in Sd])
    else:
        order=sorted(range(N),key=lambda j:-v[j]); U=np.empty((len(Sd),len(Sa)))
        for i,pl in enumerate(Sd):
            hs=set(pl); cov={x:sorted([s for s in pl if R[s,x]],key=lambda s:D[s,x]) for x in range(N)}
            for k in range(len(Sa)): U[i,k]=eval_pair(Sa[k],pl,Dbig,v,c,p,T,N,hs,cov,order)
    return Sd,Sa,U,Dbig

def restored_set(pl,w,Dbig,c):
    covers={j:[b for b in pl if Dbig[b,j]<1e8] for j in range(N)}
    attacked=[j for j in range(N) if w[j]>0]; base=[j for j in range(N) if w[j]==0]
    defend=[j for j in attacked if len(covers[j])*c>=w[j]]; best=(-1,())
    for k in range(len(defend)+1):
        for S in itertools.combinations(defend,k):
            val=sum(v[j]*p**int(w[j]) for j in S)
            if val>best[0] and feasible(set(S),[int(x) for x in w],list(pl),covers,c): best=(val,S)
    return sorted(set(base)|set(best[1]))

D,R=reach(speed,T)
Sd,Sa,U,Dbig=util_matrix(D,R,c,p,exact=True)
worst=U.min(1); ri=int(np.argmax(worst)); game=solve_matrix_game(U)
def wcov(pl):
    cov=np.zeros(N,bool)
    for s in pl: cov|=R[s]
    return (v*cov).sum()
fi=int(np.argmax([wcov(pl) for pl in Sd]))
# greedy placement
_,_,Ug,_=util_matrix(D,R,c,p,exact=False); gi=int(np.argmax(Ug.min(1)))
wc=int(np.argmin(U[ri])); wdem=[int(x) for x in Sa[wc]]
restored=restored_set(Sd[ri],Sa[wc],Dbig,c)

res=dict(scenario=dict(N=N,H=H,m=m,n=n,c=c,p=p,T=T,speed=speed),
    zones={k:list(map(float,zones[k])) for k in zones}, hubs=hubs.tolist(),
    reachability=R.astype(int).tolist(),
    random_mean=round(float(worst.mean()),2),
    coverage_max=dict(hubs=[int(s) for s in Sd[fi]], worst=round(float(worst[fi]),2)),
    greedy=dict(hubs=[int(s) for s in Sd[gi]], worst=round(float(Ug.min(1)[gi]),2)),
    robust=dict(hubs=[int(s) for s in Sd[ri]], worst=round(float(worst[ri]),2)),
    concealed=round(float(game['value']),2),
    worst_demand={names[j]:wdem[j] for j in range(N) if wdem[j]},
    restored_zones=[names[j] for j in restored], lost_zones=[names[j] for j in range(N) if j not in restored],
    gain_vs_random_pct=round(100*(worst[ri]-worst.mean())/worst.mean(),1),
    gain_conceal_pct=round(100*(game['value']-worst[ri])/worst[ri],1))
json.dump(res,open('case_study.json','w'),indent=2)
print(json.dumps({k:res[k] for k in ['random_mean','coverage_max','greedy','robust','concealed',
    'worst_demand','restored_zones','lost_zones','gain_vs_random_pct','gain_conceal_pct']},indent=2))
