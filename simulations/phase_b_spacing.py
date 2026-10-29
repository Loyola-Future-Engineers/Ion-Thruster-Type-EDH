"""Phase B: electrode spacing for one-, two- and three-stage devices.

Outputs: data/phase_b_*.csv, charts/B*.png|svg, numbers quoted in docs/results/spacing.md.
Run: .venv/bin/python simulations/phase_b_spacing.py
"""
import itertools
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ehd import device as D, reference as ref, study  # noqa: E402
from ehd.constants import STANDARD_AIR  # noqa: E402
from ehd.plotting import COLORS, DATA, save  # noqa: E402

A = ref.ASSUMPTIONS


def single_stage_sweep():
    gaps = np.round(np.geomspace(0.008, 0.08, 18), 4)
    rows = study.run_many([ref.device(1, gaps=[g]) for g in gaps])
    df = pd.DataFrame(rows)
    df["gap_mm"] = gaps * 1e3
    # fixed-voltage curves (20 kV) to separate geometry from the voltage choice
    fixed = []
    for g in gaps:
        dev = ref.device(1, gaps=[g])
        geo = D.analyse_geometry(dev, n_lines=48)
        for V in (15e3, 20e3, 25e3):
            vsp = D.spark_limits(dev)
            r = D.evaluate(geo, V) if (V > geo.onset[0] and V < vsp) else None
            fixed.append({"gap_mm": g * 1e3, "V_kV": V / 1e3,
                          "thrust_mN": r["thrust"] * 1e3 if r else np.nan,
                          "TP_mNW": r["T_per_P"] * 1e3 if r else np.nan,
                          "P_W": r["P"] if r else np.nan, "Q_cfm": r["Q"] * 2118.88 if r else np.nan,
                          "V_onset_kV": geo.onset[0] / 1e3, "V_spark_kV": vsp / 1e3})
    fx = pd.DataFrame(fixed)
    df.to_csv(DATA / "phase_b_single_stage.csv", index=False)
    fx.to_csv(DATA / "phase_b_single_stage_fixedV.csv", index=False)
    return df, fx


def plot_single(df, fx):
    fig, axs = plt.subplots(2, 2, figsize=(11, 7.5))
    specs = [("thrust_mN", "Thrust (mN)", "B1 Gap vs thrust"),
             ("Q_cfm", "Volumetric flow (CFM)", "B2 Gap vs airflow"),
             ("P_W", "Electrical power (W)", "B3 Gap vs power"),
             ("TP_mNW", "Thrust-to-power (mN/W)", "B4 Gap vs thrust-to-power")]
    for ax, (col, lab, title) in zip(axs.flat, specs):
        ax.plot(df.gap_mm, df["op_" + col], "o-", color="k", lw=2,
                label=f"V = min({ref.V_SUPPLY_MAX/1e3:.0f} kV, {ref.SPARK_MARGIN:.0%} sparkover)")
        for V, c in zip((15, 20, 25), ("#93c5fd", "#3b82f6", "#1e3a8a")):
            s = fx[fx.V_kV == V]
            ax.plot(s.gap_mm, s[col], "--", color=c, label=f"fixed {V} kV")
        ax.set_xscale("log"); ax.set_xlabel("Emitter-collector gap (mm)"); ax.set_ylabel(lab)
        ax.set_xticks([10, 15, 20, 30, 40, 60, 80]); ax.get_xaxis().set_major_formatter(plt.ScalarFormatter())
        ax.set_title(title.split(" ", 1)[1])
        ax.axvline(ref.V_SUPPLY_MAX / (ref.SPARK_MARGIN * STANDARD_AIR.e_spark) * 1e3, color="#999", lw=0.8)
    axs[0, 0].legend(fontsize=7.5, loc="upper left")
    axs[0, 0].annotate("supply-limited\nbeyond this gap", xy=(0.62, 0.05), xycoords="axes fraction", fontsize=8, color="#666")
    fig.suptitle("Single stage: emitter-collector gap sweep", fontweight="bold")
    fig.tight_layout()
    save(fig, "B1_single_stage_gap_sweep", assumptions=A + " Ring emitter, torus collector, both 30 mm dia.")

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(df.gap_mm, df.V_onset_kV, color=COLORS["power"], label="Corona onset (Peek, CSM field)")
    ax.plot(df.gap_mm, df.V_spark_kV, color=COLORS["efficiency"], label="Sparkover estimate (1.0 MV/m)")
    ax.fill_between(df.gap_mm, df.V_spark_kV * 0.7, df.V_spark_kV * 1.4, color=COLORS["efficiency"], alpha=0.12,
                    label="Sparkover uncertainty band (0.7-1.4 MV/m)")
    ax.plot(df.gap_mm, df.op_V_kV, "k-", lw=2, label="Chosen operating voltage")
    ax.axhline(ref.V_SUPPLY_MAX / 1e3, color="#666", ls=":", label="Assumed supply limit")
    ax.set_xscale("log"); ax.set_xlabel("Gap (mm)"); ax.set_ylabel("Voltage (kV)")
    ax.set_xticks([10, 15, 20, 30, 40, 60, 80]); ax.get_xaxis().set_major_formatter(plt.ScalarFormatter())
    ax.set_title("Operating window: onset to sparkover"); ax.legend(fontsize=8)
    ax2 = ax.twinx(); ax2.plot(df.gap_mm, df.op_margin * 100, color=COLORS["margin"], ls="--")
    ax2.set_ylabel("Breakdown margin at operating point (%)", color=COLORS["margin"]); ax2.grid(False)
    save(fig, "B5_breakdown_margin", assumptions=A)


