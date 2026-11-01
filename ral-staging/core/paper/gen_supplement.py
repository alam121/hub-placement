"""Builds supplement_tables.tex from the raw result files (no numbers typed by hand)."""
import json, os
import numpy as np
R = "/home/claude/ral"; G = "/home/claude/gz"
ci = lambda d: (float(np.mean(d)), float(1.96 * np.std(d, ddof=1) / np.sqrt(len(d)))) if len(d) > 1 else (float(np.mean(d)), 0.0)
f = lambda m, h: f"${m:.2f}\\pm{h:.2f}$"
out = []
T = out.append

# S-I closed-loop, all regimes / policies / q, paired over 15 layouts
S = json.load(open(f"{R}/sim_results.json"))
T("\\begin{table}[h]\\centering\\caption{Closed-loop simulation, all policies (15 layouts; mean simulated value, change vs.\\ fixed maximin with 95\\% $t$-interval over layouts, layouts with a gain, relocation distance per shift, fraction of shifts observed).}\\label{tab:s-sim}\\scriptsize")
T("\\begin{tabular}{@{}llrrrrr@{}}\\toprule regime & policy & $q$ & value & $\\Delta$ vs fixed (\\%) & wins & reloc.\\ (m) / obs.\\\\\\midrule")
for reg in ("sparse", "dense"):
    for q in (0.0, 0.25, 0.5):
        base = {(r["map"], r["layout"]): r["mean"] for r in S if r["regime"] == reg and r["q"] == q and r["policy"] == "fixed_maximin"}
        for p in ("fixed_maximin", "mexclp", "uniform_random", "concealed_q0", "leakage_aware"):
            g = [r for r in S if r["regime"] == reg and r["q"] == q and r["policy"] == p]
            d = [100 * (r["mean"] - base[(r["map"], r["layout"])]) / base[(r["map"], r["layout"])] for r in g]
            m, h = ci(d)
            T(f"{reg} & {p.replace('_', ' ')} & {q} & {np.mean([r['mean'] for r in g]):.2f} & {f(m, h)} & {sum(x > 1e-9 for x in d)}/15 & {np.mean([r['reloc_m'] for r in g]):.0f} / {np.mean([r['observed_frac'] for r in g]):.3f}\\\\")
T("\\bottomrule\\end{tabular}\\end{table}")

# S-II largest-case solver statistics
st = [json.loads(l) for l in open(f"{R}/stress.jsonl")]
sc = [json.loads(l) for l in open(f"{R}/scale_results.jsonl")]
T("\\begin{table}[h]\\centering\\caption{Matrix-free solver statistics. Top: maximum over the 9 instances of each Table~II row. Bottom: stress tests (single instances; $q\\in\\{0,0.5\\}$). Time includes initialization, all exact pure worst cases $\\mu_d$ needed for $P$ and the rows, and all listed $q$; it excludes Python start-up and one-time numba compilation.}\\label{tab:s-solver}\\scriptsize")
T("\\begin{tabular}{@{}rrrrrrrrr@{}}\\toprule $N$ & $K$ & $m$ & $n$ & $c$ & $|\\D|$ & $|\\W|$ & time (s) & B\\&B nodes / BR calls / attacks\\\\\\midrule")
for N in (30, 40, 50):
    for c in (1, 2):
        g = [r for r in sc if r["N"] == N and r["c"] == c]
        T(f"{N} & 20 & 3 & 6 & {c} & 1140 & {g[0]['n_attacks_total']:.1e} & {max(r['sec'] for r in g):.2f} & {max(r['nodes'] for r in g)} / {max(r['br_calls'] for r in g)} / {max(r['attacks_generated'] for r in g)}\\\\")
T("\\midrule")
for r in st:
    T(f"{r['N']} & {r['K']} & {r['m']} & {r['n']} & {r['c']} & {r['n_place']} & {r['n_attacks_total']:.1e} & {r['sec']:.2f} & {r['nodes']} / {r['br_calls']} / {r['attacks_generated']} ({r['priority']})\\\\")
T("\\bottomrule\\end{tabular}\\end{table}")

