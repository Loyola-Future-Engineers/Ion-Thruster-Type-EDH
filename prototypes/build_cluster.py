"""Prototype P1x3: three P1 thrusters in a triangular cluster, plus a 3-into-1 merge joint.

Writes (in prototypes/):
  P1x3_cluster.stl              three P1 thrusters on a shared triangular base plate
  P1x3_merge_joint.stl          the 3-into-1 joint on its own (print in PETG/ASA)
  P1x3_cluster_with_joint.stl   cluster with the joint fitted
  P1x3_viewer.html              interactive 3-D viewer, coloured by material
  P1x3_drawing.png|svg          top view (triangle layout) and section through the joint, dimensioned
  P1x3_interference.txt         pairwise overlap check

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
from manifold3d import Manifold  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "prototypes"
spec = importlib.util.spec_from_file_location("cadbuild", ROOT / "cad" / "build.py")
cad = importlib.util.module_from_spec(spec); spec.loader.exec_module(cad)
spec2 = importlib.util.spec_from_file_location("drawings", ROOT / "prototypes" / "build_drawings.py")
drw = importlib.util.module_from_spec(spec2); spec2.loader.exec_module(drw)

C = cad.Cfg(n_stages=2)
PITCH = 92.0                         # mm between thruster axes (clears lugs and terminal pins)
RC = PITCH / np.sqrt(3)              # circumradius of the triangle
ANGLES = [90.0, 210.0, 330.0]        # thruster positions around the cluster axis
WALL = 2.5                           # joint wall thickness
FLANGE_T = 5.0
MERGE_LEN = 90.0                     # inlet plane to the merged outlet plane
OUTLET_LEN = 25.0
R_OUT = C.bore_r * np.sqrt(3)        # equal-area outlet: 3 x Ø40 -> Ø69.3


def centre(phi):
    return np.array([RC * np.cos(np.radians(phi)), RC * np.sin(np.radians(phi))])


def disc(r, z, xy=(0.0, 0.0), h=0.2):
    return Manifold.cylinder(h, r, r, cad.SEG).translate([xy[0], xy[1], z])


def thruster_parts():
    """Placed parts of one P1 (without its own base plate), standing on z = stand bottom."""
    parts, placed, _, _ = cad.build(C)
    keep = [(n, m) for n, m in placed if n != "base_plate"]
    z_top = max(cad.to_trimesh(m).bounds[1, 2] for n, m in keep if n == "exit_ring")
    z_base = min(cad.to_trimesh(m).bounds[0, 2] for n, m in keep if n == "standoff")
    return keep, z_top, z_base


def cluster(keep):
    placed = []
    for phi in ANGLES:
        c = centre(phi)
        rot = phi - 90.0                 # turn each thruster so one lug points away from the cluster centre
        for n, m in keep:
            placed.append((n, m.rotate([0, 0, rot]).translate([c[0], c[1], 0])))
    return placed


def base_plate(z_base):
    """Rounded-triangle plate (6 mm) under all three thrusters, with an air hole under each inlet."""
    plate = Manifold()
    for phi in ANGLES:
        c = centre(phi)
        plate += Manifold.cylinder(6, 62, 62, cad.SEG).translate([c[0], c[1], z_base - 6])
    plate = plate.hull()
    for phi in ANGLES:
        c = centre(phi)
        plate -= Manifold.cylinder(10, 32, 32, cad.SEG).translate([c[0], c[1], z_base - 8])
        for k in range(3):
            a = np.radians(90 + 120 * k + phi - 90)
            plate -= Manifold.cylinder(10, 1.7, 1.7, 24).translate([c[0] + C.lug_r * np.cos(a),
                                                                    c[1] + C.lug_r * np.sin(a), z_base - 8])
    return plate


def merge_joint(z0):
    """3-into-1 joint. Flanges bolt to each exit ring through the tie rods; three ducts blend into one."""
    z1 = z0 + FLANGE_T                 # start of the ducts
    z2 = z1 + MERGE_LEN                # merged plane
    outer = Manifold(); inner = Manifold()
    for phi in ANGLES:
        c = centre(phi)
        outer += (disc(C.bore_r + WALL, z1, c) + disc(R_OUT + WALL, z2)).hull()
        inner += (disc(C.bore_r, z1 - 0.1, c) + disc(R_OUT, z2 + 0.1)).hull()
    outer += Manifold.cylinder(OUTLET_LEN, R_OUT + WALL, R_OUT + WALL, cad.SEG).translate([0, 0, z2])
    inner += Manifold.cylinder(OUTLET_LEN + 2, R_OUT, R_OUT, cad.SEG).translate([0, 0, z2 - 1])
    flange = Manifold()
    holes = Manifold()
    for phi in ANGLES:
        c = centre(phi)
        ring = Manifold.cylinder(FLANGE_T, C.lug_r + 4.5, C.lug_r + 4.5, cad.SEG).translate([c[0], c[1], z0])
        flange += ring
        inner += Manifold.cylinder(FLANGE_T + 0.2, C.bore_r, C.bore_r, cad.SEG).translate([c[0], c[1], z0 - 0.1])
        for k in range(3):
            a = np.radians(90 + 120 * k + phi - 90)
            holes += Manifold.cylinder(FLANGE_T + 2, 1.7, 1.7, 24).translate(
                [c[0] + C.lug_r * np.cos(a), c[1] + C.lug_r * np.sin(a), z0 - 1])
    return outer + flange - inner - holes, (z0, z1, z2, z2 + OUTLET_LEN)


def joint_nuts(z0):
    """M3 nylon nuts on the tie rods above the joint flange (shown in the assembly only)."""
    nuts = Manifold()
    for phi in ANGLES:
        c = centre(phi)
        for k in range(3):
            a = np.radians(90 + 120 * k + phi - 90)
            x, y = c[0] + C.lug_r * np.cos(a), c[1] + C.lug_r * np.sin(a)
            nuts += (Manifold.cylinder(2.4, 3.2, 3.2, 6) - Manifold.cylinder(3, 1.5, 1.5, 16).translate([0, 0, -0.3])
                     ).translate([x, y, z0 + FLANGE_T])
    return nuts


def exterior(items, name, title, elev=18):
    """Shaded 3-D render coloured by material (painter's algorithm; good for exterior views)."""
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


MAT = {"base_plate_cluster": "Polycarbonate or acetal", "merge_joint": "PETG or ASA", "joint_nut": "Nylon M3"}


def color_of(name):
    return drw.MAT_COLOR[MAT.get(name, cad.PART_INFO.get(name, ("PETG or ASA",))[0])]


def main():
    keep, z_top, z_base = thruster_parts()
    placed = cluster(keep)
    # tie rods were sized for one exit ring + nut; lengthen them by the joint flange thickness
    placed = [(n, (m + Manifold.cylinder(FLANGE_T + 2.4, 1.5, 1.5, 24).translate(
        [cad.to_trimesh(m).bounds[:, 0].mean(), cad.to_trimesh(m).bounds[:, 1].mean(), cad.to_trimesh(m).bounds[1, 2]]))
               if n == "tie_rod" else m) for n, m in placed]
    placed.append(("base_plate_cluster", base_plate(z_base)))
    joint, (z0, z1, z2, z3) = merge_joint(z_top)
    with_joint = placed + [("merge_joint", joint), ("joint_nut", joint_nuts(z_top))]

    clashes = cad.interference(with_joint)
    (OUT / "P1x3_interference.txt").write_text(
        f"Pairwise overlap check of {len(with_joint)} placed parts (tolerance 0.5 mm3)\n"
        + ("\n".join(f"{a} x {b}: {v} mm3" for a, b, v in clashes) or "No interferences found.") + "\n")

    trimesh.util.concatenate([cad.to_trimesh(m) for _, m in placed]).export(OUT / "P1x3_cluster.stl")
    jt = cad.to_trimesh(joint)
    assert jt.is_watertight
    jt.export(OUT / "P1x3_merge_joint.stl")
    trimesh.util.concatenate([cad.to_trimesh(m) for _, m in with_joint]).export(OUT / "P1x3_cluster_with_joint.stl")

    # viewer
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
                                name=f"{drw.LABEL.get(n, n.replace('_', ' '))} ({mat})", color=color_of(n),
                                opacity=0.45 if mat.startswith("PETG") else 1.0, showlegend=True))
    fig.update_layout(title="P1x3: three P1 thrusters in a triangle with a 3-into-1 merge joint (design, not built)",
                      scene=dict(aspectmode="data"), margin=dict(l=0, r=0, t=40, b=0))
    fig.write_html(OUT / "P1x3_viewer.html", include_plotlyjs="cdn")

    # drawing: top view + section through the cluster axis and thruster 1 (x = 0 plane)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(16, 10), gridspec_kw={"width_ratios": [1, 1.1]})
    for n, m in with_joint:
        if n in ("merge_joint", "joint_nut"):
            continue
        tm = cad.to_trimesh(m)
        zc = z_top - 3.0                                   # cut through the exit rings
        if tm.bounds[0, 2] > zc or tm.bounds[1, 2] < zc:
            continue
        sec = tm.section(plane_origin=[0, 0, zc], plane_normal=[0, 0, 1])
        if sec is not None:
            drw.fill(a1, [p[:, :2] for p in sec.discrete], color_of(n), 0.4)
    bp = cad.to_trimesh(base_plate(z_base))
    sec = bp.section(plane_origin=[0, 0, z_base - 3], plane_normal=[0, 0, 1])
    for p in sec.discrete:
        a1.plot(p[:, 0], p[:, 1], ls="--", lw=0.7, color="#3b82f6")
    pts = np.array([centre(p) for p in ANGLES] + [centre(ANGLES[0])])
    a1.plot(pts[:, 0], pts[:, 1], "k-.", lw=0.6)
    for i, phi in enumerate(ANGLES):
        c = centre(phi); a1.plot(*c, "k+", ms=8); a1.text(c[0], c[1] - 6, f"P1 #{i + 1}", ha="center", fontsize=8)
    drw.dim(a1, centre(210), centre(330), f"{PITCH:.0f} between axes", off=(0, -6))
    a1.text(0, 2, f"triangle circumradius {RC:.1f}", ha="center", fontsize=7)
    a1.set_aspect("equal"); a1.grid(alpha=0.2); a1.set_xlabel("mm"); a1.set_ylabel("mm")
    a1.set_title("Top view: section through the exit rings\n(dashed: shared base plate outline)", fontsize=10)

    for n, m in with_joint:
        tm = cad.to_trimesh(m)
        if tm.bounds[0, 0] > 0.5 or tm.bounds[1, 0] < -0.5:
            continue
        sec = tm.section(plane_origin=[0.001, 0, 0], plane_normal=[1, 0, 0])
        if sec is not None:
            drw.fill(a2, [p[:, 1:] for p in sec.discrete], color_of(n), 0.35)
    a2.autoscale_view()
    yc = centre(90)[1]
    drw.dim(a2, (yc + 62, z0), (yc + 62, z1), f"{FLANGE_T:.0f}", off=(5, 0), fs=6.5)
    drw.dim(a2, (yc + 62, z1), (yc + 62, z2), f"{MERGE_LEN:.0f} merge", off=(9, 0))
    drw.dim(a2, (yc + 62, z2), (yc + 62, z3), f"{OUTLET_LEN:.0f}", off=(5, 0), fs=6.5)
    drw.dim(a2, (-R_OUT, z3 + 8), (R_OUT, z3 + 8), f"Ø{2 * R_OUT:.1f} outlet (= area of 3 × Ø40)", off=(0, 4))
    drw.dim(a2, (yc - C.bore_r, z0 - 12), (yc + C.bore_r, z0 - 12), "Ø40 inlet", off=(0, 3), fs=6.5)
    a2.set_aspect("equal"); a2.grid(alpha=0.2); a2.set_xlabel("mm"); a2.set_ylabel("mm (air flows upward)")
    a2.set_title("Section through the cluster axis and thruster #1\n(joint bolts to the exit rings via the tie rods)",
                 fontsize=10)
    mats = ["Brass", "Stainless steel 304", "Aluminium 6061", "PETG or ASA", "Nylon M3", "PTFE or acetal",
            "Polycarbonate or acetal"]
    fig.legend(handles=[Patch(fc=drw.MAT_COLOR[m], ec="#333", lw=0.5, label=m) for m in mats], loc="lower center",
               ncol=7, fontsize=8, frameon=False)
    fig.suptitle("Prototype P1x3: triangular cluster with 3-into-1 merge joint (design dimensions in mm, not built)",
                 fontweight="bold")
    fig.tight_layout(rect=(0, 0.04, 1, 0.96))
    for ext in ("png", "svg"):
        fig.savefig(OUT / f"P1x3_drawing.{ext}", dpi=140, bbox_inches="tight")
    plt.close(fig)

    exterior(with_joint, "P1x3_exterior_with_joint.png", "P1x3 cluster with merge joint fitted")
    exterior(placed, "P1x3_exterior_cluster.png", "P1x3: three P1 thrusters in a triangle")
    exterior([("merge_joint", joint)], "P1x3_merge_joint.png", "3-into-1 merge joint (PETG/ASA)", elev=-25)

    jm = joint.volume() * 1.27e-3
    print(f"pitch {PITCH} mm, outlet Ø{2 * R_OUT:.1f} mm, joint height {z3 - z0:.0f} mm, joint mass {jm:.1f} g, "
          f"clashes: {clashes or 'none'}")


if __name__ == "__main__":
    main()