PATTERNS = {  # total gap held at 75 mm (3 stages) / 50 mm (2 stages)
    3: {"equal": [25, 25, 25], "decreasing": [35, 25, 15], "increasing": [15, 25, 35]},
    2: {"equal": [25, 25], "decreasing": [30, 20], "increasing": [20, 30]},
}


def pattern_study():
    devs, meta = [], []
    for n, pats in PATTERNS.items():
        for name, g in pats.items():
            for s in (15, 25, 40):
                for sep in (False, True):
                    devs.append(ref.device(n, gaps=[x / 1e3 for x in g], spacings=[s / 1e3] * (n - 1),
                                           per_stage_supply=sep))
                    meta.append({"pattern": name, "spacing_mm": s, "supply": "per-stage" if sep else "common"})
    rows = study.run_many(devs)
    df = pd.DataFrame([{**m, **r} for m, r in zip(meta, rows)])
    df.to_csv(DATA / "phase_b_gap_patterns.csv", index=False)
    return df


def plot_patterns(df):
    for supply in ("common", "per-stage"):
        fig, axs = plt.subplots(1, 3, figsize=(13, 4.3))
        pats = ["equal", "decreasing", "increasing"]
        for ax, (col, lab) in zip(axs, [("eqP_thrust_mN", f"Thrust at {ref.P_COMPARE:.0f} W (mN)"),
                                        ("op_thrust_mN", "Thrust at max safe voltage (mN)"),
                                        ("op_TP_mNW", "Thrust/power at max safe voltage (mN/W)")]):
            x = np.arange(6)
            for j, p in enumerate(pats):
                vals, labels = [], []
                for n in (2, 3):
                    for s in (15, 25, 40):
                        r = df[(df.n_stages == n) & (df.pattern == p) & (df.spacing_mm == s)
                               & (df.supply == supply)].iloc[0]
                        vals.append(r[col]); labels.append(f"{n}st\ns={s}")
                ax.bar(x[:len(vals)] + (j - 1) * 0.27, vals, 0.27, color=COLORS[p], label=p)
            ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=8); ax.set_ylabel(lab)
        axs[0].legend(title="gap pattern", fontsize=8)
        axs[0].set_title("Equal power"); axs[1].set_title("Max safe voltage"); axs[2].set_title("Efficiency")
        fig.suptitle(f"Equal vs unequal stage gaps, {supply} supply (same total gap; 2-stage 20/30 mm, "
                     "3-stage 15/25/35 mm)", fontweight="bold")
        fig.tight_layout()
        save(fig, f"B6_gap_patterns_{supply}_supply",
             assumptions=A + " s = collector-to-next-emitter spacing (mm). Per-stage supply: V_k proportional to gap_k.")

    fig, ax = plt.subplots(figsize=(8, 4.3))
    sub = df[(df.n_stages == 3) & (df.supply == "common")]
    for i, s in enumerate((15, 25, 40)):
        for j, p in enumerate(pats):
            r = sub[(sub.pattern == p) & (sub.spacing_mm == s)].iloc[0]
            bf = [r.get(f"s{k}_backflow", np.nan) * 100 for k in (1, 2, 3)]
            ax.bar(i * 4 + j * 1.1 + np.arange(3) * 0.33, bf, 0.3, color=COLORS[p], edgecolor="k", lw=0.4)
    ax.set_xticks([i * 4 + 1.43 for i in range(3)])
    ax.set_xticklabels([f"s = {s} mm" for s in (15, 25, 40)])
    ax.set_ylabel("Current lost to upstream collector (%)")
    ax.set_title("Back-flow current per stage (3 stages; bars = stage 1, 2, 3 within each colour)")
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=COLORS[p], label=p) for p in pats], fontsize=8)
    save(fig, "B7_backflow_by_stage", assumptions=A)


