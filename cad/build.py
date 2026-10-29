"""Parametric 3-D models of every part of the recommended thruster, plus assemblies.

Writes:
  cad/stl/<part>.stl               one file per unique part (millimetres)
  cad/assembly_<n>stage.stl        assembled device on its test stand
  cad/viewer_<n>stage.html         interactive 3-D viewer (Plotly)
  cad/bom_<n>stage.csv             bill of materials with masses from the meshes
  diagrams/cad_<n>stage_*.png      section drawing and exterior render

Geometry follows docs/recommendations.md (common-supply build): 40 mm insulating bore, 16 axial
stainless needles on a 30 mm brass ring, 30 mm aluminium tube collectors, d = 25 mm, s = 75 mm.
The parts are a design proposal. They have not been printed, machined or tested.

Run: .venv/bin/python cad/build.py
"""
import csv
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import trimesh
from manifold3d import CrossSection, Manifold

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "cad"
SEG = 96


@dataclass
class Cfg:
    n_stages: int = 2
    bore_r: float = 20.0            # mm, inner radius of the housing
    wall: float = 3.0
    gap: float = 25.0               # emitter ring plane -> collector leading edge
    spacing: float = 75.0           # collector leading edge -> next emitter plane (s = 3d)
    ring_r: float = 15.0            # emitter / collector mean radius
    n_pins: int = 16
    pin_len: float = 6.0            # exposed needle length
    pin_d: float = 0.8
    coll_len: float = 10.0
    coll_wall: float = 1.0
    carrier_t: float = 6.0          # axial thickness of carrier rings
    lug_r: float = 38.0             # tie-rod pitch radius (clears the inlet flare and standoffs)
    standoff_len: float = 100.0


# --------------------------------------------------------------------------- helpers
def to_trimesh(m: Manifold):
    mesh = m.to_mesh()
    return trimesh.Trimesh(np.asarray(mesh.vert_properties)[:, :3], np.asarray(mesh.tri_verts), process=False)


def tube(r_in, r_out, z0, z1):
    return (Manifold.cylinder(z1 - z0, r_out, r_out, SEG) - Manifold.cylinder(z1 - z0, r_in, r_in, SEG)).translate([0, 0, z0])


def revolve(profile_rz):
    """Revolve a closed (r, z) polygon about the z axis."""
    return CrossSection([profile_rz]).revolve(SEG)


def rounded_rect_rz(r0, r1, z0, z1, rad, n=8):
    pts = []
    rad = min(rad, (r1 - r0) / 2, (z1 - z0) / 2)
    for cx, cz, a0 in ((r1 - rad, z0 + rad, -90), (r1 - rad, z1 - rad, 0), (r0 + rad, z1 - rad, 90), (r0 + rad, z0 + rad, 180)):
        for a in np.linspace(a0, a0 + 90, n):
            pts.append((cx + rad * np.cos(np.radians(a)), cz + rad * np.sin(np.radians(a))))
    return pts


def polar(m, n, phase=0.0):
    out = Manifold()
    for k in range(n):
        out += m.rotate([0, 0, phase + 360.0 * k / n])
    return out


def lugs(c: Cfg, z0, z1, phase=90.0):
    lug = Manifold.cylinder(z1 - z0, 4.5, 4.5, 48).translate([c.lug_r, 0, z0])
    web = Manifold.cube([c.lug_r - c.bore_r, 6.0, z1 - z0]).translate([c.bore_r + c.wall - 1, -3.0, z0])
    hole = Manifold.cylinder(z1 - z0 + 2, 1.7, 1.7, 32).translate([c.lug_r, 0, z0 - 1])
    return polar(lug + web, 3, phase), polar(hole, 3, phase)


# --------------------------------------------------------------------------- parts (each at its own origin)
def emitter_mount_ring(c: Cfg):
    body = revolve(rounded_rect_rz(c.ring_r - 1.25, c.ring_r + 1.25, -1.5, 1.5, 0.4))
    hole = Manifold.cylinder(4, c.pin_d / 2 + 0.02, c.pin_d / 2 + 0.02, 24).translate([c.ring_r, 0, -2])
    return body - polar(hole, c.n_pins)


