"""Phase D: electrode materials.

Two kinds of output, kept visibly separate:
  * analytical calculation: resistive loss in the electrodes, electrode mass;
  * qualitative engineering assessment: oxidation, erosion, manufacturability, cost,
    stability. These are judgements with written reasons in docs/results/materials.md,
    NOT measurements, and they are never turned into thrust or efficiency numbers.

Run: .venv/bin/python simulations/phase_d_materials.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ehd.constants import CONDUCTIVITY  # noqa: E402
from ehd.plotting import DATA, save  # noqa: E402

DENSITY = {"copper": 8960, "aluminium": 2700, "stainless_304": 8000, "tungsten": 19300}  # kg/m^3, handbook

COMBOS = {  # label: (emitter, collector)
    "A": ("Copper ring/wire", "Smooth copper ring"),
    "B": ("Stainless needles", "Smooth copper ring"),
    "C": ("Sharpened copper needles", "Smooth copper ring"),
    "D": ("Serrated copper ring", "Smooth copper ring"),
    "E": ("Stainless needles", "Copper mesh"),
    "F": ("Copper needles", "Copper mesh"),
    "G": ("Stainless needles", "Aluminium ring"),
    "H": ("Copper ring/wire", "Aluminium ring"),
    "I": ("Stainless needles", "Stainless ring"),
    "J1": ("Tungsten wire ring", "Aluminium tube"),
    "J2": ("Stainless needles", "Aluminium tube"),
}

# Qualitative 1 (poor) - 5 (good) scores. Reasons for every score: docs/results/materials.md.
EMITTER = {
    "Copper ring/wire":         {"oxidation": 2, "erosion": 2, "manufacture": 5, "cost": 5, "stability": 3},
    "Stainless needles":        {"oxidation": 4, "erosion": 4, "manufacture": 4, "cost": 5, "stability": 4},
    "Sharpened copper needles": {"oxidation": 2, "erosion": 1, "manufacture": 2, "cost": 4, "stability": 2},
    "Copper needles":           {"oxidation": 2, "erosion": 2, "manufacture": 3, "cost": 4, "stability": 3},
    "Serrated copper ring":     {"oxidation": 2, "erosion": 2, "manufacture": 2, "cost": 4, "stability": 2},
    "Tungsten wire ring":       {"oxidation": 3, "erosion": 5, "manufacture": 3, "cost": 3, "stability": 4},
}
COLLECTOR = {
    "Smooth copper ring": {"oxidation": 3, "erosion": 4, "manufacture": 4, "cost": 4, "stability": 4},
    "Copper mesh":        {"oxidation": 2, "erosion": 3, "manufacture": 3, "cost": 4, "stability": 3},
    "Aluminium ring":     {"oxidation": 4, "erosion": 4, "manufacture": 4, "cost": 5, "stability": 4},
    "Stainless ring":     {"oxidation": 5, "erosion": 5, "manufacture": 3, "cost": 4, "stability": 4},
    "Aluminium tube":     {"oxidation": 4, "erosion": 4, "manufacture": 5, "cost": 5, "stability": 4},
}
CRITERIA = ["oxidation", "erosion", "manufacture", "cost", "stability"]


def resistive_loss():
    """I^2 R in a 30 mm ring made of 1 mm wire carrying the full corona current."""
    L = np.pi * 0.030; area = np.pi * (0.5e-3) ** 2
    rows = []
    for m, sigma in CONDUCTIVITY.items():
        R = L / (sigma * area)
        for I in (100e-6, 1e-3):
            rows.append({"material": m, "R_ohm": R, "I_A": I, "loss_W": I**2 * R,
                         "fraction_of_3W": I**2 * R / 3.0})
    return pd.DataFrame(rows)


def masses():
    """Electrode mass per stage: emitter = 1 mm wire ring, collector = 4 mm tube torus or 10 mm x 0.5 mm tube."""
    R = 0.015
    vol = {"emitter wire ring": 2 * np.pi**2 * R * (0.5e-3) ** 2,
           "collector torus 4 mm (solid)": 2 * np.pi**2 * R * (2e-3) ** 2,
           "collector tube 10 mm x 0.5 mm wall": 2 * np.pi * R * 0.010 * 0.5e-3}
    return pd.DataFrame([{"part": p, "material": m, "mass_g": v * DENSITY[m] * 1e3}
                         for p, v in vol.items() for m in DENSITY])


def plot_scores():
    rows = []
    for k, (e, c) in COMBOS.items():
        se, sc = EMITTER[e], COLLECTOR[c]
        rows.append({"combo": k, "emitter": e, "collector": c,
                     **{f"E_{x}": se[x] for x in CRITERIA}, **{f"C_{x}": sc[x] for x in CRITERIA}})
    df = pd.DataFrame(rows)
    df.to_csv(DATA / "phase_d_material_scores_QUALITATIVE.csv", index=False)
    cols = [f"E_{x}" for x in CRITERIA] + [f"C_{x}" for x in CRITERIA]
    fig, ax = plt.subplots(figsize=(12, 5.5))
    im = ax.imshow(df[cols].values, cmap="RdYlGn", vmin=1, vmax=5, aspect="auto")
    ax.set_xticks(range(len(cols)))
    ax.set_xticklabels([("Emitter\n" if c.startswith("E") else "Collector\n") + c[2:] for c in cols], fontsize=8)
    ax.set_yticks(range(len(df)))
    ax.set_yticklabels([f"{k}: {e} + {c}" for k, e, c in zip(df.combo, df.emitter, df.collector)], fontsize=8)
    for (i, j), v in np.ndenumerate(df[cols].values):
        ax.text(j, i, str(v), ha="center", va="center", fontsize=8)
    ax.axvline(4.5, color="k", lw=1.5); ax.grid(False)
    cb = fig.colorbar(im, ax=ax, shrink=0.8); cb.set_label("1 = poor ... 5 = good (judgement)")
    ax.set_title("Material combinations: qualitative durability and manufacturability ratings")
    save(fig, "D1_material_combinations_qualitative", source="qual",
         assumptions="Scores are engineering judgement with written reasons (docs/results/materials.md). They are NOT "
                     "measurements and imply NO thrust or efficiency difference between materials.")
    return df


def plot_mass(mdf):
    fig, ax = plt.subplots(figsize=(9, 4))
    parts = mdf.part.unique(); mats = list(DENSITY)
    cols = {"copper": "#b45309", "aluminium": "#9ca3af", "stainless_304": "#475569", "tungsten": "#1f2937"}
    for j, m in enumerate(mats):
        s = mdf[mdf.material == m]
        ax.bar(np.arange(len(parts)) + (j - 1.5) * 0.2, s.mass_g, 0.2, color=cols[m], label=m)
    ax.set_xticks(range(len(parts))); ax.set_xticklabels(parts, fontsize=9)
    ax.set_ylabel("Mass per electrode (g)"); ax.set_title("Electrode mass by material (30 mm ring)"); ax.legend(fontsize=8)
    save(fig, "D2_electrode_mass", source="analytic",
         assumptions="Handbook densities: Cu 8960, Al 2700, SS304 8000, W 19300 kg/m3. Solid torus vs thin tube.")


if __name__ == "__main__":
    r = resistive_loss(); r.to_csv(DATA / "phase_d_resistive_loss.csv", index=False)
    m = masses(); m.to_csv(DATA / "phase_d_electrode_mass.csv", index=False)
    plot_scores(); plot_mass(m)
    pd.set_option("display.width", 200)
    print(r.to_string()); print(m.round(2).to_string())
