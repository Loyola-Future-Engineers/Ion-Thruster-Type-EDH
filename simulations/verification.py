"""Numerical verification: convergence of the solvers and qualitative trend checks.

Outputs: charts/V1_numerical_convergence.png|svg, data/verification_*.csv,
charts/interactive_pareto.html (Plotly, if phase G has been run).
Run: .venv/bin/python simulations/verification.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ehd import csm, device as D, reference as ref  # noqa: E402
from ehd.constants import EPS0  # noqa: E402
from ehd.plotting import CHARTS, COLORS, DATA, save  # noqa: E402


def torus_convergence():
    R, a = 0.015, 1e-4
    exact = 4 * np.pi**2 * EPS0 * R / np.log(8 * R / a)
    rows = []
    for n in (4, 8, 12, 16, 24, 32, 48):
        s = csm.solve([csm.Electrode.torus("t", R, 0, a, 1.0)], n)
        rows.append({"n_per": n, "rel_err": abs(s.charge_on(0) / exact - 1), "residual": s.residual})
    return pd.DataFrame(rows)


def device_convergence():
    dev = ref.device(2, gaps=[0.025] * 2, spacings=[0.05])
    rows = []
    for n_lines in (16, 24, 32, 48, 64, 96):
        geo = D.analyse_geometry(dev, n_lines=n_lines, n_per=40)
        r = D.evaluate(geo, 19e3)
        rows.append({"kind": "n_lines", "value": n_lines, "thrust_mN": r["thrust"] * 1e3,
                     "backflow": D.stage_current_split(geo, 1)["upstream"], "V0_kV": geo.onset[0] / 1e3})
    for n_per in (16, 24, 32, 40, 56, 72):
        geo = D.analyse_geometry(dev, n_lines=48, n_per=n_per)
        r = D.evaluate(geo, 19e3)
        rows.append({"kind": "n_per", "value": n_per, "thrust_mN": r["thrust"] * 1e3,
                     "backflow": D.stage_current_split(geo, 1)["upstream"], "V0_kV": geo.onset[0] / 1e3})
    return pd.DataFrame(rows)


def trend_checks():
    """Masuyama & Barrett (2013) abstract: increasing gap -> higher onset, less thrust per volt,
    more thrust per current, more thrust per power (single stage, same voltage)."""
    out = []
    for g in (0.02, 0.03, 0.04):
        dev = ref.device(1, gaps=[g])
        geo = D.analyse_geometry(dev, n_lines=48)
        r = D.evaluate(geo, 20e3, iterate_flow=False)
        cur = {"gap_mm": g * 1e3, "onset_kV": geo.onset[0] / 1e3, "T_per_V": r["F_ehd"] / 20e3,
               "T_per_I": r["F_ehd"] / r["I"], "T_per_P": r["F_ehd"] / r["P"]}
        out.append(cur)
    df = pd.DataFrame(out)
    checks = {"onset rises with gap": df.onset_kV.is_monotonic_increasing,
              "thrust per volt falls with gap": df.T_per_V.is_monotonic_decreasing,
              "thrust per current rises with gap": df.T_per_I.is_monotonic_increasing,
              "thrust per power rises with gap": df.T_per_P.is_monotonic_increasing}
    return df, checks


def interactive_pareto():
    p = DATA / "phase_g_pareto_designs.csv"
    if not p.exists():
        return
    import plotly.express as px
    df = pd.read_csv(p)
    df["stages"] = df.n.astype(str) + "-stage"
    fig = px.scatter(df, x="thrust_mN", y="TP_mNW", color="stages", symbol="collector",
                     hover_data=["gap_mm", "s_over_d", "dia_mm", "V_kV", "P_W", "Q_cfm", "length_mm"],
                     color_discrete_map={f"{n}-stage": COLORS[f"{n}-stage"] for n in (1, 2, 3)},
                     labels={"thrust_mN": "Net thrust (mN)", "TP_mNW": "Thrust/power (mN/W)"},
                     title="EHD design space (numerical simulation, unvalidated reduced-order model)")
    fig.write_html(CHARTS / "interactive_pareto.html", include_plotlyjs="cdn")


if __name__ == "__main__":
    tc = torus_convergence(); dc = device_convergence(); td, checks = trend_checks()
    tc.to_csv(DATA / "verification_torus_convergence.csv", index=False)
    dc.to_csv(DATA / "verification_device_convergence.csv", index=False)
    td.to_csv(DATA / "verification_trend_checks.csv", index=False)
    fig, axs = plt.subplots(1, 3, figsize=(14, 4))
    axs[0].semilogy(tc.n_per, tc.rel_err, "o-", color=COLORS["thrust"], label="capacitance error vs thin-ring formula")
    axs[0].semilogy(tc.n_per, tc.residual, "s--", color=COLORS["power"], label="max boundary residual (V per V)")
    axs[0].set_xlabel("ring charges per electrode"); axs[0].set_title("CSM convergence: isolated torus")
    axs[0].legend(fontsize=8)
    for ax, kind, lab in [(axs[1], "n_lines", "traced ion paths per emitter"), (axs[2], "n_per", "ring charges per electrode")]:
        s = dc[dc.kind == kind]
        ax.plot(s.value, s.thrust_mN, "o-", color=COLORS["thrust"], label="thrust (mN)")
        ax2 = ax.twinx(); ax2.plot(s.value, s.backflow * 100, "s--", color=COLORS["efficiency"]); ax2.grid(False)
        ax2.set_ylabel("stage-2 back-flow (%)", color=COLORS["efficiency"])
        ax.set_xlabel(lab); ax.set_ylabel("thrust (mN)"); ax.set_title(f"2-stage reference vs {kind}")
    fig.tight_layout()
    save(fig, "V1_numerical_convergence", assumptions="2-stage reference d=25 mm, s=50 mm at 19 kV. "
         "Verification of numerics only: says nothing about physical accuracy.")
    interactive_pareto()
    pd.set_option("display.width", 200)
    print(tc.to_string()); print(dc.round(4).to_string()); print(td.round(6).to_string()); print(checks)