def needle(c: Cfg):
    shank = Manifold.cylinder(3.0 + c.pin_len - 1.5, c.pin_d / 2, c.pin_d / 2, 24)
    tip = Manifold.cylinder(1.5, c.pin_d / 2, 0.05, 24).translate([0, 0, 3.0 + c.pin_len - 1.5])
    return (shank + tip).translate([0, 0, -1.5])          # 1.5 mm below ring mid-plane, tip at +pin_len above top face


def collector_tube(c: Cfg):
    return revolve(rounded_rect_rz(c.ring_r - c.coll_wall / 2, c.ring_r + c.coll_wall / 2, 0, c.coll_len, c.coll_wall / 2))


def carrier(c: Cfg, kind):
    """Insulating ring with 3 spokes holding an electrode, tie-rod lugs and a terminal boss."""
    t = c.carrier_t
    ring = tube(c.bore_r, c.bore_r + c.wall, -t / 2, t / 2)
    lug, lug_hole = lugs(c, -t / 2, t / 2)
    phase = 0.0 if kind == "emitter" else 60.0          # offset spokes to lengthen surface creepage paths
    spoke = Manifold.cube([c.bore_r + 0.5 - (c.ring_r - 2.5), 2.4, t / 2]).translate([c.ring_r - 2.5, -1.2, -t / 4])
    spokes = polar(spoke, 3, phase)
    boss = Manifold.cylinder(5, 2.5, 2.5, 32).rotate([0, 90, 0]).translate([c.bore_r + c.wall - 0.5, 0, 0]).rotate([0, 0, phase])
    channel = Manifold.cylinder(c.bore_r + c.wall + 6 - c.ring_r, 0.7, 0.7, 24).rotate([0, 90, 0]).translate([c.ring_r, 0, 0]).rotate([0, 0, phase])
    body = ring + lug + spokes + boss - lug_hole - channel
    if kind == "emitter":
        seat = revolve(rounded_rect_rz(c.ring_r - 1.35, c.ring_r + 1.35, -1.6, 1.6, 0.4))
        pins_clear = Manifold.cylinder(c.pin_len + 3, 0.9, 0.9, 16).translate([c.ring_r, 0, -1])
        body = body - seat - polar(pins_clear, c.n_pins)
    else:
        seat = tube(c.ring_r - c.coll_wall / 2 - 0.1, c.ring_r + c.coll_wall / 2 + 0.1, -t, t)
        body = body - seat
    return body


def spacer(c: Cfg, length):
    return tube(c.bore_r, c.bore_r + c.wall, 0, length)


def inlet_bellmouth(c: Cfg):
    """Rounded inlet: a 3 mm shell following a quarter-ellipse lip (8 mm radial, 10 mm axial), plus lugs."""
    R, H = 8.0, 10.0
    a = np.radians(np.linspace(0, 90, 24))
    inner = [(c.bore_r + R - R * np.cos(t), -H * np.sin(t)) for t in a]
    outer = [(r + c.wall, z) for r, z in inner][::-1]
    body = revolve(inner + outer) + tube(c.bore_r, c.bore_r + c.wall, 0, c.carrier_t)
    lug, hole = lugs(c, 0, c.carrier_t)
    return body + lug - hole


def exit_ring(c: Cfg):
    body = tube(c.bore_r, c.bore_r + c.wall, 0, c.carrier_t)
    lug, hole = lugs(c, 0, c.carrier_t)
    return body + lug - hole


def tie_rod(length):
    return Manifold.cylinder(length, 1.5, 1.5, 24)


def standoff(c: Cfg):
    # M3 threaded bore modelled at the 3 mm major diameter, so the tie rod threads straight in
    return Manifold.cylinder(c.standoff_len, 6, 6, 48) - Manifold.cylinder(c.standoff_len + 2, 1.5, 1.5, 24).translate([0, 0, -1])


def base_plate(c: Cfg):
    plate = Manifold.cube([140, 140, 6], center=True).translate([0, 0, -3])
    holes = polar(Manifold.cylinder(10, 1.7, 1.7, 24).translate([c.lug_r, 0, -8]), 3, 90)
    return plate - Manifold.cylinder(10, 32, 32, SEG).translate([0, 0, -8]) - holes


def terminal_pin():
    return Manifold.cylinder(8, 0.6, 0.6, 16) + Manifold.cylinder(2, 1.5, 1.5, 24).translate([0, 0, 8])


