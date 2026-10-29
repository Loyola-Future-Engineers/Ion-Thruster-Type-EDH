"""Prototype P1x3: three P1 thrusters packed in a triangle, plus a 3-into-1 merge joint.

Compact layout: the single-thruster tie-rod lugs are removed. All three stacks are clamped between
a shared inlet plate (with the three rounded inlets built in) and a shared top plate by three nylon
tie rods that run through the gaps between the thrusters. Each thruster is turned so its
high-voltage terminal faces outward, away from its neighbours.

Writes (in prototypes/):
  P1x3_cluster.stl, P1x3_merge_joint.stl, P1x3_inlet_plate.stl, P1x3_top_plate.stl,
  P1x3_cluster_with_joint.stl
  P1x3_viewer.html                  interactive 3-D viewer, coloured by material
  P1x3_drawing.png|svg              top view and section, dimensioned
  P1x3_exterior_*.png, P1x3_merge_joint.png   renders
  P1x3_checks.txt                   interference and high-voltage clearance checks

Design dimensions only: not built or tested.
Run: .venv/bin/python prototypes/build_cluster.py
"""
import importlib.util
from pathlib import Path

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402
import trimesh  # noqa: E402
from manifold3d import CrossSection, Manifold  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "prototypes"
spec = importlib.util.spec_from_file_location("cadbuild", ROOT / "cad" / "build.py")
cad = importlib.util.module_from_spec(spec); spec.loader.exec_module(cad)
spec2 = importlib.util.spec_from_file_location("drawings", ROOT / "prototypes" / "build_drawings.py")
drw = importlib.util.module_from_spec(spec2); spec2.loader.exec_module(drw)

C = cad.Cfg(n_stages=2, lugs=False)
PITCH = 60.0                         # mm between thruster axes
RC = PITCH / np.sqrt(3)              # triangle circumradius (34.6)
ANGLES = [90.0, 210.0, 330.0]        # thruster positions around the cluster axis
ROD_ANGLES = [30.0, 150.0, 270.0]    # tie rods sit midway between neighbouring thrusters
ROD_R = RC / 2                       # edge midpoints of the triangle
PLATE_R = 30.0                       # rounding radius of the triangular plates around each axis
INLET_T, TOP_T = 12.0, 6.0           # shared plate thicknesses
FLARE = 4.0                          # inlet flare radius built into the inlet plate
WALL = 2.5
FLANGE_T = 5.0
MERGE_LEN = 60.0
OUTLET_LEN = 25.0
R_OUT = C.bore_r * np.sqrt(3)        # equal-area outlet: 3 x Ø40 -> Ø69.3
STANDOFF_D, BASE_T = 10.0, 6.0
HV_LIMIT = 25.0                      # minimum HV-to-ground air clearance target, mm


def centre(phi):
    return np.array([RC * np.cos(np.radians(phi)), RC * np.sin(np.radians(phi))])


def rod_xy(a):
    return np.array([ROD_R * np.cos(np.radians(a)), ROD_R * np.sin(np.radians(a))])


def disc(r, z, xy=(0.0, 0.0), h=0.2):
    return Manifold.cylinder(h, r, r, cad.SEG).translate([xy[0], xy[1], z])


def tri_plate(z0, t, extra=0.0):
    p = Manifold()
    for phi in ANGLES:
        c = centre(phi)
        p += Manifold.cylinder(t, PLATE_R + extra, PLATE_R + extra, cad.SEG).translate([c[0], c[1], z0])
    return p.hull()


def rod_holes(z0, t, r=1.7):
    h = Manifold()
    for a in ROD_ANGLES:
        x, y = rod_xy(a)
        h += Manifold.cylinder(t + 2, r, r, 24).translate([x, y, z0 - 1])
    return h


def thruster_parts():
    """One lug-free P1 stack. Its inlet bellmouth becomes a plain ring; the flare moves into the plate."""
    _, placed, _, _ = cad.build(C)
    t = C.carrier_t
    stack = []
    for n, m in placed:
        if n in ("tie_rod", "standoff", "base_plate"):
            continue
        if n == "inlet_bellmouth":
            m = cad.tube(C.bore_r, C.bore_r + C.wall, -1.5 * t, -0.5 * t)
            n = "inlet_ring"
        stack.append((n, m))
    z_top = max(cad.to_trimesh(m).bounds[1, 2] for n, m in stack if n == "exit_ring")
    return stack, -1.5 * t, z_top