def heatmap():
    gaps = [10, 15, 20, 25, 30, 40, 50]
    sps = [8, 12, 16, 20, 25, 30, 40, 50]
    devs, meta = [], []
    for g, s in itertools.product(gaps, sps):
        devs.append(ref.device(2, gaps=[g / 1e3] * 2, spacings=[s / 1e3])); meta.append({"gap": g, "s": s})
    rows = study.run_many(devs)
    df = pd.DataFrame([{**m, **r} for m, r in zip(meta, rows)])
    df.to_csv(DATA / "phase_b_heatmap_2stage.csv", index=False)
    fig, axs = plt.subplots(1, 3, figsize=(14, 4.4))
    for ax, (col, lab, cmap) in zip(axs, [("op_thrust_mN", "Thrust at max safe V (mN)", "viridis"),
                                          ("op_TP_mNW", "Thrust/power at max safe V (mN/W)", "magma"),
                                          ("s2_backflow", "Stage-2 back-flow fraction", "Reds")]):
        piv = df.pivot(index="gap", columns="s", values=col)
        im = ax.imshow(piv.values, origin="lower", aspect="auto", cmap=cmap)
        ax.set_xticks(range(len(sps))); ax.set_xticklabels(sps)
        ax.set_yticks(range(len(gaps))); ax.set_yticklabels(gaps)
        ax.set_xlabel("Inter-stage spacing s (mm)"); ax.set_ylabel("Stage gap d (mm)")
        ax.set_title(lab, fontsize=10); ax.grid(False)
        for (i, j), v in np.ndenumerate(piv.values):
            if np.isfinite(v):
                ax.text(j, i, f"{v:.2f}" if v < 10 else f"{v:.0f}", ha="center", va="center", fontsize=6.5,
                        color="w" if col != "s2_backflow" else "k")
        fig.colorbar(im, ax=ax, shrink=0.85)
    fig.suptitle("Two equal stages: gap d vs inter-stage spacing s", fontweight="bold")
    fig.tight_layout()
    save(fig, "B8_heatmap_gap_vs_spacing", assumptions=A + " Voltage limited by the smaller of d and s.")
    return df


def independent_gaps():
    """Coarse search over three independent gaps at fixed spacing 25 mm."""
    opts = [12, 18, 25, 32, 40]
    devs, meta = [], []
    for g in itertools.product(opts, repeat=3):
        for sep in (False, True):
            devs.append(ref.device(3, gaps=[x / 1e3 for x in g], per_stage_supply=sep))
            meta.append({"g1": g[0], "g2": g[1], "g3": g[2], "supply": "per-stage" if sep else "common"})
    rows = study.run_many(devs)
    df = pd.DataFrame([{**m, **r} for m, r in zip(meta, rows)])
    df.to_csv(DATA / "phase_b_independent_gaps_3stage.csv", index=False)
    return df


def plot_independent(df):
    fig, axs = plt.subplots(2, 2, figsize=(12, 8))
    for ax, col, lab, sup in [(axs[0, 0], "eqP_thrust_mN", f"Thrust at {ref.P_COMPARE:.0f} W (mN)", "common"),
                              (axs[0, 1], "op_thrust_mN", "Thrust at max safe voltage (mN)", "common"),
                              (axs[1, 0], "eqP_thrust_mN", f"Thrust at {ref.P_COMPARE:.0f} W (mN)", "per-stage"),
                              (axs[1, 1], "op_thrust_mN", "Thrust at max safe voltage (mN)", "per-stage")]:
        d = df[df.supply == sup].dropna(subset=[col]).sort_values(col, ascending=False).head(12)
        labels = [f"{a}/{b}/{c}" for a, b, c in zip(d.g1, d.g2, d.g3)]
        cols = [COLORS["decreasing"] if a > b > c else COLORS["increasing"] if a < b < c else
                COLORS["equal"] if a == b == c else "#9ca3af" for a, b, c in zip(d.g1, d.g2, d.g3)]
        ax.barh(labels[::-1], d[col].values[::-1], color=cols[::-1])
        ax.set_xlabel(lab); ax.set_title(f"{sup} supply: top 12 of 125 gap triples (mm)", fontsize=10)
    from matplotlib.patches import Patch
    axs[0, 1].legend(handles=[Patch(color=COLORS["decreasing"], label="d1>d2>d3"),
                           Patch(color=COLORS["increasing"], label="d1<d2<d3"),
                           Patch(color=COLORS["equal"], label="equal"), Patch(color="#9ca3af", label="other")],
                  fontsize=8, loc="lower right")
    fig.suptitle("Three stages with independently chosen gaps (spacing 25 mm)", fontweight="bold")
    fig.tight_layout()
    save(fig, "B9_independent_gap_search", assumptions=A)


if __name__ == "__main__":
    DATA.mkdir(exist_ok=True)
    parts = sys.argv[1:] or ["single", "patterns", "heatmap", "independent"]
    if "single" in parts:
        df, fx = single_stage_sweep(); plot_single(df, fx)
    if "patterns" in parts:
        plot_patterns(pattern_study())
    if "heatmap" in parts:
        heatmap()
    if "independent" in parts:
        plot_independent(independent_gaps())
    print("done")
