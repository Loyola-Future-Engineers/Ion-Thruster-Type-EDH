"""Phase G: sensitivity, Monte-Carlo uncertainty and multi-objective (Pareto) design search.

Outputs: data/phase_g_*.csv, charts/G*.png|svg.
Run: .venv/bin/python simulations/phase_g_sensitivity_pareto.py [sens] [mc] [pareto]
"""
import copy
import itertools
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ehd import corona, device as D, reference as ref  # noqa: E402
from ehd.constants import STANDARD_AIR  # noqa: E402
from ehd.plotting import COLORS, DATA, save  # noqa: E402

A = ref.ASSUMPTIONS
BASE = dict(n=2, gap=0.025, spacing=0.050)


def make(n=2, gap=0.025, spacing=0.050, **kw):
    return ref.device(n, gaps=[gap] * n, spacings=[spacing] * (n - 1), **kw)


def metrics(dev, air=STANDARD_AIR, k_scale=1.0, geo=None):
    geo = geo or D.analyse_geometry(dev, air, n_lines=48)
    v = min(ref.V_SUPPLY_MAX, ref.SPARK_MARGIN * D.spark_limits(dev, air))
    if v <= geo.onset.min():
        return {"thrust_mN": 0.0, "TP_mNW": np.nan, "Q_cfm": 0.0, "P_W": 0.0}
    r = D.evaluate(geo, v, air, k_scale)
    return {"thrust_mN": r["thrust"] * 1e3, "TP_mNW": r["T_per_P"] * 1e3, "Q_cfm": r["Q"] * 2118.88, "P_W": r["P"]}


# ---------------------------------------------------------------- one-at-a-time sensitivity
FACTORS = {  # name: (low, high, how to apply, label)
    "gap": (0.020, 0.030, "geom", "Stage gap 20-30 mm"),
    "spacing": (0.0375, 0.0625, "geom", "Inter-stage spacing 37.5-62.5 mm"),
    "emitter_wire": (5e-5, 2e-4, "geom", "Emitter edge radius 50-200 um"),
    "ring_dia": (0.026, 0.034, "geom", "Ring diameter 26-34 mm"),
    "temperature_K": (273.15, 313.15, "air", "Air temperature 0-40 C"),
    "pressure_Pa": (90e3, 103e3, "air", "Air pressure 90-103 kPa (~1 km altitude to sea level)"),
    "mobility_ref": (1.8e-4, 2.2e-4, "air", "Ion mobility 1.8-2.2e-4 m2/Vs (humidity proxy)"),
    "e_spark_ref": (0.7e6, 1.4e6, "air", "Sparkover field 0.7-1.4 MV/m"),
    "peek_m": (0.8, 1.0, "air", "Peek surface factor 0.8-1.0"),
    "k_scale": (0.5, 2.0, "model", "Current closure factor 0.5-2"),
}


def sens_case(args):
    name, value = args
    kw = dict(BASE)
    air = STANDARD_AIR
    k_scale = 1.0
    stage_kw = {}
    if name == "ring_dia":
        stage_kw = {"emitter_radius": value / 2, "collector_radius": value / 2}
    elif name == "emitter_wire":
        stage_kw = {"emitter_wire": value}
    elif name in ("gap", "spacing"):
        kw[name] = value
    elif name == "k_scale":
        k_scale = value
    elif name is not None:
        air = air.with_(**{name: value})
    return name, value, metrics(make(**kw, **stage_kw), air, k_scale)


def sensitivity():
    jobs = [(None, None)] + [(k, v) for k, (lo, hi, _, _) in FACTORS.items() for v in (lo, hi)]
    with ProcessPoolExecutor(6) as ex:
        res = list(ex.map(sens_case, jobs))
    base = res[0][2]
    rows = [{"factor": k, "value": v, **m} for k, v, m in res[1:]]
    df = pd.DataFrame(rows)
    df.to_csv(DATA / "phase_g_sensitivity.csv", index=False)
    fig, axs = plt.subplots(1, 2, figsize=(13, 5))
    for ax, col, lab in [(axs[0], "thrust_mN", "Thrust at max safe V"), (axs[1], "TP_mNW", "Thrust/power at max safe V")]:
        spans = []
        for k, (lo, hi, _, label) in FACTORS.items():
            s = df[df.factor == k].set_index("value")[col]
            spans.append((label, (s.loc[lo] / base[col] - 1) * 100, (s.loc[hi] / base[col] - 1) * 100))
        spans.sort(key=lambda t: max(abs(t[1]), abs(t[2])))
        for i, (label, l, h) in enumerate(spans):
            ax.barh(i, l, color="#93c5fd", height=0.6); ax.barh(i, h, color="#1d4ed8", height=0.6)
        ax.set_yticks(range(len(spans))); ax.set_yticklabels([s[0] for s in spans], fontsize=8)
        ax.axvline(0, color="k", lw=0.8); ax.set_xlabel(f"Change in {lab.lower()} (%)")
        ax.set_title(f"{lab}: base {base[col]:.2f} {'mN' if col == 'thrust_mN' else 'mN/W'}")
    from matplotlib.patches import Patch
    axs[0].legend(handles=[Patch(color="#93c5fd", label="low end of range"), Patch(color="#1d4ed8", label="high end")],
                  fontsize=8, loc="lower right")
    fig.suptitle("One-at-a-time sensitivity, 2-stage reference (d = 25 mm, s = 50 mm)", fontweight="bold")
    fig.tight_layout()
    save(fig, "G1_sensitivity_tornado", assumptions=A + " Humidity is represented only through the mobility "
         "and sparkover ranges; no humidity-specific model is used.")
    return df, base