def inlet_plate(z_bot):
    """Shared plate under the stacks with three rounded inlets (quarter-circle flare, radius FLARE)."""
    z0 = z_bot - INLET_T
    plate = tri_plate(z0, INLET_T)
    a = np.radians(np.linspace(0, 90, 20))
    prof = [(0.0, z_bot + 0.1), (C.bore_r, z_bot + 0.1)]
    prof += [(C.bore_r + FLARE - FLARE * np.cos(t), z0 + FLARE - FLARE * np.sin(t)) for t in a]
    prof += [(C.bore_r + FLARE, z0 - 0.1), (0.0, z0 - 0.1)]
    prof = prof[::-1]                                  # counter-clockwise in (r, z) for the revolve
    hole = CrossSection([prof]).revolve(cad.SEG)
    for phi in ANGLES:
        c = centre(phi)
        plate -= hole.translate([c[0], c[1], 0])
    return plate - rod_holes(z0, INLET_T, 1.5), z0     # M3 thread tapped into the plate


def top_plate(z_top):
    plate = tri_plate(z_top, TOP_T)
    for phi in ANGLES:
        c = centre(phi)
        plate -= Manifold.cylinder(TOP_T + 2, C.bore_r, C.bore_r, cad.SEG).translate([c[0], c[1], z_top - 1])
    return plate - rod_holes(z_top, TOP_T)


def merge_joint(z0):
    """3-into-1 joint with a triangular flange that bolts onto the top plate through the tie rods."""
    z1 = z0 + FLANGE_T
    z2 = z1 + MERGE_LEN
    outer, inner = Manifold(), Manifold()
    for phi in ANGLES:
        c = centre(phi)
        outer += (disc(C.bore_r + WALL, z1, c) + disc(R_OUT + WALL, z2)).hull()
        inner += (disc(C.bore_r, z1 - 0.1, c) + disc(R_OUT, z2 + 0.1)).hull()
        inner += Manifold.cylinder(FLANGE_T + 0.2, C.bore_r, C.bore_r, cad.SEG).translate([c[0], c[1], z0 - 0.1])
    outer += Manifold.cylinder(OUTLET_LEN, R_OUT + WALL, R_OUT + WALL, cad.SEG).translate([0, 0, z2])
    inner += Manifold.cylinder(OUTLET_LEN + 2, R_OUT, R_OUT, cad.SEG).translate([0, 0, z2 - 1])
    joint = outer + tri_plate(z0, FLANGE_T) - inner - rod_holes(z0, FLANGE_T)
    return joint, (z0, z1, z2, z2 + OUTLET_LEN)


def rods_and_nuts(z_from, z_to):
    rods, nuts = Manifold(), Manifold()
    for a in ROD_ANGLES:
        x, y = rod_xy(a)
        rods += Manifold.cylinder(z_to + 4 - z_from, 1.5, 1.5, 24).translate([x, y, z_from])
        nuts += (Manifold.cylinder(2.4, 3.2, 3.2, 6) - Manifold.cylinder(3, 1.55, 1.55, 16).translate([0, 0, -0.3])
                 ).translate([x, y, z_to])
    return rods, nuts


def stand(z_plate_bottom):
    """Three PTFE standoffs under the tie rods, and a base plate with three air holes."""
    z_b = z_plate_bottom - C.standoff_len
    st = Manifold()
    for a in ROD_ANGLES:
        x, y = rod_xy(a)
        st += (Manifold.cylinder(C.standoff_len, STANDOFF_D / 2, STANDOFF_D / 2, 48)
               - Manifold.cylinder(C.standoff_len + 2, 1.5, 1.5, 24).translate([0, 0, -1])).translate([x, y, z_b])
    base = tri_plate(z_b - BASE_T, BASE_T, extra=10)
    for phi in ANGLES:
        c = centre(phi)
        base -= Manifold.cylinder(BASE_T + 2, C.bore_r + FLARE, C.bore_r + FLARE, cad.SEG).translate(
            [c[0], c[1], z_b - BASE_T - 1])
    return st, base - rod_holes(z_b - BASE_T, BASE_T)