PART_INFO = {  # name: (material, density g/mm3, process, notes)
    "inlet_bellmouth": ("PETG or ASA", 1.27e-3, "3-D print", "Rounded inlet; faces down on the test stand"),
    "emitter_carrier": ("PETG or ASA", 1.27e-3, "3-D print", "Holds the emitter ring on 3 spokes; HV wire runs through the spoke at 0 deg"),
    "collector_carrier": ("PETG or ASA", 1.27e-3, "3-D print", "Spokes offset 60 deg from emitter spokes to lengthen creepage"),
    "spacer_gap": ("PETG or ASA", 1.27e-3, "3-D print", "Sets gap d; print several lengths to test d"),
    "spacer_stage": ("PETG or ASA", 1.27e-3, "3-D print", "Sets inter-stage spacing s"),
    "exit_ring": ("PETG or ASA", 1.27e-3, "3-D print", ""),
    "emitter_mount_ring": ("Brass", 8.5e-3, "Machine or bend + solder", "16 x 0.82 mm needle holes"),
    "needle": ("Stainless steel 304", 8.0e-3, "Buy (0.8 mm needle, ~50 um tip)", "Press-fit or clamp; do not solder"),
    "collector_tube": ("Aluminium 6061", 2.7e-3, "Cut from tube, deburr, round edges", "Simulations used a 4 mm-thick rounded section; 1 mm wall is lighter"),
    "terminal_pin": ("Brass", 8.5e-3, "Buy/turn", "HV feed (emitters) and ground return (collectors)"),
    "tie_rod": ("Nylon M3", 1.15e-3, "Buy, cut to length", "Insulating; holds the stack together"),
    "standoff": ("PTFE or acetal", 2.2e-3, "Machine/buy", "Insulates the thruster from the balance"),
    "base_plate": ("Polycarbonate or acetal", 1.2e-3, "Laser cut / machine", "Sits on the balance; 64 mm hole lets air in"),
}


def build(c: Cfg):
    parts = {
        "inlet_bellmouth": inlet_bellmouth(c), "emitter_carrier": carrier(c, "emitter"),
        "collector_carrier": carrier(c, "collector"), "spacer_gap": spacer(c, 0), "spacer_stage": spacer(c, 0),
        "exit_ring": exit_ring(c), "emitter_mount_ring": emitter_mount_ring(c), "needle": needle(c),
        "collector_tube": collector_tube(c), "terminal_pin": terminal_pin(), "standoff": standoff(c),
        "base_plate": base_plate(c),
    }
    t = c.carrier_t
    placed = []                          # (part, Manifold placed)
    z = 0.0
    placed.append(("inlet_bellmouth", parts["inlet_bellmouth"].translate([0, 0, -t - t / 2])))
    spacer_lengths = {}
    z_prev_end = -t / 2
    for k in range(c.n_stages):
        ze = z                                         # emitter ring plane
        if k == 0:
            # inlet ring ends at -t/2 (it is t long, placed from -1.5t to -t/2)
            pass
        else:
            L = ze - t / 2 - z_prev_end
            spacer_lengths["spacer_stage"] = L
            placed.append(("spacer_stage", spacer(c, L).translate([0, 0, z_prev_end])))
        placed.append(("emitter_carrier", parts["emitter_carrier"].translate([0, 0, ze])))
        placed.append(("emitter_mount_ring", parts["emitter_mount_ring"].translate([0, 0, ze])))
        for th in np.linspace(0, 360, c.n_pins, endpoint=False):
            placed.append(("needle", parts["needle"].translate([c.ring_r, 0, ze]).rotate([0, 0, th])))
        zc0 = ze + c.gap                               # collector leading edge
        zcc = zc0 + c.coll_len / 2                     # collector carrier mid-plane
        L = zcc - t / 2 - (ze + t / 2)
        spacer_lengths["spacer_gap"] = L
        placed.append(("spacer_gap", spacer(c, L).translate([0, 0, ze + t / 2])))
        placed.append(("collector_carrier", parts["collector_carrier"].translate([0, 0, zcc])))
        placed.append(("collector_tube", parts["collector_tube"].translate([0, 0, zc0])))
        placed.append(("terminal_pin", terminal_pin().rotate([0, 90, 0]).translate([c.bore_r + c.wall + 4.5, 0, ze])))
        placed.append(("terminal_pin", terminal_pin().rotate([0, 90, 0]).translate([c.bore_r + c.wall + 4.5, 0, zcc]).rotate([0, 0, 60])))
        z_prev_end = zcc + t / 2
        z = zc0 + c.spacing
    placed.append(("exit_ring", parts["exit_ring"].translate([0, 0, z_prev_end])))
    z_top = z_prev_end + t
    z_bot = -t - t / 2
    rod_len = z_top - z_bot + 8
    for th in (90, 210, 330):
        placed.append(("tie_rod", tie_rod(rod_len).translate([c.lug_r, 0, z_bot - 4]).rotate([0, 0, th])))
    for th in (90, 210, 330):
        placed.append(("standoff", parts["standoff"].translate([c.lug_r, 0, z_bot - c.standoff_len]).rotate([0, 0, th])))
    placed.append(("base_plate", parts["base_plate"].translate([0, 0, z_bot - c.standoff_len])))
    # unique-part STLs (spacers at their real lengths)
    parts["spacer_gap"] = spacer(c, spacer_lengths["spacer_gap"])
    if "spacer_stage" in spacer_lengths:
        parts["spacer_stage"] = spacer(c, spacer_lengths["spacer_stage"])
    else:
        parts.pop("spacer_stage")
    parts["tie_rod"] = tie_rod(rod_len)
    return parts, placed, spacer_lengths, (z_bot, z_top)


