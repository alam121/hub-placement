"""Gazebo/Nav2 validation figure: (a) Nav2 vs model travel time, (b) Nav2 trajectory on the warehouse map."""
import sys, json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
sys.path.insert(0, "/home/claude/ral")
from sim import scenario

C = {"warehouse": "#2a78d6", "office": "#eb6834", "campus": "#1baf7a"}
INK, INK2, GRID = "#1f1f1e", "#5c5b55", "#e4e3de"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8, "axes.edgecolor": INK2, "axes.labelcolor": INK,
                     "xtick.color": INK2, "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False,
                     "legend.frameon": False})
S = json.load(open("/home/claude/gz/gz_summary.json"))
fit = S["response_fit"]
fig, (a, b) = plt.subplots(1, 2, figsize=(7.0, 2.5), gridspec_kw=dict(width_ratios=[1, 1.35]))
a.grid(True, color=GRID, lw=0.6)
hi = 0
for m in C:
    L = [l for l in json.load(open(f"/home/claude/gz/results/{m}.json"))["legs"] if l["status"] == "succeeded" and l["kind"] == "response"]
    x = [l["model_len"] / 1.5 for l in L]; y = [l["sim_time"] for l in L]
    hi = max(hi, max(x + y))
    a.scatter(x, y, s=12, color=C[m], edgecolor="white", lw=0.5, label=m, zorder=3)
xx = np.array([0, hi])
a.plot(xx, xx, color=INK2, lw=0.8, ls="--", label="model = Nav2")
a.plot(xx, fit["alpha"] * xx + fit["beta"], color=INK, lw=1.2, label=f"fit: {fit['alpha']:.2f}t + {fit['beta']:.1f}")
a.set_xlabel("model travel time (s)"); a.set_ylabel("Gazebo/Nav2 travel time (s)"); a.legend(loc="upper left", fontsize=7)
sc = scenario("warehouse", 700, density=0.20, priority="skewed", c=1)
H, W = sc["obst"].shape
b.imshow(sc["obst"], cmap=LinearSegmentedColormap.from_list("o", ["#ffffff", "#9b9a93"]), extent=(0, W, 0, H), origin="upper")
tr = np.array(json.load(open("/home/claude/gz/results/warehouse.json"))["traj"])
b.plot(tr[:, 0], tr[:, 1], color=C["warehouse"], lw=0.8, alpha=0.85)
meta = json.load(open("/home/claude/gz/maps/meta.json"))["warehouse"]
sx, sy = zip(*meta["sites"]); zx, zy = zip(*meta["zones"])
b.scatter(sx, sy, marker="s", s=14, color=C["warehouse"], edgecolor="white", lw=0.6, zorder=3, label="staging site")
b.scatter(zx, zy, marker="o", s=14, color=C["office"], edgecolor="white", lw=0.6, zorder=3, label="zone")
b.set_xticks([]); b.set_yticks([]); b.set_title("Nav2 trajectory, warehouse world", fontsize=8, color=INK)
b.legend(loc="lower left", bbox_to_anchor=(0, -0.16), ncol=2, fontsize=7)
fig.savefig("/home/claude/ral/paper/fig_gazebo.pdf", bbox_inches="tight")
fig.savefig("/home/claude/gz/fig_gazebo.png", dpi=200, bbox_inches="tight")