MAT = {"inlet_ring": "PETG or ASA", "inlet_plate": "PETG or ASA", "top_plate": "PETG or ASA",
       "merge_joint": "PETG or ASA", "joint_nut": "Nylon M3", "cluster_tie_rod": "Nylon M3",
       "cluster_standoff": "PTFE or acetal", "cluster_base_plate": "Polycarbonate or acetal"}
LABEL = {"inlet_ring": "Inlet ring", "inlet_plate": "Shared inlet plate", "top_plate": "Shared top plate",
         "merge_joint": "Merge joint", "joint_nut": "Nuts", "cluster_tie_rod": "Tie rods",
         "cluster_standoff": "Standoffs", "cluster_base_plate": "Base plate"}


def color_of(name):
    return drw.MAT_COLOR[MAT.get(name, cad.PART_INFO.get(name, ("PETG or ASA",))[0])]


def hv_clearance(tagged):
    """Minimum air distance from each thruster's HV metal to another thruster's grounded metal."""
    hv_names = ("emitter_mount_ring", "needle", "terminal_pin_hv")
    gnd_names = ("collector_tube", "terminal_pin_gnd")
    worst = np.inf
    for i in range(3):
        hv = trimesh.util.concatenate([cad.to_trimesh(m) for k, n, m in tagged if k == i and n in hv_names])
        gnd = trimesh.util.concatenate([cad.to_trimesh(m) for k, n, m in tagged if k != i and n in gnd_names])
        from scipy.spatial import cKDTree
        d, _ = cKDTree(gnd.sample(60000)).query(hv.sample(20000))   # dense surface samples (~0.5 mm spacing)
        worst = min(worst, float(d.min()))
    return worst


def exterior(items, name, title, elev=18):
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    meshes, cols = [], []
    for n, m in items:
        tm = cad.to_trimesh(m)
        meshes.append(tm); cols += [matplotlib.colors.to_rgb(color_of(n))] * len(tm.faces)
    tm = trimesh.util.concatenate(meshes)
    cols = np.array(cols)
    light = np.array([0.4, -0.6, 0.7]); light /= np.linalg.norm(light)
    shade = (0.45 + 0.55 * np.clip(tm.face_normals @ light, 0, 1))[:, None]
    fig = plt.figure(figsize=(8, 9))
    ax = fig.add_subplot(111, projection="3d")
    ax.add_collection3d(Poly3DCollection(tm.vertices[tm.faces], facecolors=cols * shade, edgecolor="none"))
    lo, hi = tm.bounds
    ax.set_xlim(lo[0], hi[0]); ax.set_ylim(lo[1], hi[1]); ax.set_zlim(lo[2], hi[2])
    ax.set_box_aspect(hi - lo); ax.view_init(elev=elev, azim=-60); ax.set_axis_off()
    ax.set_title(title + "\n(design, not built)", fontsize=10)
    fig.savefig(OUT / name, dpi=130, bbox_inches="tight")
    plt.close(fig)