# ---------------------------------------------------------------- Monte-Carlo uncertainty
def monte_carlo(n_samples=600, seed=1):
    out = []
    for n_st in (1, 2, 3):
        rng = np.random.default_rng(seed)        # common random numbers: paired samples across designs
        dev = make(n=n_st)
        geo0 = D.analyse_geometry(dev, n_lines=48)
        peek0 = corona.peek_field_wire(dev.stages[0].emitter_wire, STANDARD_AIR)
        for i in range(n_samples):
            air = STANDARD_AIR.with_(mobility_ref=rng.uniform(1.8e-4, 2.2e-4),
                                     e_spark_ref=rng.uniform(0.7e6, 1.4e6),
                                     peek_m=rng.uniform(0.8, 1.0),
                                     temperature_K=rng.uniform(288, 303),
                                     pressure_Pa=rng.uniform(99e3, 103e3))
            k_scale = float(np.exp(rng.uniform(np.log(0.5), np.log(2.0))))
            geo = copy.copy(geo0)
            geo.onset = geo0.onset * corona.peek_field_wire(dev.stages[0].emitter_wire, air) / peek0
            m = metrics(dev, air, k_scale, geo)
            out.append({"n": n_st, "sample": i, **m})
    df = pd.DataFrame(out)
    w = df.pivot(index="sample", columns="n")
    paired = {"P(TP 1st > 2st)": float((w.TP_mNW[1] > w.TP_mNW[2]).mean()),
              "P(TP 2st > 3st)": float((w.TP_mNW[2] > w.TP_mNW[3]).mean()),
              "P(thrust 2st > 1st)": float((w.thrust_mN[2] > w.thrust_mN[1]).mean()),
              "P(thrust 3st > 2st)": float((w.thrust_mN[3] > w.thrust_mN[2]).mean())}
    pd.Series(paired).to_csv(DATA / "phase_g_monte_carlo_rankings.csv")
    print(paired)
    df.to_csv(DATA / "phase_g_monte_carlo.csv", index=False)
    summ = df.drop(columns="sample").groupby("n").quantile([0.05, 0.5, 0.95]).unstack()
    summ.to_csv(DATA / "phase_g_monte_carlo_summary.csv")
    fig, axs = plt.subplots(1, 3, figsize=(13, 4))
    for ax, (col, lab) in zip(axs, [("thrust_mN", "Thrust (mN)"), ("TP_mNW", "Thrust/power (mN/W)"),
                                    ("Q_cfm", "Flow (CFM)")]):
        data = [df[df.n == n][col].dropna() for n in (1, 2, 3)]
        parts = ax.violinplot(data, positions=[1, 2, 3], showmedians=True, quantiles=[[0.05, 0.95]] * 3)
        for pc, n in zip(parts["bodies"], (1, 2, 3)):
            pc.set_facecolor(COLORS[f"{n}-stage"]); pc.set_alpha(0.6)
        ax.set_xticks([1, 2, 3]); ax.set_xticklabels(["1 stage", "2 stages", "3 stages"]); ax.set_ylabel(lab)
    fig.suptitle(f"Monte-Carlo spread at max safe voltage ({n_samples} samples per design; lines = median, 5th/95th pct)",
                 fontweight="bold")
    fig.tight_layout()
    save(fig, "G2_monte_carlo_uncertainty", assumptions=A + " Sampled: mobility 1.8-2.2e-4, sparkover 0.7-1.4 MV/m, "
         "Peek m 0.8-1, current factor 0.5-2 (log-uniform), 15-30 C, 99-103 kPa. Uniform priors are ASSUMED.")
    return summ


