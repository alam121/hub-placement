"""Fig. 1 (Lemma 2: same marginals, different worst case) and the per-layout planned-vs-Nav2 plot."""
import json, collections
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle

plt.rcParams.update({"font.family": "serif", "font.size": 7.5, "axes.linewidth": 0.6, "pdf.fonttype": 42})
INK, MUTED, GRID = "#1f1f1e", "#6b6a65", "#d9d8d2"
C_MODEL, C_VER = "#eb6834", "#2a78d6"
OPEN = "#2a78d6"

# ---------------------------------------------------------------- Fig. 1: Lemma 2
L2 = json.load(open("/home/claude/ral/lemma2_example.json"))
fig, axes = plt.subplots(2, 2, figsize=(3.45, 1.95), gridspec_kw=dict(hspace=0.08, wspace=0.08))
sx = [0.8, 1.6, 2.4, 3.2]                    # site x positions
zA, zB = (1.2, 1.55), (2.8, 1.55)
cfgs = {0: [(0, 1), (2, 3)], 1: [(0, 2), (1, 3)]}
for col in (0, 1):
    for row in (0, 1):
        ax = axes[row, col]; ax.set_xlim(0.2, 3.8); ax.set_ylim(0.15, 2.05); ax.axis("off")
        openset = cfgs[col][row]
        for i in range(4):                       # reachability lines
            z = zA if i < 2 else zB
            ax.plot([sx[i], z[0]], [0.62, z[1]], color=GRID, lw=0.8, zorder=1)
        ax.scatter([zA[0]], [zA[1]], s=150, marker="o", facecolor="white", edgecolor=INK, lw=0.8, zorder=2)
        ax.scatter([zB[0]], [zB[1]], s=65, marker="o", facecolor="white", edgecolor=INK, lw=0.8, zorder=2)
        ax.text(*zA, "A", ha="center", va="center", fontsize=7.5, zorder=3)
        ax.text(*zB, "B", ha="center", va="center", fontsize=6.5, zorder=3)
        ax.text(zA[0] - 0.32, zA[1], "$v{=}10$", ha="right", va="center", fontsize=6.5, color=MUTED)
        ax.text(zB[0] + 0.24, zB[1], "$v{=}1$", ha="left", va="center", fontsize=6.5, color=MUTED)
        for i in range(4):
            o = i in openset
            ax.add_patch(Rectangle((sx[i] - 0.15, 0.32), 0.3, 0.3, fc=OPEN if o else "white", ec=INK, lw=0.8, zorder=2))
            ax.text(sx[i], 0.47, str(i + 1), ha="center", va="center", fontsize=6.5, color="white" if o else INK, zorder=3)
        ax.text(0.22, 0.47, "1/2", ha="left", va="center", fontsize=6, color=MUTED)
        if row == 0:
            name = "$x$: docks {1,2} or {3,4}" if col == 0 else "$x'$: docks {1,3} or {2,4}"
            ax.set_title(name, fontsize=7.5, pad=2)
for col, key, att in ((0, "x", "one alarm in each zone"), (1, "x_prime", "both alarms in A")):
    z = L2[key]["z"]
    axes[1, col].text(2.0, -0.12, f"worst case {z:.2f}", ha="center", va="top", fontsize=8, fontweight="bold",
                      transform=axes[1, col].transData)
    axes[1, col].text(2.0, -0.42, f"({att})", ha="center", va="top", fontsize=6.5, color=MUTED, transform=axes[1, col].transData)
fig.text(0.5, 0.995, "each dock is open with probability 1/2 under both policies", ha="center", va="top", fontsize=6.8, color=MUTED)
fig.subplots_adjust(left=0.01, right=0.99, top=0.88, bottom=0.17)
fig.savefig("/home/claude/ral/paper/fig_lemma2.pdf"); fig.savefig("/home/claude/ral/fig_lemma2.png", dpi=220)

# ---------------------------------------------------------------- per-layout planned vs Nav2
B = "/home/claude/gz/multi/exact"
def rows(m):
    s = json.load(open(f"{B}/{m}/summary.json"))
    return {r["layout"]: r for r in s["layouts"]}, s
def causes(m):
    """per layout: did any failed leg come from converging robots (>=2 robots to one zone)?"""
    out = collections.defaultdict(set)
    import glob, os
    for p in glob.glob(f"{B}/{m}/*/gazebo_results.json"):
        L = os.path.basename(os.path.dirname(p))
        for r in json.load(open(p)):
            zc = collections.Counter(l["zone"] for l in r["legs"])
            for l in r["legs"]:
                if not l["on_time"]:
                    out[L].add("conv" if zc[l["zone"]] > 1 and not (L == "office0" and (l["dock"], l["zone"]) == (7, 8)) else
                               ("wall" if (L, l["dock"], l["zone"]) == ("office0", 7, 8) else "slack"))
    return out
RM, _ = rows("model"); RV, _ = rows("verified_all")
CM, CV = causes("model"), causes("verified_all")
fig, ax = plt.subplots(figsize=(3.45, 2.35))
lim = (-21, 30)
ax.axhline(0, color=GRID, lw=0.6, zorder=0); ax.axvline(0, color=GRID, lw=0.6, zorder=0)
ax.plot(lim, lim, color=MUTED, lw=0.8, ls=(0, (4, 3)), zorder=1)
ax.text(18.3, 20.2, "realized = planned", fontsize=6.3, color=MUTED, ha="right")
for R, Cs, col, mk, lab in ((RM, CM, C_MODEL, "o", "model reach."), (RV, CV, C_VER, "s", "slack-verified (3 runs)")):
    xs = np.array([R[L]["model_gain"] for L in R]); ys = np.array([np.mean(R[L]["realized_gain"]) for L in R])
    ax.scatter(xs, ys, s=22, marker=mk, facecolor=col if mk == "s" else "white", edgecolor=col, lw=1.1, zorder=3, label=lab)
    for L, x, y in zip(R, xs, ys):
        if "conv" in Cs.get(L, ()):
            ax.scatter([x], [y], s=95, marker="o", facecolor="none", edgecolor=INK, lw=0.7, zorder=2)
ann = [(RM, "office4", "office 4: low-slack arcs", (6.5, -17.5)), (RV, "warehouse4", "warehouse 4: fixed\nbaseline's arc fails", (6.5, 25.5)),
       (RV, "campus1", "campus 1", (16.6, 4.6)), (RV, "office0", "office 0", (12.8, -5.6))]
for R, L, t, (tx, ty) in ann:
    x, y = R[L]["model_gain"], np.mean(R[L]["realized_gain"])
    ax.annotate(t, (x, y), (tx, ty), fontsize=6.3, color=INK, ha="left", va="center",
                arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.5, shrinkA=1, shrinkB=4))
ax.scatter([], [], s=95, marker="o", facecolor="none", edgecolor=INK, lw=0.7, label="converging robots")
ax.set_xlim(-1, 18.5); ax.set_ylim(*lim)
ax.set_xlabel("planned gain over best fixed staging (%)"); ax.set_ylabel("Nav2-realized gain (%)")
for s_ in ("top", "right"): ax.spines[s_].set_visible(False)
ax.tick_params(width=0.6, length=2.5)
fig.legend(*ax.get_legend_handles_labels(), loc="upper center", ncol=3, fontsize=6.0, frameon=False, handletextpad=0.2, columnspacing=0.8)
fig.tight_layout(pad=0.3, rect=(0, 0, 1, 0.92))
fig.savefig("/home/claude/ral/paper/fig_nav2_layouts.pdf"); fig.savefig("/home/claude/ral/fig_nav2_layouts.png", dpi=220)
print("ok")
