"""Phase I: can a guard ring stop back-flow between stages? (space-charge solver)

A blunt ring (4 mm section, same 30 mm diameter) is placed a distance g upstream of the
stage-2 emitter and held at a fraction of the emitter voltage. A guard at the emitter's own
potential removes the field that pulls stage-2 ions backwards toward collector 1.

Outputs: data/phase_i_guard.csv, charts/I1_guard_electrode.png|svg.
Run: .venv/bin/python simulations/phase_i_guard.py
"""
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ehd import corona, csm, device as D, reference as ref, spacecharge as S  # noqa: E402
from ehd.constants import STANDARD_AIR  # noqa: E402
from ehd.plotting import COLORS, DATA, save  # noqa: E402

V = 19.47e3
GAP = 0.025
GUARD_MINOR = 0.002
A = ref.ASSUMPTIONS.replace("no space charge in ion paths", "self-consistent space charge") + \
    f" Two stages, d = 25 mm, {V/1e3:.1f} kV, insulating bore. Guard: 4 mm-section ring, 30 mm diameter."


def guard_ring(dev, g, frac):
    z_e2 = dev.stages[0].gap + dev.spacing[0]
    return csm.Electrode.torus("G", ref.EMITTER_RADIUS, z_e2 - g, GUARD_MINOR, frac, "guard", 0)


def guard_checks(dev, g, frac):
    """Laplace checks: does the guard start its own corona, and do its gaps spark?"""
    els = D.build_electrodes(dev, 1.0) + [guard_ring(dev, g, frac)]
    for e in els:
        if e.kind == "guard":
            e.potential = frac
    sol = csm.solve(els, 40)
    _, _, en, _ = csm.surface_field(sol, len(els) - 1, 96)
    e_guard = np.abs(en).max() * V
    e_onset = float(corona.peek_field_wire(GUARD_MINOR))
    clear_c1 = dev.spacing[0] - g - GUARD_MINOR - dev.stages[0].collector_minor
    clear_e2 = g - GUARD_MINOR - dev.stages[1].emitter_wire
    v_c1, v_e2 = frac * V, (1 - frac) * V
    return {"guard_peak_field_kV_per_mm": e_guard / 1e6, "guard_onset_field_kV_per_mm": e_onset / 1e6,
            "guard_corona_free": e_guard < e_onset,
            "field_guard_C1_kV_per_mm": v_c1 / clear_c1 / 1e6, "field_guard_E2_kV_per_mm": v_e2 / clear_e2 / 1e6}


def case(args):
    label, s, g, frac = args
    dev = ref.device(2, gaps=[GAP] * 2, spacings=[s])
    geo = D.analyze_geometry(dev, n_lines=48)
    extra = [guard_ring(dev, g, frac)] if g else []
    res = S.run_device(dev, V, geo.onset, housing="insulating", box=0.3, extra=extra)
    els = res["electrodes"]
    i_e2 = [i for i, e in enumerate(els) if e.kind == "emitter" and e.stage == 2][0]
    i_c1 = [i for i, e in enumerate(els) if e.kind == "collector" and e.stage == 1][0]
    pe = res["per_emitter"][i_e2]
    emitted = pe[("emit", i_e2)]
    i_g = [i for i, e in enumerate(els) if e.kind == "guard"]
    out = {"label": label, "s_mm": s * 1e3, "guard_g_mm": g * 1e3 if g else np.nan, "guard_frac": frac if g else np.nan,
           "backflow_s2": pe[("recv", i_c1)] / emitted, "to_guard_s2": pe[("recv", i_g[0])] / emitted if i_g else 0.0,
           "F_mN": res["force_z"] * 1e3, "F_s2_mN": res["force_z_per_emitter"][i_e2] * 1e3,
           "I_uA": sum(res["currents"][("emit", i)] for i, e in enumerate(els) if e.kind == "emitter") * 1e6,
           "length_mm": dev.length() * 1e3, "iterations": res["iterations"]}
    out["P_W"] = out["I_uA"] * 1e-6 * V
    K = D.loss_coefficient(dev) + (1.2 * 0.0 if not g else 0.3)    # guard ring adds roughly one more ring's loss
    area = np.pi * dev.duct_radius**2
    F = res["force_z"]
    u = np.sign(F) * np.sqrt(abs(F) / (STANDARD_AIR.density * area * (1 + K / 2)))
    out["thrust_mN"] = np.sign(u) * STANDARD_AIR.density * area * u**2 * 1e3
    out["TP_mNW"] = out["thrust_mN"] / out["P_W"]
    if g:
        out.update(guard_checks(dev, g, frac))
    return out


def main():
    jobs = [("no guard, s=50", 0.050, 0, 0), ("no guard, s=75", 0.075, 0, 0), ("no guard, s=37.5", 0.0375, 0, 0)]
    for frac in (1.0, 0.75, 0.5):
        jobs.append((f"guard {frac:.2f}V, s=50", 0.050, 0.012, frac))
    jobs.append(("guard 1.00V, s=37.5", 0.0375, 0.010, 1.0))
    with ProcessPoolExecutor(5) as ex:
        df = pd.DataFrame(list(ex.map(case, jobs)))
    df.to_csv(DATA / "phase_i_guard.csv", index=False)
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
    print(df.round(3).to_string())

    fig, axs = plt.subplots(1, 3, figsize=(15, 4.6))
    labels = df.label.tolist()
    col = [COLORS["1-stage"] if "no guard" in l else COLORS["optimized"] for l in labels]
    x = np.arange(len(df))
    axs[0].bar(x, df.backflow_s2 * 100, color=col)
    axs[0].set_ylabel("Stage-2 current drifting back to collector 1 (%)"); axs[0].set_title("Back-flow")
    axs[1].bar(x, df.thrust_mN, color=col)
    axs[1].set_ylabel("Net thrust (mN)"); axs[1].set_title("Thrust")
    axs[2].bar(x, df.TP_mNW, color=col)
    axs[2].set_ylabel("Thrust/power (mN/W)"); axs[2].set_title("Efficiency")
    for ax in axs:
        ax.set_xticks(x); ax.set_xticklabels([l.replace(", ", "\n") for l in labels], fontsize=7.5, rotation=0)
    fig.suptitle("Guard ring upstream of the stage-2 emitter (purple) vs no guard (grey)", fontweight="bold")
    fig.tight_layout()
    save(fig, "I1_guard_electrode", source="sc", assumptions=A + " Guard 12 mm upstream of emitter 2 "
         "(10 mm at s = 37.5). Guard loss coefficient ASSUMED 0.3.")
    return df


if __name__ == "__main__":
    main()
