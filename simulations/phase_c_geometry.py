"""Phase C: ring diameters, collector shape and field visualisation (axisymmetric model).

Outputs: data/phase_c_*.csv, charts/C*.png|svg.
Run: .venv/bin/python simulations/phase_c_geometry.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ehd import device as D, reference as ref, study  # noqa: E402
from ehd.plotting import COLORS, DATA, save  # noqa: E402

A = ref.ASSUMPTIONS
GAP, S = 0.025, 0.050    # stage gap and inter-stage spacing used here (s = 2d, per Phase B)


def diameter_sweeps():
    rows = []
    # collector diameter with emitter fixed at 30 mm
    for dc in [20, 24, 27, 30, 33, 36]:
        for n in (1, 2):
            dev = ref.device(n, gaps=[GAP] * n, spacings=[S] * (n - 1), collector_radius=dc / 2e3)
            rows.append(({"study": "collector_dia", "De_mm": 30, "Dc_mm": dc, "n": n}, dev))
    # emitter diameter with collector equal to emitter
    for de in [16, 20, 24, 28, 32, 36]:
        dev = ref.device(1, gaps=[GAP], emitter_radius=de / 2e3, collector_radius=de / 2e3)
        rows.append(({"study": "equal_dia", "De_mm": de, "Dc_mm": de, "n": 1}, dev))
    # diameter progression across two stages
    for name, (d1, d2) in {"constant": (30, 30), "increasing": (24, 34), "decreasing": (34, 24)}.items():
        dev = ref.device(2, gaps=[GAP] * 2, spacings=[S])
        for st, dd in zip(dev.stages, (d1, d2)):
            st.emitter_radius = st.collector_radius = dd / 2e3
        rows.append(({"study": f"progression_{name}", "De_mm": f"{d1}->{d2}", "Dc_mm": f"{d1}->{d2}", "n": 2}, dev))
    res = study.run_many([d for _, d in rows])
    df = pd.DataFrame([{**m, **r} for (m, _), r in zip(rows, res)])
    df.to_csv(DATA / "phase_c_diameters.csv", index=False)
    return df


def collector_shapes():
    rows = []
    for minor in [0.5, 1.0, 2.0, 3.0, 4.0]:
        rows.append(({"study": "torus_minor", "shape": "torus", "minor_mm": minor},
                     ref.device(1, gaps=[GAP], collector_minor=minor / 1e3)))
    for kind, extra in [("torus", {}), ("flat", {}), ("tube", {"collector_len": 0.010}), ("mesh", {})]:
        for n in (1, 2):
            rows.append(({"study": "collector_kind", "shape": kind, "minor_mm": 2.0, "n": n},
                         ref.device(n, gaps=[GAP] * n, spacings=[S] * (n - 1), collector_kind=kind, **extra)))
    res = study.run_many([d for _, d in rows])
    df = pd.DataFrame([{**m, **r} for (m, _), r in zip(rows, res)])
    df.to_csv(DATA / "phase_c_collector_shapes.csv", index=False)
    return df


def plot_diameters(df):
    fig, axs = plt.subplots(1, 3, figsize=(14, 4.2))
    c = df[df.study == "collector_dia"]
    for n, col in ((1, COLORS["1-stage"]), (2, COLORS["2-stage"])):
        s = c[c.n == n]
        axs[0].plot(s.Dc_mm.astype(float) / 30, s.op_thrust_mN, "o-", color=col, label=f"{n}-stage, max safe V")
        axs[0].plot(s.Dc_mm.astype(float) / 30, s.eqP_thrust_mN, "s--", color=col, label=f"{n}-stage, 2 W")
        axs[1].plot(s.Dc_mm.astype(float) / 30, s.op_TP_mNW, "o-", color=col, label=f"{n}-stage")
    axs[0].set_xlabel("Collector / emitter diameter ratio (emitter 30 mm)"); axs[0].set_ylabel("Thrust (mN)")
    axs[0].set_title("Diameter ratio vs thrust"); axs[0].legend(fontsize=8)
    axs[1].set_xlabel("Collector / emitter diameter ratio"); axs[1].set_ylabel("Thrust/power (mN/W)")
    axs[1].set_title("Diameter ratio vs efficiency"); axs[1].legend(fontsize=8)
    e = df[df.study == "equal_dia"]
    ax = axs[2]
    ax.plot(e.De_mm.astype(float), e.op_thrust_mN, "o-", color=COLORS["thrust"], label="Thrust (mN)")
    ax.plot(e.De_mm.astype(float), e.op_Q_cfm, "s-", color=COLORS["flow"], label="Flow (CFM)")
    ax.set_xlabel("Emitter = collector diameter (mm), bore 40 mm"); ax.set_title("Ring diameter (1 stage)")
    ax2 = ax.twinx(); ax2.plot(e.De_mm.astype(float), e.op_P_W, "^--", color=COLORS["power"]); ax2.grid(False)
    ax2.set_ylabel("Power (W)", color=COLORS["power"]); ax.legend(fontsize=8, loc="upper left")
    fig.tight_layout()
    save(fig, "C1_ring_diameter_and_ratio", assumptions=A + f" Gap {GAP*1e3:.0f} mm, inter-stage {S*1e3:.0f} mm.")


def plot_shapes(df):
    fig, axs = plt.subplots(1, 2, figsize=(12, 4.3))
    t = df[df.study == "torus_minor"]
    ax = axs[0]
    ax.plot(t.minor_mm * 2, t.op_thrust_mN, "o-", color=COLORS["thrust"], label="Thrust (mN)")
    ax.plot(t.minor_mm * 2, t.op_TP_mNW, "s-", color=COLORS["efficiency"], label="Thrust/power (mN/W)")
    ax.plot(t.minor_mm * 2, t.K_loss, "^-", color=COLORS["power"], label="Loss coefficient K (-)")
    ax.set_xlabel("Collector tube diameter (mm)"); ax.set_title("Collector cross-section (torus)"); ax.legend(fontsize=8)
    k = df[df.study == "collector_kind"]
    shapes = ["torus", "flat", "tube", "mesh"]
    x = np.arange(len(shapes))
    for j, (n, col) in enumerate(((1, COLORS["1-stage"]), (2, COLORS["2-stage"]))):
        vals = [k[(k['shape'] == s) & (k.n == n)].op_thrust_mN.iloc[0] for s in shapes]
        axs[1].bar(x + (j - 0.5) * 0.38, vals, 0.38, color=col, label=f"{n}-stage thrust (mN)")
    kv = [k[(k['shape'] == s) & (k.n == 1)].K_loss.iloc[0] for s in shapes]
    for xi, kk in zip(x, kv):
        axs[1].text(xi, 0.3, f"K={kk:.2f}", ha="center", fontsize=8, color="w", fontweight="bold")
    axs[1].set_xticks(x); axs[1].set_xticklabels(["rounded ring\n(torus)", "flat washer", "tube 10 mm", "mesh disc\n(70% open)"])
    axs[1].set_ylabel("Thrust at max safe V (mN)"); axs[1].set_title("Collector type"); axs[1].legend(fontsize=8)
    fig.tight_layout()
    save(fig, "C2_collector_shape", assumptions=A + " Mesh modelled as a solid equipotential disc plus a screen loss "
         "K=(1-f)/f^2 with f=0.7 (ASSUMED).")


def field_map():
    dev = ref.device(2, gaps=[GAP] * 2, spacings=[S])
    geo = D.analyse_geometry(dev, n_lines=40)
    V = 20e3
    r = np.linspace(0.0005, 0.04, 220); z = np.linspace(-0.02, 0.12, 600)
    R, Z = np.meshgrid(r, z)
    er, ez = geo.sol.field(R.ravel(), Z.ravel())
    E = np.hypot(er, ez).reshape(R.shape) * V
    inside = np.zeros_like(E, bool)
    for el in geo.sol.electrodes:
        inside |= el.sdf(R, Z) <= 0
    E[inside] = np.nan
    fig, ax = plt.subplots(figsize=(11, 4.6))
    im = ax.pcolormesh(Z * 1e3, R * 1e3, np.log10(E), cmap="inferno", shading="auto", vmin=4.5, vmax=6.5)
    cb = fig.colorbar(im, ax=ax, pad=0.01); cb.set_label("log10 |E| (V/m), Laplace field at 20 kV")
    ax.contour(Z * 1e3, R * 1e3, np.log10(np.nan_to_num(E, nan=1e7)), levels=[np.log10(1e6)], colors="cyan",
               linewidths=0.8)
    for k, ln in enumerate(geo.lines):
        for i in range(len(ln["end"])):
            if ln["weight"][i] < 1e-3 or ln["end"][i] < 0:
                continue
            col = "#22c55e" if ln["end"][i] == 2 * k + 1 else ("#ef4444" if 0 <= ln["end"][i] < 2 * k else "#aaa")
            ax.plot([ln["start"][i, 1] * 1e3, ln["stop"][i, 1] * 1e3], [ln["start"][i, 0] * 1e3, ln["stop"][i, 0] * 1e3],
                    color=col, lw=0.5, alpha=0.8)
    for el in geo.sol.electrodes:
        pts, _, _ = el.contour(60)
        ax.fill(pts[:, 1] * 1e3, pts[:, 0] * 1e3, color="#60a5fa" if el.kind == "emitter" else "#d1d5db", zorder=5)
        ax.text(el.z_c * 1e3, el.r_c * 1e3 + 3.5, el.name, ha="center", color="w", fontsize=9, zorder=6)
    ax.set_xlim(z[0] * 1e3, z[-1] * 1e3); ax.set_ylim(0, r[-1] * 1e3)
    ax.set_xlabel("Axial position z (mm), flow left to right"); ax.set_ylabel("Radius r (mm)")
    ax.set_title("Electric field magnitude, 2-stage reference (d = 25 mm, s = 50 mm, 20 kV)")
    ax.text(0.01, 0.03, "ion-path chords: green = own collector, red = back-flow; cyan = 1 MV/m contour",
            transform=ax.transAxes, color="w", fontsize=7.5, zorder=7)
    save(fig, "C3_electric_field_map", assumptions=A + " Laplace field only: space charge would lower the field near "
         "the emitter and raise it near the collector.")


if __name__ == "__main__":
    parts = sys.argv[1:] or ["diameters", "shapes", "field"]
    if "diameters" in parts:
        plot_diameters(diameter_sweeps())
    if "shapes" in parts:
        plot_shapes(collector_shapes())
    if "field" in parts:
        field_map()
    print("done")
