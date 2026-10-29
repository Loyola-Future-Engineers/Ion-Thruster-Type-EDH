"""Prototype P1 drawing package: dimensioned assembly, exploded stack and per-part drawings.

All dimensions come from the parametric CAD model (cad/build.py). They are design dimensions,
not measurements of a built part.

Writes (in prototypes/):
  P1_assembled_section.png|svg     fully assembled, dimensioned section, coloured by material
  P1_exploded_section.png|svg      the stack pulled apart in assembly order, every part labelled
  P1_parts_sheet.png|svg           every unique part on its own with dimensions, material and quantity
  P1_exploded.stl, P1_viewer_exploded.html   3-D exploded model and interactive viewer
  P1_parts_list.csv                parts, materials, dimensions, masses

Run: .venv/bin/python prototypes/build_drawings.py
"""
import csv
import importlib.util
from pathlib import Path

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402
import trimesh  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "prototypes"
spec = importlib.util.spec_from_file_location("cadbuild", ROOT / "cad" / "build.py")
cad = importlib.util.module_from_spec(spec); spec.loader.exec_module(cad)

C = cad.Cfg(n_stages=2)
MAT_COLOR = {"Brass": "#c99a2e", "Stainless steel 304": "#6b7785", "Aluminium 6061": "#aeb9c6",
             "PETG or ASA": "#dbe4f0", "Nylon M3": "#f1efe6", "PTFE or acetal": "#fafafa",
             "Polycarbonate or acetal": "#bfe0f2"}
LABEL = {"inlet_bellmouth": "Inlet bellmouth", "emitter_carrier": "Emitter carrier", "collector_carrier":
         "Collector carrier", "spacer_gap": "Gap spacer", "spacer_stage": "Stage spacer", "exit_ring": "Exit ring",
         "emitter_mount_ring": "Emitter mounting ring", "needle": "Emitter needle", "collector_tube": "Collector tube",
         "terminal_pin": "Terminal pin", "tie_rod": "Tie rod", "standoff": "Insulating standoff",
         "base_plate": "Base plate"}
KEY_DIMS = {  # human-readable key dimensions, mm (from the CAD parameters)
    "inlet_bellmouth": "Ø40 bore, Ø62 lip, 16 tall, 3 wall",
    "emitter_carrier": "Ø40 / Ø46 ring, 6 thick, 3 spokes 2.4 wide, Ø1.4 wire channel",
    "collector_carrier": "Ø40 / Ø46 ring, 6 thick, 3 spokes (60° offset)",
    "spacer_gap": "Ø40 / Ø46 tube, 24 long",
    "spacer_stage": "Ø40 / Ø46 tube, 64 long",
    "exit_ring": "Ø40 / Ø46 ring, 6 thick",
    "emitter_mount_ring": "Ø30 mean, 2.5 × 3 section, 16 holes Ø0.82",
    "needle": "Ø0.8 × 9 (6 exposed), tip radius ≈ 0.05",
    "collector_tube": "Ø30 mean, 1 wall, 10 long, edges R0.5",
    "terminal_pin": "Ø1.2 × 8 shank, Ø3 head",
    "tie_rod": "M3 × 156",
    "standoff": "Ø12 × 100, M3 tapped through",
    "base_plate": "140 × 140 × 6, Ø64 air hole",
}


def section(m, y=0.001):
    tm = cad.to_trimesh(m)
    sec = tm.section(plane_origin=[0, y, 0], plane_normal=[0, 1, 0])
    return [] if sec is None else [p[:, [0, 2]] for p in sec.discrete]


def top_section(m):
    tm = cad.to_trimesh(m)
    zmid = 0.5 * (tm.bounds[0, 2] + tm.bounds[1, 2])
    sec = tm.section(plane_origin=[0, 0, zmid], plane_normal=[0, 0, 1])
    return [] if sec is None else [p[:, :2] for p in sec.discrete]