def main():
    stack, z_stack_bot, z_top = thruster_parts()
    tagged = []                                       # (thruster index, name, manifold)
    for i, phi in enumerate(ANGLES):
        c = centre(phi)
        for n, m in stack:
            mm = m.rotate([0, 0, phi]).translate([c[0], c[1], 0])     # HV terminal (0 deg) now points outward
            if n == "terminal_pin":
                zc = cad.to_trimesh(mm).bounds[:, 2].mean()
                n = "terminal_pin_hv" if any(abs(zc - ze) < 1 for ze in (0.0, C.tip_z() + C.gap + C.spacing)) else "terminal_pin_gnd"
            tagged.append((i, n, mm))
    plate_in, z_plate_bot = inlet_plate(z_stack_bot)
    plate_top = top_plate(z_top)
    joint, (z0, z1, z2, z3) = merge_joint(z_top + TOP_T)
    rods, nuts = rods_and_nuts(z_plate_bot, z0 + FLANGE_T)
    rods_nojoint, nuts_nojoint = rods_and_nuts(z_plate_bot, z_top + TOP_T)
    standoffs, base = stand(z_plate_bot)

    thrusters = [(("terminal_pin" if n.startswith("terminal_pin") else n), m) for _, n, m in tagged]
    common = [("inlet_plate", plate_in), ("top_plate", plate_top), ("cluster_standoff", standoffs),
              ("cluster_base_plate", base)]
    cluster = thrusters + common + [("cluster_tie_rod", rods_nojoint), ("joint_nut", nuts_nojoint)]
    with_joint = thrusters + common + [("cluster_tie_rod", rods), ("merge_joint", joint), ("joint_nut", nuts)]

    clashes = cad.interference(with_joint)
    clear = hv_clearance(tagged)
    lines = [f"Pairwise overlap check of {len(with_joint)} placed parts (tolerance 0.5 mm3):",
             "\n".join(f"  {a} x {b}: {v} mm3" for a, b, v in clashes) or "  No interferences found.",
             f"Minimum air clearance, HV metal of one thruster to grounded metal of another: {clear:.1f} mm "
             f"(target >= {HV_LIMIT:.0f} mm at 19.5 kV): " + ("OK" if clear >= HV_LIMIT else "TOO SMALL")]
    (OUT / "P1x3_checks.txt").write_text("\n".join(lines) + "\n")
    old = OUT / "P1x3_interference.txt"
    if old.exists():
        old.unlink()

    trimesh.util.concatenate([cad.to_trimesh(m) for _, m in cluster]).export(OUT / "P1x3_cluster.stl")
    for n, m in (("P1x3_merge_joint.stl", joint), ("P1x3_inlet_plate.stl", plate_in), ("P1x3_top_plate.stl", plate_top)):
        tm = cad.to_trimesh(m); assert tm.is_watertight, n; tm.export(OUT / n)
    trimesh.util.concatenate([cad.to_trimesh(m) for _, m in with_joint]).export(OUT / "P1x3_cluster_with_joint.stl")

    import plotly.graph_objects as go
    by = {}
    for n, m in with_joint:
        by.setdefault(n, []).append(cad.to_trimesh(m))
    fig = go.Figure()
    for n, ms in by.items():
        tm = trimesh.util.concatenate(ms)
        v, f = tm.vertices, tm.faces
        mat = MAT.get(n, cad.PART_INFO.get(n, ("",))[0])
        fig.add_trace(go.Mesh3d(x=v[:, 0], y=v[:, 1], z=v[:, 2], i=f[:, 0], j=f[:, 1], k=f[:, 2],
                                name=f"{LABEL.get(n, drw.LABEL.get(n, n))} ({mat})", color=color_of(n),
                                opacity=0.45 if mat.startswith("PETG") else 1.0, showlegend=True))
    fig.update_layout(title="P1x3: three P1 thrusters 60 mm apart with a 3-into-1 merge joint (design, not built)",
                      scene=dict(aspectmode="data"), margin=dict(l=0, r=0, t=40, b=0))
    fig.write_html(OUT / "P1x3_viewer.html", include_plotlyjs="cdn")

    # drawing: top view and section
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(16, 10), gridspec_kw={"width_ratios": [1, 1.1]})
    zc = z_top - 3.0
    for n, m in cluster:
        tm = cad.to_trimesh(m)
        if tm.bounds[0, 2] > zc or tm.bounds[1, 2] < zc:
            continue
        sec = tm.section(plane_origin=[0, 0, zc], plane_normal=[0, 0, 1])
        if sec is not None:
            drw.fill(a1, [p[:, :2] for p in sec.discrete], color_of(n), 0.4)
    sec = cad.to_trimesh(plate_top).section(plane_origin=[0, 0, z_top + TOP_T / 2], plane_normal=[0, 0, 1])
    for p in sec.discrete:
        a1.plot(p[:, 0], p[:, 1], ls="--", lw=0.7, color="#3b82f6")
    for _, n, m in tagged:
        if n == "terminal_pin_hv":
            b = cad.to_trimesh(m).bounds
            a1.plot(*b[:, :2].mean(axis=0), "o", color="#c99a2e", ms=6, mec="k", mew=0.5)
    pts = np.array([centre(p) for p in ANGLES] + [centre(ANGLES[0])])
    a1.plot(pts[:, 0], pts[:, 1], "k-.", lw=0.6)
    for i, phi in enumerate(ANGLES):
        c = centre(phi); a1.plot(*c, "k+", ms=8)
        a1.text(c[0], c[1] - 6, f"P1 #{i + 1}", ha="center", fontsize=8)
    drw.dim(a1, centre(210), centre(330), f"{PITCH:.0f} between axes", off=(0, -6))
    a1.autoscale_view(); a1.set_aspect("equal"); a1.grid(alpha=0.2); a1.set_xlabel("mm"); a1.set_ylabel("mm")
    a1.set_title("Top view: section through the exit rings\n(dashed: shared top plate; gold: HV terminals facing "
                 "outward; small circles: tie rods)", fontsize=10)
    for n, m in with_joint:
        tm = cad.to_trimesh(m)
        if tm.bounds[0, 0] > 0.5 or tm.bounds[1, 0] < -0.5:
            continue
        sec = tm.section(plane_origin=[0.001, 0, 0], plane_normal=[1, 0, 0])
        if sec is not None:
            drw.fill(a2, [p[:, 1:] for p in sec.discrete], color_of(n), 0.35)
    a2.autoscale_view()
    yd = centre(90)[1] + 42
    drw.dim(a2, (yd, z_plate_bot), (yd, z_stack_bot), f"{INLET_T:.0f}", off=(5, 0), fs=6.5)
    drw.dim(a2, (yd, z_top), (yd, z0), f"{TOP_T:.0f}", off=(4, 0), fs=6.5)
    drw.dim(a2, (yd, z1), (yd, z2), f"{MERGE_LEN:.0f} merge", off=(9, 0))
    drw.dim(a2, (yd, z2), (yd, z3), f"{OUTLET_LEN:.0f}", off=(5, 0), fs=6.5)
    drw.dim(a2, (-R_OUT, z3 + 8), (R_OUT, z3 + 8), f"Ø{2 * R_OUT:.1f} outlet (= area of 3 × Ø40)", off=(0, 4))
    a2.set_aspect("equal"); a2.grid(alpha=0.2); a2.set_xlabel("mm"); a2.set_ylabel("mm (air flows upward)")
    a2.set_title("Section through the cluster axis and thruster #1\n(shared inlet plate at the bottom, top plate "
                 "and merge joint at the top)", fontsize=10)
    mats = ["Brass", "Stainless steel 304", "Aluminum 6061", "PETG or ASA", "Nylon M3", "PTFE or acetal",
            "Polycarbonate or acetal"]
    fig.legend(handles=[Patch(fc=drw.MAT_COLOR[m], ec="#333", lw=0.5, label=m) for m in mats], loc="lower center",
               ncol=7, fontsize=8, frameon=False)
    fig.suptitle("Prototype P1x3: compact triangular cluster with 3-into-1 merge joint (design dimensions in mm, "
                 "not built)", fontweight="bold")
    fig.tight_layout(rect=(0, 0.04, 1, 0.96))
    for ext in ("png", "svg"):
        fig.savefig(OUT / f"P1x3_drawing.{ext}", dpi=140, bbox_inches="tight")
    plt.close(fig)

    exterior(with_joint, "P1x3_exterior_with_joint.png", "P1x3 cluster with merge joint fitted")
    exterior(cluster, "P1x3_exterior_cluster.png", "P1x3: three P1 thrusters, 60 mm apart")
    exterior([("merge_joint", joint)], "P1x3_merge_joint.png", "3-into-1 merge joint (PETG/ASA)", elev=-25)
    fp = cad.to_trimesh(base).bounds
    print(f"pitch {PITCH}, base footprint {fp[1, 0] - fp[0, 0]:.0f} x {fp[1, 1] - fp[0, 1]:.0f} mm, "
          f"joint height {z3 - z0:.0f} mm, joint {joint.volume() * 1.27e-3:.0f} g, "
          f"inlet plate {plate_in.volume() * 1.27e-3:.0f} g, top plate {plate_top.volume() * 1.27e-3:.0f} g, "
          f"rod length {z0 + FLANGE_T + 4 - z_plate_bot:.0f} mm")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
