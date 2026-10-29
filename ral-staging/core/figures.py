"""Paper figures (matplotlib, vector PDF + PNG). Categorical slots from the reference palette."""
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

C1, C2, C3, C4, C5 = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"
INK, INK2, GRID = "#1f1f1e", "#5c5b55", "#e4e3de"
BLUES = LinearSegmentedColormap.from_list("b", ["#f4f8fd", "#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"])
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8, "axes.edgecolor": INK2, "axes.labelcolor": INK,
                     "xtick.color": INK2, "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "legend.frameon": False})


def save(fig, name):
    fig.savefig(f"fig_{name}.pdf", bbox_inches="tight"); fig.savefig(f"fig_{name}.png", dpi=220, bbox_inches="tight")
    plt.close(fig)


def grid_figs():
    R = [json.loads(l) for l in open("results.jsonl")]
    for r in R:
        r["gain"] = {q: 100 * (r[k] - r["P"]) / r["P"] for q, k in ((0, "V0"), (0.25, "V0.25"), (0.5, "V0.5"), (0.75, "V0.75"))}
        r["gain"][1.0] = 0.0
    # Fig 1: re-optimized advantage vs q, sparse/skewed, c=1, by m
    fig, ax = plt.subplots(figsize=(3.4, 2.3))
    qs = [0, 0.25, 0.5, 0.75, 1.0]
    for m, col in zip((2, 3, 4), (C1, C2, C3)):
        g = [r for r in R if r["m"] == m and r["c"] == 1 and r["density"] == "sparse" and r["priority"] == "skewed"]
        y = [np.mean([r["gain"][q] for r in g]) for q in qs]
        se = [np.std([r["gain"][q] for r in g], ddof=1) / np.sqrt(len(g)) for q in qs]
        ax.plot(qs, y, color=col, lw=2, marker="o", ms=4, label=f"m = {m} docks")
        ax.fill_between(qs, np.array(y) - np.array(se), np.array(y) + np.array(se), color=col, alpha=0.12, lw=0)
    ax.set_xlabel("observation probability q"); ax.set_ylabel("advantage over best fixed staging (%)")
    ax.set_ylim(bottom=0); ax.legend(loc="upper right")
    save(fig, "q_curves")
    # Fig 2: concealed gain heatmaps (m x c) per density, skewed priorities
    fig, axs = plt.subplots(1, 3, figsize=(7.0, 2.1), sharey=True)
    vmax = 15
    for ax, dens in zip(axs, ("sparse", "medium", "dense")):
        M = np.zeros((3, 3))
        for i, m in enumerate((2, 3, 4)):
            for j, c in enumerate((1, 2, 3)):
                g = [r for r in R if r["m"] == m and r["c"] == c and r["density"] == dens and r["priority"] == "skewed"]
                M[i, j] = np.mean([r["gain"][0] for r in g]) if g else np.nan
        ax.imshow(M, cmap=BLUES, vmin=0, vmax=vmax, origin="lower", aspect="auto")
        for i in range(3):
            for j in range(3):
                ax.text(j, i, f"{abs(M[i, j]) if abs(M[i, j]) < 0.05 else M[i, j]:.1f}", ha="center", va="center", fontsize=8,
                        color="white" if M[i, j] > 0.55 * vmax else INK)
        ax.set_xticks(range(3), ["c=1", "c=2", "c=3"]); ax.set_yticks(range(3), ["m=2", "m=3", "m=4"])
        ax.set_title(f"{dens} reachability", fontsize=8, color=INK); ax.grid(False)
        for s in ax.spines.values():
            s.set_visible(False)
    save(fig, "gain_heatmap")


