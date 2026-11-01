"""Charts for the revised video, drawn from the raw result files."""
import json, numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
C1, INK, INK2, GRID, LIGHT = "#2a78d6", "#1f1f1e", "#5c5b55", "#e4e3de", "#9ec5f4"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 15, "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2,
                     "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": GRID, "axes.axisbelow": True})
tv = json.load(open("/home/claude/ral/terminal_variants.json"))
sub = [o for o in tv if o["density"] == "sparse" and o["c"] == 1 and o["priority"] == "skewed"]
lab = [("aon_p0.9", "all-or-nothing\np = 0.9"), ("aon_p0.7", "all-or-nothing\np = 0.7 (paper)"), ("aon_p0.5", "all-or-nothing\np = 0.5"), ("partial", "partial credit\np = 0.7")]
m = [np.mean([o[k]["G0"] for o in sub]) for k, _ in lab]
h = [1.96 * np.std([o[k]["G0"] for o in sub], ddof=1) / np.sqrt(len(sub)) for k, _ in lab]
fig, ax = plt.subplots(figsize=(8.6, 4.9), dpi=100)
ax.bar(range(4), m, yerr=h, color=[C1, C1, LIGHT, LIGHT], width=0.6, error_kw=dict(ecolor=INK2, capsize=4, lw=1.2))
for i, v in enumerate(m): ax.text(i + 0.33, v + 0.4, f"{v:.1f}%", ha="left", fontsize=15, color=INK)
ax.set_xticks(range(4), [l for _, l in lab], fontsize=12); ax.set_ylabel("gain over best fixed staging, q = 0")
ax.set_ylim(0, 22); ax.set_title("Response model (favourable cell, 20 games)", fontsize=15, color=INK, pad=12); ax.grid(axis="x", visible=False)
fig.savefig("chart_response.png", bbox_inches="tight"); plt.close(fig)
S = json.load(open("/home/claude/gz/multi/gazebo_multi_summary.json"))
groups = [("warehouse1", "warehouse\nmodel routes"), ("office0", "office\nmodel routes"), ("warehouse1_verified", "warehouse\nverified routes"), ("office0_verified", "office\nverified routes")]
mod = [S[k]["model_gain_same_draws"] for k, _ in groups]; rea = [S[k]["realized_gain_vs_P"] for k, _ in groups]
fig, ax = plt.subplots(figsize=(8.6, 4.9), dpi=100); x = np.arange(4); w = 0.36
ax.bar(x - w / 2, mod, w, color=LIGHT, label="model (same success draws)"); ax.bar(x + w / 2, rea, w, color=C1, label="realized in Gazebo / Nav2")
for i in range(4):
    ax.text(x[i] - w / 2, mod[i] + 0.3, f"{mod[i]:.1f}", ha="center", fontsize=13, color=INK2)
    ax.text(x[i] + w / 2, rea[i] + 0.3, f"{rea[i]:.1f}", ha="center", fontsize=13, color=INK)
ax.set_xticks(x, [l for _, l in groups], fontsize=12); ax.set_ylabel("gain over fixed staging (%)"); ax.legend(frameon=False, fontsize=12, loc="upper left")
ax.set_title("Concurrent Nav2 shifts in Gazebo (20 per layout)", fontsize=15, color=INK, pad=12); ax.grid(axis="x", visible=False); ax.set_ylim(0, 20)
fig.savefig("chart_gazebo.png", bbox_inches="tight"); plt.close(fig)