def fill(ax, loops, fc, lw=0.4):
    """Fill closed section loops with the even-odd rule, so holes stay open."""
    from matplotlib.path import Path as MPath
    from matplotlib.patches import PathPatch
    from shapely.geometry import Polygon
    shape = None
    for lp in loops:
        if len(lp) < 3:
            continue
        pg = Polygon(lp).buffer(0)
        shape = pg if shape is None else shape.symmetric_difference(pg)
    if shape is None or shape.is_empty:
        return
    geoms = getattr(shape, "geoms", [shape])
    for g in geoms:
        if g.geom_type != "Polygon":
            continue
        verts, codes = [], []
        for ring in [g.exterior, *g.interiors]:
            xy = np.asarray(ring.coords)
            verts += xy.tolist(); codes += [MPath.MOVETO] + [MPath.LINETO] * (len(xy) - 2) + [MPath.CLOSEPOLY]
        ax.add_patch(PathPatch(MPath(verts, codes), fc=fc, ec="#333", lw=lw))


def color(name):
    return MAT_COLOR[cad.PART_INFO[name][0]]


def dim(ax, p0, p1, text, off=(0, 0), fs=7, color="k"):
    (x0, y0), (x1, y1) = p0, p1
    ax.annotate("", xy=(x1, y1), xytext=(x0, y0), arrowprops=dict(arrowstyle="<->", lw=0.7, color=color,
                                                                   shrinkA=0, shrinkB=0))
    ax.text((x0 + x1) / 2 + off[0], (y0 + y1) / 2 + off[1], text, fontsize=fs, ha="center", va="center",
            color=color, bbox=dict(fc="white", ec="none", pad=0.6))


def material_legend(ax, loc="upper left", anchor=(1.01, 1)):
    ax.legend(handles=[Patch(fc=c, ec="#333", lw=0.5, label=m) for m, c in MAT_COLOR.items()],
              title="Material", fontsize=7, title_fontsize=8, loc=loc, bbox_to_anchor=anchor, frameon=False)