def map_fig():
    from sim import scenario
    fig, axs = plt.subplots(1, 3, figsize=(7.0, 1.9))
    for ax, kind in zip(axs, ("warehouse", "office", "campus")):
        sc = scenario(kind, 700, density=0.20, priority="skewed", c=1)
        ax.imshow(sc["obst"], cmap=LinearSegmentedColormap.from_list("o", ["#ffffff", "#9b9a93"]), origin="upper")
        for i, (y, x) in enumerate(sc["sites"]):
            for j, (zy, zx) in enumerate(sc["zones"]):
                if sc["A"][i, j]:
                    ax.plot([x, zx], [y, zy], color=C1, lw=0.4, alpha=0.5)
        sy, sx = zip(*sc["sites"]); zy, zx = zip(*sc["zones"])
        ax.scatter(sx, sy, marker="s", s=14, color=C1, edgecolor="white", lw=0.6, zorder=3, label="staging site")
        ax.scatter(zx, zy, marker="o", s=10 + 3 * sc["v"], color=C2, edgecolor="white", lw=0.6, zorder=3, label="zone (size = priority)")
        ax.set_title(kind, fontsize=8, color=INK); ax.set_xticks([]); ax.set_yticks([]); ax.grid(False)
    axs[0].legend(loc="lower left", bbox_to_anchor=(0, -0.32), ncol=2, fontsize=7)
    save(fig, "maps")


def sim_figs():
    S = json.load(open("sim_results.json"))
    pols = ["mexclp", "uniform_random", "concealed_q0", "leakage_aware"]
    names = {"mexclp": "MEXCLP (fixed)", "uniform_random": "uniform random", "concealed_q0": "concealed (q=0) mix", "leakage_aware": "leakage-aware mix"}
    cols = {"mexclp": C4, "uniform_random": C5, "concealed_q0": C2, "leakage_aware": C1}
    fig, axs = plt.subplots(1, 2, figsize=(7.0, 2.3), sharey=True)
    for ax, regime in zip(axs, ("sparse", "dense")):
        for k, p in enumerate(pols):
            ys, es = [], []
            for q in (0.0, 0.25, 0.5):
                d = []
                for r in S:
                    if r["regime"] == regime and r["q"] == q and r["policy"] == p:
                        base = [b for b in S if b["regime"] == regime and b["q"] == q and b["policy"] == "fixed_maximin"
                                and b["map"] == r["map"] and b["layout"] == r["layout"]][0]
                        d.append(100 * (r["mean"] - base["mean"]) / base["mean"])
                ys.append(np.mean(d)); es.append(1.96 * np.std(d, ddof=1) / np.sqrt(len(d)))
            xs = np.arange(3) + (k - 1.5) * 0.19
            ax.bar(xs, ys, width=0.17, color=cols[p], label=names[p], yerr=es, error_kw=dict(lw=0.8, ecolor=INK2, capsize=1.5))
        ax.axhline(0, color=INK2, lw=0.8)
        ax.set_xticks(range(3), ["q = 0", "q = 0.25", "q = 0.5"])
        ax.set_title(f"{regime} reachability", fontsize=8, color=INK)
    axs[0].set_ylabel("simulated value vs fixed maximin (%)")
    h, l = axs[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=4, fontsize=7, bbox_to_anchor=(0.5, -0.08))
    save(fig, "sim_bars")
    # model vs sim
    fig, ax = plt.subplots(figsize=(3.4, 2.4))
    for regime, col in (("sparse", C1), ("dense", C2)):
        g = [r for r in S if r["regime"] == regime]
        ax.scatter([r["model"] for r in g], [r["mean"] for r in g], s=9, color=col, alpha=0.7, edgecolor="white", lw=0.4, label=f"{regime}")
    lo = min(min(r["model"], r["mean"]) for r in S); hi = max(max(r["model"], r["mean"]) for r in S)
    ax.plot([lo, hi], [lo, hi], color=INK2, lw=0.8, ls="--")
    ax.set_xlabel("model value V_x(q)"); ax.set_ylabel("simulated mean value"); ax.legend(loc="upper left")
    save(fig, "model_vs_sim")


if __name__ == "__main__":
    import sys
    for f in sys.argv[1:]:
        globals()[f]()