# S-III relocation exposure
rl = json.load(open(f"{R}/relocation_study.json"))
T("\\begin{table}[h]\\centering\\caption{Policy-dependent relocation exposure (15 sparse layouts). Exposure $=\\mathbb{E}_x[\\tau]/H$ of the exogenous optimum; gains vs.\\ best fixed under end-to-end exposure for the exogenous optimum and the exposure-aware policy; layouts where the exogenous optimum falls below fixed; end-to-end threshold.}\\label{tab:s-reloc}\\scriptsize")
T("\\begin{tabular}{@{}lrrrrrr@{}}\\toprule $H$ & $q$ & exposure (\\%) & exogenous (\\%) & exposure-aware (\\%) & below fixed & $q^\\star_{\\mathrm{end}}$\\\\\\midrule")
for H in ("8h", "1h", "15min", "5min", "2min"):
    th = np.mean([r["qstar_end"] for r in rl if r["H"] == H and r["q"] == "threshold"])
    for q in (0.0, 0.25, 0.5):
        g = [r for r in rl if r["H"] == H and r["q"] == q]
        T(f"{H} & {q} & {100*np.mean([r['exposure_exo'] for r in g]):.2f} & {f(*ci([r['exo_gain'] for r in g]))} & {f(*ci([r['aware_gain'] for r in g]))} & {sum(r['exo_below_fixed'] for r in g)}/15 & {th:.2f}\\\\")
T("\\bottomrule\\end{tabular}\\end{table}")

# S-IV response-model variants
tv = json.load(open(f"{R}/terminal_variants.json"))
T("\\begin{table}[h]\\centering\\caption{Response-model sensitivity on the 240 grid games with $m\\in\\{3,4\\}$, $c\\in\\{1,2\\}$ (all densities and priority profiles) and on the favourable cell (sparse, $c=1$, skewed; 20 games).}\\label{tab:s-term}\\scriptsize")
T("\\begin{tabular}{@{}lrrrr|rrr@{}}\\toprule & \\multicolumn{4}{c|}{all 240} & \\multicolumn{3}{c}{favourable cell}\\\\ variant & $G(0)$ & $G(0.5)$ & mean $q^\\star$ & gain$>$0 & $G(0)$ & $G(0.5)$ & mean $q^\\star$\\\\\\midrule")
sub = [o for o in tv if o["density"] == "sparse" and o["c"] == 1 and o["priority"] == "skewed"]
names = {"aon_p0.7": "all-or-nothing, $p=0.7$ (paper)", "aon_p0.5": "all-or-nothing, $p=0.5$", "aon_p0.9": "all-or-nothing, $p=0.9$", "partial": "partial credit, $p=0.7$"}
for k, nm in names.items():
    T(f"{nm} & {f(*ci([o[k]['G0'] for o in tv]))} & {f(*ci([o[k]['G5'] for o in tv]))} & {np.mean([o[k]['qstar'] for o in tv]):.2f} & {sum(o[k]['G0'] > 1e-6 for o in tv)} & {f(*ci([o[k]['G0'] for o in sub]))} & {f(*ci([o[k]['G5'] for o in sub]))} & {np.mean([o[k]['qstar'] for o in sub]):.2f}\\\\")
T("\\bottomrule\\end{tabular}\\end{table}")

# S-V scenario sensitivity
if os.path.exists(f"{R}/sensitivity_study.json"):
    ss = json.load(open(f"{R}/sensitivity_study.json"))
    T("\\begin{table}[h]\\centering\\caption{One-factor-at-a-time scenario sensitivity on the 15 map layouts (base: $m=3$, $c=1$, $n=6$, density $0.20$, Zipf exponent 1). Mean $\\pm$ 95\\% CI over layouts.}\\label{tab:s-sens}\\scriptsize")
    T("\\begin{tabular}{@{}llrrrrr@{}}\\toprule factor & level & $G(0)$ (\\%) & $G(0.25)$ (\\%) & $G(0.5)$ (\\%) & mean $q^\\star$ & gain$>$0\\\\\\midrule")
    lab = {"n": "alarms $n$", "density": "density", "alpha": "Zipf exponent", "fleet": "$(m,c)$"}
    for fac in ("n", "density", "alpha", "fleet"):
        levels = []
        for o in ss:
            if o["factor"] == fac and o["level"] not in levels: levels.append(o["level"])
        for lv in levels:
            g = [o for o in ss if o["factor"] == fac and o["level"] == lv]
            T(f"{lab[fac]} & {lv} & {f(*ci([o['G0'] for o in g]))} & {f(*ci([o['G25'] for o in g]))} & {f(*ci([o['G5'] for o in g]))} & {np.mean([o['qstar'] for o in g]):.2f} & {sum(o['G0'] > 1e-6 for o in g)}/15\\\\")
    T("\\bottomrule\\end{tabular}\\end{table}")