def assembled(parts, placed):
    fig, ax = plt.subplots(figsize=(9, 13))
    for name, m in placed:
        fill(ax, section(m), color(name), 0.35)
    t = C.carrier_t
    z_e = [0.0, C.gap + C.spacing]
    z_c = [z + C.gap for z in z_e]
    thr = [cad.to_trimesh(m).bounds for n, m in placed if n not in ("standoff", "base_plate", "tie_rod")]
    zlo = min(b[0, 2] for b in thr); zhi = max(b[1, 2] for b in thr)
    # dimensions (right side)
    xr = 52
    dim(ax, (xr, zlo), (xr, zhi), f"{zhi - zlo:.0f}\noverall", off=(7, 0))
    dim(ax, (34, z_e[0]), (34, z_c[0]), f"d = {C.gap:.0f}", off=(7, 0))
    dim(ax, (34, z_c[0]), (34, z_e[1]), f"s = {C.spacing:.0f}", off=(7, 0))
    dim(ax, (34, z_e[1]), (34, z_c[1]), f"d = {C.gap:.0f}", off=(7, 0))
    dim(ax, (-C.bore_r, z_c[0] + 50), (C.bore_r, z_c[0] + 50), "Ø40 bore", off=(0, 3))
    dim(ax, (-C.bore_r - C.wall, zhi + 8), (C.bore_r + C.wall, zhi + 8), "Ø46 housing", off=(0, 3))
    dim(ax, (-C.ring_r, z_c[0] + 22), (C.ring_r, z_c[0] + 22), "Ø30 rings", off=(0, 3), fs=6.5)
    dim(ax, (-C.ring_r - 3, z_e[0] + 1.5), (-C.ring_r - 3, z_e[0] + 1.5 + C.pin_len), "6", off=(-3, 0), fs=6)
    dim(ax, (-24, z_c[0]), (-24, z_c[0] + C.coll_len), f"{C.coll_len:.0f}", off=(-4, 0), fs=6)
    zb = -t - t / 2 - C.standoff_len
    # standoffs and tie rods lie outside the section plane: draw their projected outlines dashed
    xs = C.lug_r * np.cos(np.radians(210))
    ax.add_patch(plt.Rectangle((xs - 6, zb), 12, C.standoff_len, fill=False, ls="--", lw=0.7, ec="#555"))
    ax.plot([xs, xs], [zb + C.standoff_len, zhi], ls="--", lw=0.6, color="#555")
    ax.text(xs, zb + C.standoff_len / 2, "PTFE\nstandoff\n(behind\nsection)", fontsize=6, ha="center", va="center")
    ax.text(xs - 2, zhi - 60, "nylon tie rod\n(behind section)", fontsize=6, ha="right", rotation=90, va="center")
    dim(ax, (xs - 12, zb), (xs - 12, -t - t / 2), f"{C.standoff_len:.0f}", off=(-4, 0))
    dim(ax, (-70, zb - 14), (70, zb - 14), "140 base plate (Ø64 air hole)", off=(0, 3))
    dim(ax, (-C.lug_r, zhi + 18), (C.lug_r, zhi + 18), f"Ø{2 * C.lug_r:.0f} tie-rod circle", off=(0, 3))
    # callouts (left)
    calls = [("Exit ring", zhi - 3), ("Collector tube C2 (Al)", z_c[1] + 5), ("Emitter E2: brass ring + 16 needles", z_e[1] + 3),
             ("Stage spacer (s)", z_c[0] + 45), ("Collector tube C1 (Al)", z_c[0] + 5), ("Gap spacer (d)", z_e[0] + 15),
             ("Emitter E1: brass ring + 16 needles", z_e[0] + 3), ("Inlet bellmouth", -14)]
    for text, z in calls:
        ax.annotate(text, xy=(-C.ring_r if "Emitter" in text or "Collector" in text else -C.bore_r - 1.5, z),
                    xytext=(-118, z), fontsize=7, va="center", arrowprops=dict(arrowstyle="-", lw=0.5, color="#555"))
    for z, txt in ((z_e[0], "HV terminal"), (z_e[1], "HV terminal")):
        ax.text(C.bore_r + C.wall + 10, z - 5, txt, fontsize=6.5, ha="center", va="top")
    ax.set_aspect("equal"); ax.set_xlim(-125, 75); ax.set_ylim(zb - 22, zhi + 26)
    ax.set_xlabel("mm"); ax.set_ylabel("mm (air flows upward)"); ax.grid(alpha=0.2)
    ax.set_title("Prototype P1, two stages, fully assembled: section through the axis\n"
                 "design dimensions in mm (not yet built or measured)", fontsize=10)
    material_legend(ax)
    for ext in ("png", "svg"):
        fig.savefig(OUT / f"P1_assembled_section.{ext}", dpi=150, bbox_inches="tight")
    plt.close(fig)


