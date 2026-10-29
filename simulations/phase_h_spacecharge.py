"""Phase H: self-consistent space-charge simulations and comparison with the reduced-order model.

Outputs: data/phase_h_*.csv, charts/H*.png|svg.
Run: .venv/bin/python simulations/phase_h_spacecharge.py
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

A = ref.ASSUMPTIONS.replace("no space charge in ion paths", "self-consistent space charge (Kaptsov injection)")
V_REF = 19.47e3          # max safe voltage of the d = 25 mm reference (85 % of sparkover)
MU = STANDARD_AIR.mobility


def coax_validation():
    a, R, L = 2e-4, 0.02, 0.004
    E_on = float(corona.peek_field_wire(a)); v0 = E_on * a * np.log(R / a)
    rows = []
    for V in np.linspace(9e3, 30e3, 8):
        r = S.graded_axis(0, R * 1.05, [(0, a / 8), (a, a / 8), (R, R / 200)], h_max=R / 60, growth=0.08)
        g = S.Grid(r, np.linspace(0, L, 9))
        els = [csm.Electrode("W", a / 2, L / 2, a / 2, L, 0, 1.0, "emitter"),
               csm.Electrode("O", R + 0.5 * (r[-1] - R), L / 2, 0.5 * (r[-1] - R) + 1e-9, L, 0, 0.0, "collector")]
        res = S.SpaceChargeSolver(g, els, neumann_z=True).solve({0: V, 1: 0.0}, {0: v0})
        rows.append({"V_kV": V / 1e3, "solver_uA_per_mm": res["currents"][("emit", 0)] / L * 1e3,
                     "exact_uA_per_mm": S.coax_reference(V, a, R, E_on) * 1e3,
                     "townsend_uA_per_mm": float(corona.townsend_coax_current_per_length(V, v0, a, R)) * 1e3})
    df = pd.DataFrame(rows)
    df.to_csv(DATA / "phase_h_coax_validation.csv", index=False)
    return df


def case(args):
    """One space-charge run. Returns flat metrics, including per-emitter collector currents."""
    label, n, gap, spacing, V, housing, keep = args
    dev = ref.device(n, gaps=[gap] * n, spacings=[spacing] * (n - 1))
    geo = D.analyze_geometry(dev, n_lines=48)
    res = S.run_device(dev, V, geo.onset, housing=housing, box=0.3)
    els, cur = res["electrodes"], res["currents"]
    out = {"label": label, "n": n, "gap_mm": gap * 1e3, "spacing_mm": spacing * 1e3, "V_kV": V / 1e3,
           "housing": housing or "none", "iterations": res["iterations"], "conv": res["kaptsov_error"],
           "F_mN": res["force_z"] * 1e3, "I_uA": sum(cur[("emit", i)] for i, e in enumerate(els) if e.kind == "emitter") * 1e6,
           "I_escape_uA": cur[("recv", "outer")] * 1e6}
    out["P_W"] = out["I_uA"] * 1e-6 * V
    for i, e in enumerate(els):
        if e.kind != "emitter":
            continue
        k = e.stage
        pe = res["per_emitter"].get(i)
        if pe is None:
            continue
        emitted = pe[("emit", i)]
        own = pe[("recv", i + 1)]
        upstream = sum(pe[("recv", j)] for j, ej in enumerate(els) if ej.kind == "collector" and 0 < ej.stage < k)
        out[f"s{k}_I_uA"] = emitted * 1e6
        out[f"s{k}_own"] = own / emitted if emitted else np.nan
        out[f"s{k}_backflow"] = upstream / emitted if emitted else np.nan
        out[f"s{k}_escape"] = pe[("recv", "outer")] / emitted if emitted else np.nan
        out[f"s{k}_F_mN"] = res["force_z_per_emitter"][i] * 1e3
    # reduced-order model at the same point, for comparison
    r = D.evaluate(geo, V, iterate_flow=False)
    out["ro_I_uA"] = r["I"] * 1e6; out["ro_F_mN"] = r["F_ehd"] * 1e3
    for k in range(n):
        out[f"ro_s{k+1}_backflow"] = D.stage_current_split(geo, k)["upstream"]
    # air flow with the same duct model as device.evaluate
    K = D.loss_coefficient(dev); area = np.pi * dev.duct_radius**2
    F = res["force_z"]
    u = np.sign(F) * np.sqrt(abs(F) / (STANDARD_AIR.density * area * (1 + K / 2)))
    out["thrust_mN"] = np.sign(u) * STANDARD_AIR.density * area * u**2 * 1e3
    out["u_ms"] = u; out["Q_Ls"] = area * u * 1000.0
    out["TP_mNW"] = out["thrust_mN"] / out["P_W"] if out["P_W"] > 0 else np.nan
    if keep:
        s = res["solver"]
        np.savez_compressed(DATA / f"phase_h_field_{label}.npz", r=s.g.r, z=s.g.z,
                            phi=res["phi"].reshape(s.g.nr, s.g.nz), rho=res["rho"].reshape(s.g.nr, s.g.nz),
                            tag=s.tag.reshape(s.g.nr, s.g.nz), blocked=s.blocked.reshape(s.g.nr, s.g.nz))
    return out


def main():
    cv = coax_validation()
    jobs = []
    for V in (10e3, 12.5e3, 15e3, 17.5e3, V_REF):
        jobs.append((f"iv_{V/1e3:.1f}", 1, 0.025, 0, V, "insulating", False))
    for s in (0.025, 0.0375, 0.050, 0.075):
        jobs.append((f"bf_s{s*1e3:.0f}", 2, 0.025, s, V_REF, "insulating", s == 0.050))
    for n in (1, 3):
        jobs.append((f"stages_{n}", n, 0.025, 0.050, V_REF, "insulating", False))
    jobs.append(("housing_none", 2, 0.025, 0.050, V_REF, None, False))
    with ProcessPoolExecutor(5) as ex:
        df = pd.DataFrame(list(ex.map(case, jobs)))
    df.to_csv(DATA / "phase_h_spacecharge_cases.csv", index=False)
    plots(cv, df)
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 50)
    print(cv.round(4).to_string()); print(df.round(3).T.to_string())


def plots(cv, df):
    fig, axs = plt.subplots(1, 3, figsize=(15, 4.3))
    ax = axs[0]
    ax.plot(cv.V_kV, cv.exact_uA_per_mm, "k-", lw=2, label="exact 1-D solution")
    ax.plot(cv.V_kV, cv.solver_uA_per_mm, "o", color=COLORS["thrust"], label="2-D space-charge solver")
    ax.plot(cv.V_kV, cv.townsend_uA_per_mm, "--", color=COLORS["power"], label="Townsend formula")
    ax.set_xlabel("Voltage (kV)"); ax.set_ylabel("Current per length (uA/mm)")
    ax.set_title("Validation: coaxial wire-cylinder (0.2 mm / 20 mm)"); ax.legend(fontsize=8)
    iv = df[df.label.str.startswith("iv_") | (df.label == "stages_1")].drop_duplicates("V_kV").sort_values("V_kV")
    ax = axs[1]
    ax.plot(iv.V_kV, iv.I_uA, "o-", color=COLORS["thrust"], label="space-charge solver")
    ax.plot(iv.V_kV, iv.ro_I_uA, "s--", color="#999", label="reduced model (Townsend closure)")
    ax.set_xlabel("Voltage (kV)"); ax.set_ylabel("Emitter current (uA)"); ax.set_title("Single stage I-V (d = 25 mm)")
    ax.legend(fontsize=8)
    ax = axs[2]
    ax.plot(iv.V_kV, iv.F_mN, "o-", color=COLORS["thrust"], label="space-charge solver")
    ax.plot(iv.V_kV, iv.ro_F_mN, "s--", color="#999", label="reduced model")
    ax.set_xlabel("Voltage (kV)"); ax.set_ylabel("EHD body force (mN)"); ax.set_title("Single stage force"); ax.legend(fontsize=8)
    fig.tight_layout()
    save(fig, source="sc", name="H1_spacecharge_validation_and_IV", assumptions=A + " Insulating 40 mm bore modelled as a charged-up "
         "(zero-flux) wall.")

    bf = df[df.label.str.startswith("bf_")].sort_values("spacing_mm")
    fig, axs = plt.subplots(1, 2, figsize=(12, 4.3))
    ratio = bf.spacing_mm / bf.gap_mm
    axs[0].plot(ratio, bf.s2_backflow * 100, "o-", color=COLORS["efficiency"], lw=2, label="space-charge solver")
    axs[0].plot(ratio, bf.ro_s2_backflow * 100, "s--", color="#999", label="reduced model (Laplace paths)")
    axs[0].plot(ratio, bf.s2_escape * 100, "^:", color=COLORS["margin"], label="space-charge: escaping to surroundings")
    axs[0].set_xlabel("Inter-stage spacing / gap (s/d)"); axs[0].set_ylabel("Share of stage-2 current (%)")
    axs[0].set_title("Stage-2 back-flow to collector 1"); axs[0].legend(fontsize=8)
    axs[1].plot(ratio, bf.thrust_mN, "o-", color=COLORS["thrust"], label="net thrust after duct losses")
    axs[1].plot(ratio, bf.s2_F_mN, "s-", color=COLORS["2-stage"], label="stage-2 EHD force")
    axs[1].plot(ratio, bf.s1_F_mN, "^-", color=COLORS["1-stage"], label="stage-1 EHD force")
    axs[1].axhline(0, color="k", lw=0.6)
    axs[1].set_xlabel("s/d"); axs[1].set_ylabel("mN"); axs[1].set_title("Force per stage"); axs[1].legend(fontsize=8)
    fig.tight_layout()
    save(fig, source="sc", name="H2_spacecharge_backflow", assumptions=A + f" Two stages, d = 25 mm, V = {V_REF/1e3:.1f} kV.")

    st = pd.concat([df[df.label == "stages_1"], df[df.label == "bf_s50"].assign(n=2), df[df.label == "stages_3"]])
    fig, axs = plt.subplots(1, 3, figsize=(13, 4))
    for ax, (col, lab) in zip(axs, [("thrust_mN", "Net thrust (mN)"), ("P_W", "Power (W)"), ("TP_mNW", "Thrust/power (mN/W)")]):
        ax.bar(st.n, st[col], color=[COLORS[f"{n}-stage"] for n in st.n])
        ax.set_xticks([1, 2, 3]); ax.set_xlabel("stages"); ax.set_title(lab)
    fig.suptitle(f"Stage count with space charge (d = 25 mm, s = 50 mm, {V_REF/1e3:.1f} kV, insulating bore)",
                 fontweight="bold")
    fig.tight_layout()
    save(fig, source="sc", name="H3_spacecharge_stage_count", assumptions=A)

    f = np.load(DATA / "phase_h_field_bf_s50.npz")
    r, z, phi, rho, tag, blk = f["r"], f["z"], f["phi"], f["rho"], f["tag"], f["blocked"]
    sel_r = r <= 0.03; sel_z = (z >= -0.02) & (z <= 0.12)
    R, Z = np.meshgrid(r[sel_r], z[sel_z], indexing="ij")
    P = phi[np.ix_(sel_r, sel_z)]; Q = rho[np.ix_(sel_r, sel_z)].copy()
    solid = (tag[np.ix_(sel_r, sel_z)] >= 0) | blk[np.ix_(sel_r, sel_z)]
    Q[solid] = np.nan
    fig, ax = plt.subplots(figsize=(12, 4.2))
    im = ax.pcolormesh(Z * 1e3, R * 1e3, np.log10(np.maximum(Q, 1e-7)), cmap="viridis", shading="auto", vmin=-6, vmax=-3)
    cb = fig.colorbar(im, ax=ax, pad=0.01); cb.set_label("log10 space-charge density (C/m3)")
    ax.contour(Z * 1e3, R * 1e3, P / 1e3, levels=np.arange(1, 20, 2), colors="w", linewidths=0.5)
    ax.contourf(Z * 1e3, R * 1e3, solid.astype(float), levels=[0.5, 1.5], colors=["#bbb"])
    ax.set_xlabel("Axial position z (mm)"); ax.set_ylabel("Radius r (mm)")
    ax.set_title(f"Space-charge density and equipotentials (1 kV steps), 2 stages, s = 50 mm, {V_REF/1e3:.1f} kV")
    save(fig, source="sc", name="H4_charge_density_map", assumptions=A + " Grey: electrodes and insulating bore wall.")


if __name__ == "__main__":
    main()