# ---------------------------------------------------------------- Pareto search
def pareto_case(args):
    n, g, ratio, dia, kind = args
    kw = {"emitter_radius": dia / 2, "collector_radius": dia / 2, "collector_kind": kind}
    if kind == "tube":
        kw["collector_len"] = 0.010
    dev = make(n=n, gap=g, spacing=g * ratio, **kw)
    geo = D.analyse_geometry(dev, n_lines=40)
    vmax = min(ref.V_SUPPLY_MAX, ref.SPARK_MARGIN * D.spark_limits(dev))
    rows = []
    if vmax <= geo.onset.min():
        return rows
    for V in np.linspace(geo.onset.min() * 1.05, vmax, 10):
        r = D.evaluate(geo, V)
        rows.append({"n": n, "gap_mm": g * 1e3, "s_over_d": ratio, "dia_mm": dia * 1e3, "collector": kind,
                     "V_kV": V / 1e3, "P_W": r["P"], "thrust_mN": r["thrust"] * 1e3, "TP_mNW": r["T_per_P"] * 1e3,
                     "Q_cfm": r["Q"] * 2118.88, "length_mm": dev.length() * 1e3})
    return rows


def pareto_mask(x, y):
    """Points not dominated when maximising both x and y."""
    order = np.argsort(-x)
    best_y, mask = -np.inf, np.zeros(len(x), bool)
    for i in order:
        if y[i] > best_y:
            mask[i] = True; best_y = y[i]
    return mask


def pareto():
    jobs = []
    for n in (1, 2, 3):
        for g, ratio, dia, kind in itertools.product((0.015, 0.020, 0.025, 0.030, 0.035), (1.5, 2.0, 3.0),
                                                     (0.024, 0.030, 0.036), ("torus", "tube")):
            if n == 1 and ratio != 2.0:
                continue
            jobs.append((n, g, ratio, dia, kind))
    with ProcessPoolExecutor(6) as ex:
        df = pd.DataFrame([r for rows in ex.map(pareto_case, jobs) for r in rows])
    df = df[df.thrust_mN > 0]
    df.to_csv(DATA / "phase_g_pareto_designs.csv", index=False)
    mask = pareto_mask(df.thrust_mN.values, df.TP_mNW.values)
    front = df[mask].sort_values("thrust_mN")
    front.to_csv(DATA / "phase_g_pareto_front.csv", index=False)
    fig, axs = plt.subplots(1, 2, figsize=(13, 5))
    for n in (1, 2, 3):
        s = df[df.n == n]
        axs[0].scatter(s.thrust_mN, s.TP_mNW, s=6, alpha=0.35, color=COLORS[f"{n}-stage"], label=f"{n}-stage designs")
    axs[0].plot(front.thrust_mN, front.TP_mNW, "k-", lw=1.5, label="Pareto front")
    axs[0].set_xlabel("Net thrust (mN)"); axs[0].set_ylabel("Thrust/power (mN/W)")
    axs[0].set_title("Thrust vs efficiency trade-off"); axs[0].legend(fontsize=8, markerscale=3)
    for n in (1, 2, 3):
        s = df[df.n == n]
        axs[1].scatter(s.length_mm, s.Q_cfm, s=6, alpha=0.35, color=COLORS[f"{n}-stage"], label=f"{n}-stage")
    mask2 = pareto_mask(-df.length_mm.values, df.Q_cfm.values)
    f2 = df[mask2].sort_values("length_mm")
    axs[1].step(f2.length_mm, f2.Q_cfm, "k-", where="post", lw=1.5, label="Pareto front (short + high flow)")
    axs[1].set_xlabel("Device length (mm)"); axs[1].set_ylabel("Volumetric flow (CFM)")
    axs[1].set_title("Flow vs device length"); axs[1].legend(fontsize=8, markerscale=3)
    fig.suptitle(f"Design-space search: {len(jobs)} geometries x 10 voltages", fontweight="bold")
    fig.tight_layout()
    save(fig, "G3_pareto_fronts", assumptions=A + " Gaps 15-35 mm, s/d 1.5-3, ring 24-36 mm, torus or 10 mm tube "
         "collectors, voltage onset..max safe.")
    pd.set_option("display.width", 200)
    print(front[["n", "gap_mm", "s_over_d", "dia_mm", "collector", "V_kV", "P_W", "thrust_mN", "TP_mNW", "Q_cfm",
                 "length_mm"]].round(2).to_string())
    return front


if __name__ == "__main__":
    parts = sys.argv[1:] or ["sens", "mc", "pareto"]
    if "sens" in parts:
        df, base = sensitivity(); print(base); print(df.round(3).to_string())
    if "mc" in parts:
        print(monte_carlo().round(2).T.to_string())
    if "pareto" in parts:
        pareto()