# S-VI concurrent multi-robot Gazebo shifts
for lay in ("warehouse1", "office0", "warehouse1_verified", "office0_verified", "warehouse1_verified_t20", "office0_verified_t20"):
    p = f"{G}/multi/{lay}/gazebo_results.json"
    if not os.path.exists(p): continue
    res = json.load(open(p))
    desc = {"warehouse1": "warehouse layout 1, model reachability, three Nav2 stacks",
            "office0": "office layout 0, model reachability, three Nav2 stacks",
            "warehouse1_verified": "warehouse layout 1, Nav2-verified reachability, Nav2 stack of the dispatched robot only",
            "office0_verified": "office layout 0, Nav2-verified reachability, Nav2 stack of the dispatched robot only",
            "warehouse1_verified_t20": "warehouse layout 1, Nav2-verified reachability, three Nav2 stacks (behaviour-tree server timeout 20 ms): acknowledgement timeouts under CPU load",
            "office0_verified_t20": "office layout 0, Nav2-verified reachability, three Nav2 stacks (behaviour-tree server timeout 20 ms): acknowledgement timeouts under CPU load"}[lay]
    T(f"\\begin{{table}}[h]\\centering\\caption{{Earlier sampled-shift experiment, superseded by the exact-expectation runs of Tables~S13--S15 (robots without mutual perception). Gazebo shifts, {desc}. Per shift: policy, dispatched robots, per leg (status, arrival s / model s, late flag), realized value, model value with the same success draws, minimum inter-robot distance (m).}}\\scriptsize")
    T("\\begin{tabular}{@{}lrrp{3.9cm}rrr@{}}\\toprule policy & shift & movers & legs & value & model & min $d$\\\\\\midrule")
    for r in res:
        legs = "; ".join(f"{l['status'][:4]} {l['arrival']:.1f}/{l['model_time']:.1f}{'' if l['on_time'] else ' late'}" for l in r["legs"]) or "--"
        md = f"{r['min_pair_dist']:.2f}" if r["min_pair_dist"] is not None else "--"
        T(f"{r['policy'].replace('_', ' ')} & {r['shift']} & {r['movers']} & {legs} & {r['value']:.2f} & {r['model_value_same_draws']:.2f} & {md}\\\\")
    T("\\bottomrule\\end{tabular}\\end{table}")

# S-XV real floor plan (Willow Garage office)
if os.path.exists(f"{R}/willow_results.json"):
    wr = json.load(open(f"{R}/willow_results.json"))
    tci = lambda d: (float(np.mean(d)), float(2.776 * np.std(d, ddof=1) / np.sqrt(len(d))))  # t_{0.975,4}
    T("\\begin{table}[h]\\centering\\caption{Real floor plan (Willow Garage office, 5 layouts). Top: exact model per layout. Bottom: closed-loop change vs.\\ best fixed staging, mean $\\pm$ 95\\% $t$-interval over the 5 layouts (1000 paired shifts each), layouts with a gain.}\\label{tab:s-willow}\\scriptsize")
    T("\\begin{tabular}{@{}lrrrrrr@{}}\\toprule layout & density & $P$ & $G(0)$ & $G(0.25)$ & $G(0.5)$ & $q^\\star$\\\\\\midrule")
    for r in wr["model"]:
        T(f"{r['layout']} & {r['density']:.2f} & {r['P']:.2f} & {r['G0.0']:.1f} & {r['G0.25']:.1f} & {r['G0.5']:.1f} & {r['qstar']:.2f}\\\\")
    T("\\midrule regime & policy & \\multicolumn{5}{l}{$\\Delta$ vs fixed (\\%) at $q=0$ / $0.25$ / $0.5$}\\\\\\midrule")
    S = wr["sim"]
    for reg in ("sparse", "dense"):
        for pol in ("mexclp", "uniform_random", "concealed_q0", "leakage_aware"):
            cells = []
            for q in (0.0, 0.25, 0.5):
                base = {r["layout"]: r["mean"] for r in S if r["regime"] == reg and r["q"] == q and r["policy"] == "fixed_maximin"}
                d = [100 * (r["mean"] - base[r["layout"]]) / base[r["layout"]] for r in S if r["regime"] == reg and r["q"] == q and r["policy"] == pol]
                m, h = tci(d); cells.append(f"${m:.1f}\\pm{h:.1f}$ ({sum(x > 1e-9 for x in d)}/5)")
            T(f"{reg} & {pol.replace('_', ' ')} & \\multicolumn{{5}}{{l}}{{{' / '.join(cells)}}}\\\\")
    T("\\bottomrule\\end{tabular}\\end{table}")