def exploded(placed):
    """Pull the stack apart along the axis in assembly order."""
    stack = [(n, m) for n, m in placed if n not in ("standoff", "base_plate", "tie_rod", "terminal_pin")]
    levels = sorted({round(cad.to_trimesh(m).bounds[0, 2], 1) for n, m in stack if n != "needle"})
    def level(m, name):
        zmin = round(cad.to_trimesh(m).bounds[0, 2], 1)
        if name == "needle":
            zmin = round(zmin, 1)
        return min(range(len(levels)), key=lambda i: abs(levels[i] - zmin))
    gap = 22.0
    moved = [(n, m.translate([0, 0, level(m, n) * gap])) for n, m in stack]
    pins = [(n, m) for n, m in placed if n == "terminal_pin"]
    for n, m in pins:      # terminal pins pulled outward radially from their carrier, then lifted with it
        b = cad.to_trimesh(m).bounds
        lv = min(range(len(levels)), key=lambda i: abs(levels[i] - (b[0, 2] - 2)))
        c = 0.5 * (b[0] + b[1]); r = np.hypot(c[0], c[1])
        moved.append((n, m.translate([12 * c[0] / r, 12 * c[1] / r, lv * gap + 0])))
    trimesh.util.concatenate([cad.to_trimesh(m) for _, m in moved]).export(OUT / "P1_exploded.stl")
    # interactive viewer
    import plotly.graph_objects as go
    fig = go.Figure()
    by = {}
    for n, m in moved:
        by.setdefault(n, []).append(cad.to_trimesh(m))
    for n, ms in by.items():
        tm = trimesh.util.concatenate(ms)
        v, f = tm.vertices, tm.faces
        fig.add_trace(go.Mesh3d(x=v[:, 0], y=v[:, 1], z=v[:, 2], i=f[:, 0], j=f[:, 1], k=f[:, 2],
                                name=f"{LABEL[n]} ({cad.PART_INFO[n][0]})", color=color(n), showlegend=True,
                                opacity=0.5 if cad.PART_INFO[n][0].startswith("PETG") else 1.0))
    fig.update_layout(title="Prototype P1: exploded view (design, not built). Click the legend to hide parts.",
                      scene=dict(aspectmode="data"), margin=dict(l=0, r=0, t=40, b=0))
    fig.write_html(OUT / "P1_viewer_exploded.html", include_plotlyjs="cdn")
    # 2-D exploded section with labels
    fig, ax = plt.subplots(figsize=(9, 16))
    labelled = set()
    for n, m in moved:
        fill(ax, section(m), color(n), 0.35)
    for n, m in moved:
        b = cad.to_trimesh(m).bounds
        key = (n, round(b[0, 2]))
        if key in labelled or n == "needle" or not section(m):
            continue
        labelled.add(key)
        zc = 0.5 * (b[0, 2] + b[1, 2])
        x_edge = b[1, 0]
        zt = zc - 8 if n == "terminal_pin" else zc
        ax.annotate(f"{LABEL[n]} — {cad.PART_INFO[n][0]}", xy=(min(x_edge, 50), zc), xytext=(62, zt), fontsize=7,
                    va="center", arrowprops=dict(arrowstyle="-", lw=0.5, color="#555"))
    for n, m in moved:
        if n == "needle":
            b = cad.to_trimesh(m).bounds
            key = ("needle", round(b[0, 2]))
            if key not in labelled:
                labelled.add(key)
                ax.annotate(f"16 × Emitter needle — {cad.PART_INFO['needle'][0]}", xy=(-C.ring_r, b[1, 2]),
                            xytext=(-105, b[1, 2] + 4), fontsize=7, va="center",
                            arrowprops=dict(arrowstyle="-", lw=0.5, color="#555"))
    ax.set_aspect("equal"); ax.set_xlim(-110, 170); ax.grid(alpha=0.2)
    ax.set_xlabel("mm"); ax.set_ylabel("mm (assembly order, inlet at the bottom)")
    ax.set_title("Prototype P1: exploded stack in assembly order (section through the axis)\n"
                 "tie rods, standoffs and base plate are shown on the parts sheet", fontsize=10)
    material_legend(ax)
    for ext in ("png", "svg"):
        fig.savefig(OUT / f"P1_exploded_section.{ext}", dpi=150, bbox_inches="tight")
    plt.close(fig)


