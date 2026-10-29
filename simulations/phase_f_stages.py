"""Phase F: one vs two vs three stages under equal stage geometry, equal length and equal power.

Outputs: data/phase_f_*.csv, charts/F*.png|svg.
Run: .venv/bin/python simulations/phase_f_stages.py
"""
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ehd import device as D, reference as ref  # noqa: E402
from ehd.plotting import COLORS, DATA, save  # noqa: E402

A = ref.ASSUMPTIONS
CASES = {
    # name: (n, gap mm, spacing mm)
    "equal-geometry": [(1, 25, 0), (2, 25, 50), (3, 25, 50)],
    "equal-length (100 mm, s=1.5d)": [(1, 100, 0), (2, 100 / 3.5, 1.5 * 100 / 3.5), (3, 100 / 6, 1.5 * 100 / 6)],
    "equal-geometry, tube collectors": [(1, 25, 0), (2, 25, 50), (3, 25, 50)],
}
KW = {"equal-geometry, tube collectors": {"collector_kind": "tube", "collector_len": 0.010}}


def curve(args):
    case, n, g, s = args
    dev = ref.device(n, gaps=[g / 1e3] * n, spacings=[s / 1e3] * (n - 1), **KW.get(case, {}))
    geo = D.analyse_geometry(dev, n_lines=48)
    v_max = ref.operating_voltage(dev)
    rows = []
    for V in np.linspace(geo.onset.min() * 1.02, v_max, 24):
        r = D.evaluate(geo, V)
        rows.append({"case": case, "n": n, "gap_mm": g, "spacing_mm": s, "length_mm": dev.length() * 1e3,
                     "V_kV": V / 1e3, "P_W": r["P"], "thrust_mN": r["thrust"] * 1e3, "u_ms": r["u"],
                     "Q_cfm": r["Q"] * 2118.88, "TP_mNW": r["T_per_P"] * 1e3, "K": r["K"],
                     "is_max": bool(np.isclose(V, v_max))})
    return rows


def main():
    jobs = [(c, n, g, s) for c, lst in CASES.items() for n, g, s in lst]
    with ProcessPoolExecutor(6) as ex:
        df = pd.DataFrame([r for rows in ex.map(curve, jobs) for r in rows])
    df.to_csv(DATA / "phase_f_stage_curves.csv", index=False)

    fig, axs = plt.subplots(2, 3, figsize=(16, 8))
    for col, case in enumerate(CASES):
        for n in (1, 2, 3):
            s = df[(df.case == case) & (df.n == n)]
            lab = f"{n}-stage (d={s.gap_mm.iloc[0]:.0f} mm, L={s.length_mm.iloc[0]:.0f} mm)"
            axs[0, col].plot(s.P_W, s.thrust_mN, "-", color=COLORS[f"{n}-stage"], lw=2, label=lab)
            axs[0, col].plot(s.P_W.iloc[-1], s.thrust_mN.iloc[-1], "o", color=COLORS[f"{n}-stage"])
            axs[1, col].plot(s.P_W, s.TP_mNW, "-", color=COLORS[f"{n}-stage"], lw=2, label=lab)
        axs[0, col].set_title(case); axs[0, col].legend(fontsize=8)
        axs[0, col].set_ylabel("Net thrust (mN)"); axs[1, col].set_ylabel("Thrust/power (mN/W)")
        for ax in axs[:, col]:
            ax.set_xlabel("Electrical power (W)"); ax.set_xlim(0, None)
    fig.suptitle("Stage count: thrust and efficiency vs input power (voltage swept from onset to max safe; dot = max)",
                 fontweight="bold")
    fig.tight_layout()
    save(fig, "F1_stage_count_thrust_vs_power", assumptions=A + " Equal-geometry spacing s=2d (Phase B rule).")

    # equal-power read-out
    out = []
    for case in CASES:
        for n in (1, 2, 3):
            s = df[(df.case == case) & (df.n == n)].sort_values("P_W")
            for P in (0.5, 1.0, 2.0, 4.0):
                if s.P_W.min() <= P <= s.P_W.max():
                    out.append({"case": case, "n": n, "P_W": P, **{k: np.interp(P, s.P_W, s[k])
                                for k in ("thrust_mN", "Q_cfm", "u_ms", "TP_mNW", "V_kV")}})
            m = s[s.is_max].iloc[0]
            out.append({"case": case, "n": n, "P_W": "max", "thrust_mN": m.thrust_mN, "Q_cfm": m.Q_cfm,
                        "u_ms": m.u_ms, "TP_mNW": m.TP_mNW, "V_kV": m.V_kV, "P_at_max_W": m.P_W,
                        "length_mm": m.length_mm})
    od = pd.DataFrame(out)
    od.to_csv(DATA / "phase_f_equal_power_table.csv", index=False)

    fig, axs = plt.subplots(1, 4, figsize=(15, 4))
    eg = od[(od.case == "equal-geometry")]
    for ax, (col, lab) in zip(axs, [("thrust_mN", "Thrust (mN)"), ("Q_cfm", "Flow (CFM)"),
                                    ("TP_mNW", "Thrust/power (mN/W)"), ("V_kV", "Voltage (kV)")]):
        for j, n in enumerate((1, 2, 3)):
            s = eg[(eg.n == n) & (eg.P_W != "max")]
            ax.bar(np.arange(len(s)) + (j - 1) * 0.27, s[col], 0.27, color=COLORS[f"{n}-stage"], label=f"{n}-stage")
        ax.set_xticks(range(4)); ax.set_xticklabels(["0.5 W", "1 W", "2 W", "4 W"]); ax.set_title(lab)
    axs[0].legend(fontsize=8)
    fig.suptitle("Equal electrical power, identical stages (d=25 mm, s=50 mm); missing bars = not reachable "
                 "within the safe voltage", fontweight="bold", fontsize=11)
    fig.tight_layout()
    save(fig, "F2_stage_count_equal_power", assumptions=A)

    fig, ax = plt.subplots(figsize=(7, 4.2))
    mx = od[(od.P_W == "max") & (od.case == "equal-geometry")]
    ax.bar(mx.n - 0.2, mx.P_at_max_W, 0.4, color=COLORS["power"], label="Power at max safe V (W)")
    ax.bar(mx.n + 0.2, mx.thrust_mN, 0.4, color=COLORS["thrust"], label="Thrust at max safe V (mN)")
    for n, tp in zip(mx.n, mx.TP_mNW):
        ax.text(n, 0.3, f"{tp:.1f} mN/W", ha="center", fontsize=8, color="w", fontweight="bold")
    ax.set_xticks([1, 2, 3]); ax.set_xlabel("Number of stages"); ax.set_title("Stage count vs power (identical stages)")
    ax.legend(fontsize=8)
    save(fig, "F3_stage_count_vs_power", assumptions=A)
    pd.set_option("display.width", 200)
    print(od.round(2).to_string())


if __name__ == "__main__":
    main()