# S-XII exact-expectation concurrent Nav2 runs (three Nav2 stacks, fleet perception, all 15 layouts)
var = json.load(open(f"{G}/multi/exact/verified_all/variability.json"))["summary"]
modes = {"model": "model reachability", "verified_all": ("slack-verified reachability (slack $\\ge$ 3.8\\,s, fixed before these runs), each dispatch executed three times; Nav2 gains are means over the three repetitions. "
         f"Run-to-run variability: median arrival spread {var['range_median']:.2f}\\,s, {var['on_time_flips']} of {var['legs_with_reps']} legs changed on-time status, maximum spread {var['range_max']:.0f}\\,s (converging robots)"),
         "verified2": "concurrency-aware reachability (additionally, for zones served by $\\ge2$ robots, slack $\\ge$ 9.66\\,s: the 95th percentile of shared-zone arrival delays in the model-reachability round, computed on the 14 layouts complete when this round was planned; 9.6\\,s on all 15)"}
for M, desc, suf in [(m, d, "") for m, d in modes.items()] + [("model", "Willow Garage floor plan, model reachability", "_willow"),
                                                             ("verified_all", "Willow Garage floor plan, slack-verified reachability", "_willow")]:
    p = f"{G}/multi/exact/{M}/summary{suf}.json"
    if not os.path.exists(p): continue
    sm = json.load(open(p))
    s = sm["summary"]
    T(f"\\begin{{table}}[h]\\centering\\caption{{Concurrent Nav2 execution of every dispatch the policies can produce, {desc}. Three Nav2 stacks run throughout; robots perceive each other through shared poses. Values are exact expectations over the policy distribution and robot success draws, with Nav2 deciding which legs are on time. "
      f"Per repetition: {s['dispatches']} dispatches ({s['concurrent_dispatches']} with $\\ge$2 robots moving, {s['concurrent_3']} with 3), {s['legs']} legs, {s['on_time']} on time, {s['aborted']} aborted, {s['late']} late.}}\\label{{tab:s-exact-{M}{suf}}}\\scriptsize")
    T("\\begin{tabular}{@{}lrrrrrl@{}}\\toprule layout & pairs & $P$ (model) & fixed (Nav2) & gain model (\\%) & gain Nav2 (\\%) & failed arcs (dock,zone)\\\\\\midrule")
    for r in sm["layouts"]:
        nd = sum(1 for d in sm["legs"] if d["layout"] == r["layout"])
        fa = sorted(set(tuple(a) for a in sm["failed_arcs"].get(r["layout"], [])))
        T(f"{r['layout']} & {r['pairs']} & {r['P']:.2f} & {np.mean(r['realized_fixed']):.2f} & {r['model_gain']:.1f} & {np.mean(r['realized_gain']):.1f} & {', '.join(f'({a},{b})' for a, b in fa) or '--'}\\\\")
    T(f"\\midrule mean $\\pm$ 95\\% CI & & & & ${s['model_gain'][0]:.1f}\\pm{s['model_gain'][1]:.1f}$ & ${s['realized_gain'][0]:.1f}\\pm{s['realized_gain'][1]:.1f}$ & \\\\")
    T("\\bottomrule\\end{tabular}\\end{table}")

open("/home/claude/ral/paper/supplement_tables.tex", "w").write("\n".join(out))
print("wrote", len(out), "lines")