COLORS = {"inlet_bellmouth": "#e5e7eb", "emitter_carrier": "#c7d2fe", "collector_carrier": "#fde68a",
          "spacer_gap": "#e5e7eb", "spacer_stage": "#e5e7eb", "exit_ring": "#e5e7eb",
          "emitter_mount_ring": "#b45309", "needle": "#64748b", "collector_tube": "#9ca3af",
          "terminal_pin": "#b45309", "tie_rod": "#f5f5f4", "standoff": "#f8fafc", "base_plate": "#bae6fd"}


def interference(placed, tol=0.5):
    """Volume (mm3) of every overlapping pair of placed parts; returns pairs above tol."""
    boxes = [m.bounding_box() for _, m in placed]
    clashes = []
    for i in range(len(placed)):
        for j in range(i + 1, len(placed)):
            a, b = boxes[i], boxes[j]
            if any(a[k] > b[k + 3] or b[k] > a[k + 3] for k in range(3)):
                continue
            v = (placed[i][1] ^ placed[j][1]).volume()
            if v > tol:
                clashes.append((placed[i][0], placed[j][0], round(v, 2)))
    return clashes


def write_outputs(c: Cfg):
    parts, placed, spacer_lengths, (z_bot, z_top) = build(c)
    clashes = interference(placed)
    with open(OUT / f"interference_{c.n_stages}stage.txt", "w") as f:
        f.write(f"Pairwise overlap check of {len(placed)} placed parts (tolerance 0.5 mm3)\n")
        f.write("\n".join(f"{a} x {b}: {v} mm3" for a, b, v in clashes) or "No interferences found.")
        f.write("\n")
    stl = OUT / "stl"; stl.mkdir(parents=True, exist_ok=True)
    rows = []
    counts = {}
    for name, _ in placed:
        counts[name] = counts.get(name, 0) + 1
    for name, m in parts.items():
        tm = to_trimesh(m)
        assert tm.is_watertight, name
        tm.export(stl / (f"{name}_{c.n_stages}stage.stl" if name == "tie_rod" else f"{name}.stl"))
        mat, rho, proc, note = PART_INFO[name]
        vol = m.volume()
        ext = tm.bounds[1] - tm.bounds[0]
        rows.append({"part": name, "qty": counts.get(name, 0), "material": mat, "process": proc,
                     "envelope_mm": " x ".join(f"{e:.1f}" for e in ext), "volume_mm3": round(vol, 1),
                     "mass_each_g": round(vol * rho, 2), "mass_total_g": round(vol * rho * counts.get(name, 0), 2),
                     "notes": note})
    with open(OUT / f"bom_{c.n_stages}stage.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    # assembly
    scene = [to_trimesh(m) for _, m in placed]
    trimesh.util.concatenate(scene).export(OUT / f"assembly_{c.n_stages}stage.stl")
    viewer(c, placed)
    render(c, placed)
    flying = sum(r["mass_total_g"] for r in rows if r["part"] not in ("standoff", "base_plate"))
    return rows, spacer_lengths, flying, z_top - z_bot, clashes


def viewer(c, placed):
    import plotly.graph_objects as go
    by = {}
    for name, m in placed:
        by.setdefault(name, []).append(to_trimesh(m))
    fig = go.Figure()
    for name, ms in by.items():
        tm = trimesh.util.concatenate(ms)
        v, f = tm.vertices, tm.faces
        fig.add_trace(go.Mesh3d(x=v[:, 0], y=v[:, 1], z=v[:, 2], i=f[:, 0], j=f[:, 1], k=f[:, 2], name=name,
                                color=COLORS[name], opacity=0.35 if "carrier" in name or "spacer" in name or name in
                                ("inlet_bellmouth", "exit_ring") else 1.0, showlegend=True, flatshading=False))
    fig.update_layout(title=f"{c.n_stages}-stage EHD thruster (design proposal, not built): click legend to hide parts",
                      scene=dict(aspectmode="data", xaxis_title="x (mm)", yaxis_title="y (mm)", zaxis_title="z (mm), flow up"),
                      margin=dict(l=0, r=0, t=40, b=0))
    fig.write_html(OUT / f"viewer_{c.n_stages}stage.html", include_plotlyjs="cdn")


def render(c, placed):
    """2-D section drawing through the axis (plane y = 0) and a 3-D exterior view."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    fig, ax = plt.subplots(figsize=(6, 12))
    seen = set()
    for name, m in placed:
        tm = to_trimesh(m)
        sec = tm.section(plane_origin=[0, 0.001, 0], plane_normal=[0, 1, 0])
        if sec is None:
            continue
        for poly in sec.discrete:
            ax.fill(poly[:, 0], poly[:, 2], color=COLORS[name], ec="#333", lw=0.3)
        seen.add(name)
    ax.set_aspect("equal"); ax.set_xlabel("x (mm)"); ax.set_ylabel("z (mm), air flows upward")
    ax.set_title(f"{c.n_stages}-stage thruster: section through the axis\n(design proposal, not built)", fontsize=10)
    ax.legend(handles=[Patch(color=COLORS[n], label=n) for n in COLORS if n in seen], fontsize=7,
              loc="upper left", bbox_to_anchor=(1.02, 1))
    ax.grid(alpha=0.3)
    fig.savefig(ROOT / "diagrams" / f"cad_{c.n_stages}stage_section.png", dpi=130, bbox_inches="tight")
    plt.close(fig)

    fig = plt.figure(figsize=(6, 10))
    ax = fig.add_subplot(111, projection="3d")
    allm = Manifold()
    for name, m in placed:
        allm += m
    tm = to_trimesh(allm)
    tm = tm.simplify_quadric_decimation(face_count=60000) if len(tm.faces) > 60000 else tm
    light = np.array([0.4, -0.6, 0.7]); light /= np.linalg.norm(light)
    shade = 0.45 + 0.55 * np.clip(tm.face_normals @ light, 0, 1)
    pc = Poly3DCollection(tm.vertices[tm.faces], facecolors=np.c_[shade * 0.75, shade * 0.8, shade * 0.9],
                          edgecolor="none")
    ax.add_collection3d(pc)
    lo, hi = tm.bounds
    ax.set_xlim(lo[0], hi[0]); ax.set_ylim(lo[1], hi[1]); ax.set_zlim(lo[2], hi[2])
    ax.set_box_aspect(hi - lo); ax.view_init(elev=15, azim=-60); ax.set_axis_off()
    ax.set_title(f"{c.n_stages}-stage thruster on its test stand (exterior)", fontsize=10)
    fig.savefig(ROOT / "diagrams" / f"cad_{c.n_stages}stage_exterior.png", dpi=130, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    for n in (2, 3):
        rows, sl, flying, length, clashes = write_outputs(Cfg(n_stages=n))
        print(f"{n}-stage: {len(rows)} unique parts, spacers {sl}, flying mass {flying:.1f} g, stack {length:.1f} mm, "
              f"clashes: {clashes or 'none'}")
