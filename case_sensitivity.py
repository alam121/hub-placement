import numpy as np, itertools, json
from exact_solver import exact_terminal
from vectorized_solver import compositions_array
from game_lp import solve_matrix_game
zones={'Control room':(12,46,3,12),'Comms room':(32,49,3,12),'Inspection tower':(54,49,4,12),
       'Loading bay':(78,46,3,12),'Storage area':(95,44,2,12),'Transformer area':(50,8,12,14),
       'Pump station':(24,10,2,12),'Pipeline junction':(76,10,2,12)}
Zc=np.array([[z[0],z[1]] for z in zones.values()],float)
v=np.array([z[2] for z in zones.values()],float); tt=np.array([z[3] for z in zones.values()],float)
N=len(zones); hubs=np.array([(20,43),(46,45),(72,44),(45,13),(55,13),(88,20)],float); H=len(hubs)
m,n=2,7
def go(speed,T,c):
    D=np.array([[np.hypot(*(hubs[i]-Zc[j]))/speed+tt[j] for j in range(N)] for i in range(H)])
    R=D<=T; Dbig=np.where(R,D,1e9)
    Sd=list(itertools.combinations(range(H),m)); Sa=compositions_array(n,N)
    U=np.array([[exact_terminal(Sa[k],pl,Dbig,v,c,0.85,T,N) for k in range(len(Sa))] for pl in Sd])
    g=solve_matrix_game(U)
    return dict(reach=int(R.sum()),Vseq=round(float(U.min(1).max()),2),Vsim=round(float(g['value']),2))
out={'speed':[dict(x=s,**go(s,20.0,4)) for s in [1.5,2.0,2.5,3.0,3.5,4.0]],
     'T':[dict(x=t,**go(2.5,t,4)) for t in [16,18,20,22,24,26]],
     'c':[dict(x=c,**go(2.5,20.0,c)) for c in [2,3,4,5,6]]}
json.dump(out,open('case_sensitivity.json','w'),indent=2)
for k in out: print(k, out[k])
