"""
Regenerate the industrial-campus case-study map (Figure 8) with three
honestly-distinguished zone categories under the robust worst case:
  * unaffected  (w_j = 0)          -- no robot dispatch needed, value automatic
  * loaded & restored (w_j>0, served)   -- robots complete all required actions
  * loaded & unserved (w_j>0, failed)    -- unreachable or over-loaded, value lost
Colours are driven by case_study.json so the figure cannot disagree with the
numbers. Reachability lines use the time-budget test tau_ij + sigma_j <= T.
"""
import json, numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

R = json.load(open("case_study.json"))
sc = R["scenario"]; speed, T = sc["speed"], sc["T"]
# fixed scenario geometry (matches case_study.py): name -> (x, y, priority, task_time)
zones = {
    'Control room'      : (12,46,3,12), 'Comms room'        : (32,49,3,12),
    'Inspection tower'  : (54,49,4,12), 'Loading bay'       : (78,46,3,12),
    'Storage area'      : (95,44,2,12), 'Transformer area'  : (50, 8,12,14),
    'Pump station'      : (24,10,2,12), 'Pipeline junction' : (76,10,2,12),
}
names = list(zones)
hubs = np.array([(20,43),(46,45),(72,44),(45,13),(55,13),(88,20)], float)
opened = R["robust"]["hubs"]                      # indices of opened hubs
wdem = R["worst_demand"]                          # loaded zones -> requests
restored = set(R["restored_zones"]); lost = set(R["lost_zones"])

fig, ax = plt.subplots(figsize=(9.2, 6.2))
# reachability lines from opened hubs (time budget tau + sigma <= T)
for h in opened:
    hx, hy = hubs[h]
    for nm,(x,y,v,tt) in zones.items():
        tau = np.hypot(hx-x, hy-y)/speed
        if tau + tt <= T:
            ax.plot([hx,x],[hy,y], color="#4a9d4a", lw=1.6, alpha=0.55, zorder=1)

# zones, coloured by category
def category(nm, w):
    if w == 0:                 return "unaff"
    return "rest" if nm in restored else "lost"
COL = {"unaff":"#6b8fb5", "rest":"#2e8b57", "lost":"#c0392b"}
for nm,(x,y,v,tt) in zones.items():
    w = int(wdem.get(nm, 0))
    cat = category(nm, w)
    ax.scatter([x],[y], s=180+95*v, c=COL[cat], edgecolors="black",
               linewidths=1.3, zorder=3, alpha=0.92)
    ax.annotate(nm, (x,y), textcoords="offset points", xytext=(0,14+2*np.sqrt(v)),
                ha="center", fontsize=10.5, fontweight="bold")
    if w > 0:                  # adversarial demand load (white number on the zone)
        ax.text(x, y, str(w), ha="center", va="center", fontsize=12.5,
                fontweight="bold", color="white", zorder=4)

# hub sites
for i,(hx,hy) in enumerate(hubs):
    if i in opened:
        ax.scatter([hx],[hy], marker="s", s=230, c="#222222",
                   edgecolors="black", linewidths=1.4, zorder=3)
        ax.annotate(f"hub {i} (open)", (hx,hy), textcoords="offset points",
                    xytext=(-24,6), ha="center", fontsize=10, fontweight="bold")
    else:
        ax.scatter([hx],[hy], marker="s", s=150, facecolors="none",
                   edgecolors="#777777", linewidths=1.4, zorder=2)
        ax.annotate(f"hub {i}", (hx,hy), textcoords="offset points",
                    xytext=(0,-18), ha="center", fontsize=9, color="#777777")

leg = [
    Line2D([0],[0], marker='o', color='w', markerfacecolor=COL["unaff"],
           markeredgecolor='black', markersize=13, label='Unaffected (w=0): no dispatch, value automatic'),
    Line2D([0],[0], marker='o', color='w', markerfacecolor=COL["rest"],
           markeredgecolor='black', markersize=13, label='Loaded & restored by robots (w>0, served)'),
    Line2D([0],[0], marker='o', color='w', markerfacecolor=COL["lost"],
           markeredgecolor='black', markersize=13, label='Loaded & unserved (w>0, value lost)'),
    Line2D([0],[0], marker='s', color='w', markerfacecolor='#222222',
           markeredgecolor='black', markersize=12, label='Opened hub (robust placement)'),
    Line2D([0],[0], color='#4a9d4a', lw=2.2, label='Reachable within mission horizon (τ+σ ≤ T)'),
]
ax.legend(handles=leg, loc="lower center", bbox_to_anchor=(0.5,-0.29),
          ncol=2, fontsize=9.3, frameon=True)
ax.set_xlabel("x  (m)", fontsize=11); ax.set_ylabel("y  (m)", fontsize=11)
ax.set_title("Industrial-campus restoration (synthetic scenario): robust placement under worst-case disruption",
             fontsize=11.5, fontweight="bold")
ax.set_xlim(-4, 104); ax.set_ylim(-8, 62)
ax.grid(alpha=0.25)
plt.tight_layout()
plt.savefig("figs/fig_case_map.png", dpi=150, bbox_inches="tight")
print("wrote figs/fig_case_map.png")
print("unaffected:", [n for n in names if int(wdem.get(n,0))==0])
print("loaded&restored:", [n for n in names if int(wdem.get(n,0))>0 and n in restored])
print("loaded&unserved:", [n for n in names if int(wdem.get(n,0))>0 and n in lost])
