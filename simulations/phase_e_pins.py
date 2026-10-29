"""Phase E: discrete-pin emitters: pin count, shielding, orientation, sharpness (3-D CSM).

Outputs: data/phase_e_*.csv, charts/E*.png|svg.
Absolute currents from the pin model use a different closure (Sigmond point-plane,
capped by the ring Townsend current) from the ring model in device.py, so pin results
are reported mainly relative to a reference pin ring and are not compared numerically
with ring-emitter results.
Run: .venv/bin/python simulations/phase_e_pins.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ehd import corona, pins  # noqa: E402
from ehd.plotting import COLORS, DATA, save  # noqa: E402
from ehd.reference import ASSUMPTIONS  # noqa: E402

V = 20e3
A = ASSUMPTIONS + f" Pins: 6 mm long, 0.05 mm tip radius, 30 mm ring, gap 25 mm (ring->collector), V={V/1e3:.0f} kV."
ORIENT = ["axial", "angled_in", "angled_out", "radial_out", "radial_in"]
OCOL = dict(zip(ORIENT, ["#2563eb", "#059669", "#d97706", "#dc2626", "#7c3aed"]))


def row(pr, **meta):
    r = pins.performance(pr, V)
    return {**meta, "n_pins": pr.n_pins, "orientation": pr.orientation, "tip_mm": pr.tip_radius * 1e3,
            "E_tip_per_V": r["E_tip_per_V"], "V0_kV": r["V0"] / 1e3, "I_uA": r["I"] * 1e6,
            "I_pins_uA": r["I_pins_uncapped"] * 1e6, "I_cap_uA": r["I_ring_cap"] * 1e6,
            "T_mN": r["T_ehd"] * 1e3, "P_W": r["P"], "TP_mNW": r["T_ehd"] / r["P"] * 1e3 if r["P"] else np.nan,
            "lever_mm": r["lever"] * 1e3, "d_tc_mm": r["d_tip_collector"] * 1e3, "csm_residual": r["residual"]}


def count_and_orientation():
    rows = [row(pins.PinRing(n_pins=n, orientation=o), study="count")
            for o in ORIENT for n in (1, 2, 4, 6, 8, 12, 16, 24, 32, 48, 64)]
    df = pd.DataFrame(rows)
    df.to_csv(DATA / "phase_e_pin_count_orientation.csv", index=False)
    fig, axs = plt.subplots(1, 3, figsize=(14, 4.3))
    for o in ORIENT:
        s = df[df.orientation == o]
        e1 = s[s.n_pins == 1].E_tip_per_V.iloc[0]
        axs[0].plot(s.n_pins, s.E_tip_per_V / e1, "o-", color=OCOL[o], label=o)
        axs[1].plot(s.n_pins, s.V0_kV, "o-", color=OCOL[o], label=o)
        t_ref = df[(df.orientation == "axial") & (df.n_pins == 16)].T_mN.iloc[0]
        axs[2].plot(s.n_pins, s.T_mN / t_ref, "o-", color=OCOL[o], label=o)
    axs[0].set_ylabel("Tip field / single-pin tip field"); axs[0].set_title("Mutual shielding")
    axs[1].set_ylabel("Corona onset voltage (kV)"); axs[1].set_title("Onset vs pin count")
    axs[2].set_ylabel(f"Relative thrust at {V/1e3:.0f} kV (16 axial pins = 1)")
    axs[2].set_title("Thrust vs pin count")
    for ax in axs:
        ax.set_xscale("log", base=2); ax.set_xlabel("Number of pins on the ring")
        ax.set_xticks([1, 2, 4, 8, 16, 32, 64]); ax.get_xaxis().set_major_formatter(plt.ScalarFormatter())
    axs[0].legend(fontsize=8)
    fig.tight_layout()
    save(fig, "E1_pin_count_shielding", assumptions=A + " Thrust shown relative: the pin current closure is a "
         "HEURISTIC, so read trends, not absolute values.")

    s16 = df[df.n_pins == 16].set_index("orientation").loc[ORIENT]
    ref = s16.loc["axial"]
    metrics = [("E_tip_per_V", "tip field"), ("I_uA", "current"), ("T_mN", "thrust"), ("TP_mNW", "thrust/power")]
    fig, ax = plt.subplots(figsize=(10, 4.3))
    x = np.arange(len(metrics))
    for j, o in enumerate(ORIENT):
        ax.bar(x + (j - 2) * 0.16, [s16.loc[o, m] / ref[m] for m, _ in metrics], 0.16, color=OCOL[o], label=o)
    ax.axhline(1, color="k", lw=0.7)
    ax.set_xticks(x); ax.set_xticklabels([lab for _, lab in metrics])
    ax.set_ylabel("Relative to 16 axial pins"); ax.set_title("Pin orientation (16 pins)")
    ax.legend(fontsize=8, ncol=5, loc="upper center")
    for j, o in enumerate(ORIENT):
        ax.text(3 + (j - 2) * 0.16, 0.05, f"{s16.loc[o, 'V0_kV']:.1f} kV", rotation=90, ha="center", fontsize=7,
                color="w")
    save(fig, "E2_pin_orientation", assumptions=A + " Numbers inside the last bar group: onset voltage. "
         "axial = pins point downstream at the collector; radial_out/in = in the ring plane.")
    return df


def sharpness():
    rows = []
    for rt in (10, 20, 35, 50, 75, 100, 150, 250, 400):
        for n in (1, 16):
            rows.append(row(pins.PinRing(n_pins=n, tip_radius=rt * 1e-6), study="tip"))
    df = pd.DataFrame(rows)
    gap = pins.PinRing().tip_to_collector()
    df["V0_hyperboloid_kV"] = [corona.onset_voltage_needle(t * 1e-3, gap) / 1e3 for t in df.tip_mm]
    df["E_peek_kV_per_mm"] = [corona.peek_field_sphere(t * 1e-3) / 1e6 for t in df.tip_mm]
    df.to_csv(DATA / "phase_e_tip_radius.csv", index=False)
    fig, axs = plt.subplots(1, 2, figsize=(12, 4.3))
    for n, col in ((1, COLORS["1-stage"]), (16, COLORS["2-stage"])):
        s = df[df.n_pins == n]
        axs[0].plot(s.tip_mm, s.V0_kV, "o-", color=col, label=f"3-D CSM, {n} pin(s)")
        t_ref = df[(df.n_pins == 16) & np.isclose(df.tip_mm, 0.05)].T_mN.iloc[0]
        axs[1].plot(s.tip_mm, s.T_mN / t_ref, "o-", color=col, label=f"{n} pin(s)")
    s = df[df.n_pins == 1]
    axs[0].plot(s.tip_mm, s.V0_hyperboloid_kV, "k--", label="Hyperboloid point-plane formula (1 pin)")
    axs[0].set_ylabel("Corona onset voltage (kV)"); axs[0].set_title("Tip sharpness vs onset")
    axs[1].set_ylabel(f"Relative thrust at {V/1e3:.0f} kV (16 pins, 0.05 mm = 1)"); axs[1].set_title("Tip sharpness vs thrust")
    for ax in axs:
        ax.set_xscale("log"); ax.set_xlabel("Tip radius of curvature (mm)"); ax.legend(fontsize=8)
    ax2 = axs[0].twinx(); ax2.plot(s.tip_mm, s.E_peek_kV_per_mm, ":", color=COLORS["efficiency"]); ax2.grid(False)
    ax2.set_ylabel("Peek onset field at tip (kV/mm)", color=COLORS["efficiency"])
    fig.tight_layout()
    save(fig, "E3_tip_sharpness", assumptions=A + " Peek sphere law, m=1. Real tips blunt with use (erosion), "
         "raising onset over time.")
    return df


if __name__ == "__main__":
    c = count_and_orientation()
    t = sharpness()
    pd.set_option("display.width", 200)
    print(c[c.n_pins.isin([1, 8, 16, 32, 64])][["orientation", "n_pins", "E_tip_per_V", "V0_kV", "I_uA",
                                                   "I_pins_uA", "I_cap_uA", "T_mN", "TP_mNW", "csm_residual"]].round(3))
    print(t[["n_pins", "tip_mm", "V0_kV", "V0_hyperboloid_kV", "T_mN"]].round(2))