def parts_sheet(parts, counts):
    order = ["inlet_bellmouth", "emitter_carrier", "emitter_mount_ring", "needle", "spacer_gap", "collector_carrier",
             "collector_tube", "spacer_stage", "exit_ring", "terminal_pin", "tie_rod", "standoff", "base_plate"]
    top_view = {"inlet_bellmouth", "emitter_carrier", "collector_carrier", "emitter_mount_ring", "exit_ring", "base_plate"}
    panels = []
    for n in order:
        panels.append((n, "side"))
        if n in top_view:
            panels.append((n, "top"))
    cols = 4
    rows = int(np.ceil(len(panels) / cols))
    fig, axs = plt.subplots(rows, cols, figsize=(16, 3.9 * rows))
    rows_csv = []
    for ax, (n, view) in zip(axs.flat, panels):
        m = parts[n]
        polys = section(m) if view == "side" else top_section(m)
        fill(ax, polys, color(n), 0.5)
        tm = cad.to_trimesh(m)
        lo, hi = tm.bounds
        if view == "side":
            w, h = hi[0] - lo[0], hi[2] - lo[2]
            dim(ax, (lo[0], lo[2] - 0.12 * h - 0.4), (hi[0], lo[2] - 0.12 * h - 0.4), f"{w:.1f}", fs=7)
            dim(ax, (hi[0] + 0.08 * w + 0.3, lo[2]), (hi[0] + 0.08 * w + 0.3, hi[2]), f"{h:.1f}", fs=7)
            pad = max(w, h) * 0.25 + 1
            ax.set_xlim(lo[0] - pad * 0.3, hi[0] + pad); ax.set_ylim(lo[2] - pad, hi[2] + pad * 0.3)
        else:
            w = hi[0] - lo[0]; d = hi[1] - lo[1]
            dim(ax, (lo[0], lo[1] - 0.1 * d - 0.4), (hi[0], lo[1] - 0.1 * d - 0.4), f"{w:.1f}", fs=7)
            pad = max(w, d) * 0.2 + 1
            ax.set_xlim(lo[0] - pad * 0.3, hi[0] + pad * 0.3); ax.set_ylim(lo[1] - pad, hi[1] + pad * 0.3)
        mat = cad.PART_INFO[n][0]
        ax.set_title(f"{LABEL[n]}  ×{counts[n]}  ({'section' if view == 'side' else 'top view'})\n{mat}",
                     fontsize=8.5)
        ax.text(0.5, -0.02, KEY_DIMS[n], transform=ax.transAxes, ha="center", va="top", fontsize=7, color="#333")
        ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
        for s in ax.spines.values():
            s.set_color("#ccc")
        if view == "side":
            vol = m.volume(); rho = cad.PART_INFO[n][1]
            rows_csv.append({"part": LABEL[n], "file": f"cad/stl/{n}{'_2stage' if n == 'tie_rod' else ''}.stl",
                             "qty": counts[n], "material": mat, "key_dimensions_mm": KEY_DIMS[n],
                             "envelope_mm": f"{hi[0]-lo[0]:.1f} x {hi[1]-lo[1]:.1f} x {hi[2]-lo[2]:.1f}",
                             "mass_each_g": round(vol * rho, 2), "mass_total_g": round(vol * rho * counts[n], 2),
                             "process": cad.PART_INFO[n][2]})
    for ax in list(axs.flat)[len(panels):]:
        ax.axis("off")
    fig.suptitle("Prototype P1: every part, separated (design dimensions in mm; each panel has its own scale)",
                 fontsize=12, fontweight="bold")
    fig.legend(handles=[Patch(fc=c, ec="#333", lw=0.5, label=mm) for mm, c in MAT_COLOR.items()],
               loc="lower center", ncol=7, fontsize=8, frameon=False, bbox_to_anchor=(0.5, -0.005))
    fig.tight_layout(rect=(0, 0.02, 1, 0.97))
    for ext in ("png", "svg"):
        fig.savefig(OUT / f"P1_parts_sheet.{ext}", dpi=140, bbox_inches="tight")
    plt.close(fig)
    with open(OUT / "P1_parts_list.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows_csv[0])); w.writeheader(); w.writerows(rows_csv)
    return rows_csv


if __name__ == "__main__":
    parts, placed, _, _ = cad.build(C)
    counts = {}
    for n, _ in placed:
        counts[n] = counts.get(n, 0) + 1
    assembled(parts, placed)
    exploded(placed)
    rows = parts_sheet(parts, counts)
    flying = sum(r["mass_total_g"] for r in rows if r["part"] not in ("Insulating standoff", "Base plate"))
    print(f"{len(rows)} parts, flying mass {flying:.1f} g")
