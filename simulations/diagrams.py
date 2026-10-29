"""Engineering diagrams (drawn to scale from the reference geometry) -> diagrams/*.png|svg.

Run: .venv/bin/python simulations/diagrams.py
"""
import sys
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyArrowPatch, Rectangle

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ehd import plotting  # noqa: E402

OUT = plotting.ROOT / "diagrams"
EMIT, COLL, HOUSE = "#2563eb", "#b45309", "#d1d5db"


def dim(ax, x0, x1, y, text, above=True):
    ax.add_patch(FancyArrowPatch((x0, y), (x1, y), arrowstyle="<->", mutation_scale=8, lw=0.8, color="k"))
    ax.text((x0 + x1) / 2, y + (1.2 if above else -2.6), text, ha="center", fontsize=8)


TIP = 7.5        # needle tip height above the emitter ring mid-plane (matches cad/build.py)
COLL_LEN = 10.0  # collector tube length


def section(n, gaps, spacings, name, title):
    """gaps: needle tip -> collector leading edge; spacings: collector leading edge -> next emitter ring."""
    bore_r, ring_r = 20, 15
    fig, ax = plt.subplots(figsize=(11, 4.6))
    z = 0
    zs = []
    for k in range(n):
        if k:
            z += spacings[k - 1]
        ze, zc = z, z + TIP + gaps[k]
        zs.append((ze, zc))
        z = zc
    length = z + COLL_LEN + 10
    for sgn in (1, -1):
        ax.add_patch(Rectangle((-10, sgn * bore_r), length + 10, sgn * 3, color=HOUSE))
        for k, (ze, zc) in enumerate(zs):
            ax.add_patch(Rectangle((ze - 1.5, sgn * ring_r - 1.25), 3, 2.5, color="#c99a2e", zorder=3))   # brass ring
            ax.plot([ze, ze + TIP], [sgn * ring_r, sgn * ring_r], color=EMIT, lw=1.6, zorder=4)            # needle
            ax.plot([ze, ze], [sgn * (ring_r + 1.25), sgn * bore_r], color="#888", lw=0.8)              # spoke
            ax.add_patch(Rectangle((zc, sgn * ring_r - 0.5), COLL_LEN, 1.0, color=COLL, zorder=3))       # tube collector
            ax.plot([zc + COLL_LEN / 2] * 2, [sgn * (ring_r + 0.5), sgn * bore_r], color="#888", lw=0.8)
            if sgn == 1:
                ax.text(ze, ring_r + 7, f"E{k+1}\n+V", ha="center", fontsize=8, color=EMIT)
                ax.text(zc + COLL_LEN / 2, ring_r + 7, f"C{k+1}\n0 V", ha="center", fontsize=8, color=COLL)
    ax.axhline(0, color="#999", ls="-.", lw=0.7)
    for k, (ze, zc) in enumerate(zs):
        dim(ax, ze + TIP, zc, -ring_r - 6, f"d{k+1} = {gaps[k]:.0f}", above=False)
        if k:
            dim(ax, zs[k - 1][1], ze, -ring_r - 11, f"s{k} = {spacings[k-1]:.0f}", above=False)
    ax.annotate("", xy=(length + 5, 0), xytext=(-12, 0), arrowprops=dict(arrowstyle="->", color="#059669", lw=2))
    ax.text(-12, 2, "air in", color="#059669", fontsize=9); ax.text(length - 6, 2, "jet out", color="#059669", fontsize=9)
    ax.plot([-6, -6], [-bore_r, bore_r], "k", lw=0.6); ax.text(-8, -10, "bore 40", rotation=90, va="center", fontsize=8)
    ax.text(zs[0][0] + 2, ring_r - 4.5, "ring dia 30", fontsize=7)
    ax.set_aspect("equal"); ax.set_xlim(-16, length + 8); ax.set_ylim(-bore_r - 14, bore_r + 14)
    ax.set_xlabel("axial position (mm)"); ax.set_ylabel("radius (mm)"); ax.set_title(title)
    ax.grid(False)
    plotting.footer(fig, "illus", "Section through the axis, to scale (mm). Emitter: brass ring with 16 stainless needles "
                    "(blue); d is measured from the needle tips. Collector: 10 mm aluminum tube. Grey lines: insulating spokes.")
    OUT.mkdir(exist_ok=True)
    for ext in ("png", "svg"):
        fig.savefig(OUT / f"{name}.{ext}", bbox_inches="tight")
    plt.close(fig)


def pin_orientations():
    fig, axs = plt.subplots(1, 5, figsize=(13, 3.2))
    s = np.sqrt(0.5)
    dirs = {"axial": (0, 1), "angled in": (-s, s), "angled out": (s, s), "radial out": (1, 0), "radial in": (-1, 0)}
    for ax, (name, (dr, dz)) in zip(axs, dirs.items()):
        ax.add_patch(Circle((0, 15), 0.6, color=EMIT))
        ax.plot([0, 6 * dz], [15, 15 + 6 * dr], color=EMIT, lw=2.5, solid_capstyle="round")
        ax.add_patch(Circle((25, 15), 2, color=COLL))
        ax.axhline(0, color="#999", ls="-.", lw=0.7); ax.axhline(20, color=HOUSE, lw=4)
        ax.annotate("", xy=(30, 3), xytext=(-4, 3), arrowprops=dict(arrowstyle="->", color="#059669"))
        ax.set_title(name, fontsize=10); ax.set_aspect("equal"); ax.set_xlim(-6, 31); ax.set_ylim(-2, 23)
        ax.set_xticks([]); ax.set_yticks([]); ax.grid(False)
    fig.suptitle("Pin orientations modelled (r-z section; axis at bottom, bore wall at top, flow left to right)",
                 fontweight="bold")
    plotting.footer(fig, "illus", "Pins 6 mm long on a 30 mm ring; collector 25 mm downstream of the ring.")
    for ext in ("png", "svg"):
        fig.savefig(OUT / f"pin_orientations.{ext}", bbox_inches="tight")
    plt.close(fig)


def pin_ring_front():
    fig, axs = plt.subplots(1, 3, figsize=(11, 4))
    for ax, n in zip(axs, (8, 16, 32)):
        ax.add_patch(Circle((0, 0), 20, fill=False, lw=3, color=HOUSE))
        ax.add_patch(Circle((0, 0), 15, fill=False, lw=1.5, color=EMIT))
        for th in np.linspace(0, 2 * np.pi, n, endpoint=False):
            ax.plot(15 * np.cos(th), 15 * np.sin(th), "o", color=EMIT, ms=4)
        spacing = 2 * np.pi * 15 / n
        ax.set_title(f"{n} pins: spacing {spacing:.1f} mm", fontsize=10)
        ax.set_aspect("equal"); ax.set_xlim(-23, 23); ax.set_ylim(-23, 23); ax.set_xticks([]); ax.set_yticks([])
        ax.grid(False)
    fig.suptitle("Pin ring seen along the axis (pin length 6 mm; model optimum near spacing ≈ pin length)",
                 fontweight="bold")
    plotting.footer(fig, "illus", "30 mm pin circle inside a 40 mm bore.")
    for ext in ("png", "svg"):
        fig.savefig(OUT / f"pin_ring_front.{ext}", bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    section(2, [25, 25], [75], "two_stage_section", "Recommended two-stage build: d = 25 mm, s = 75 mm (3d), one supply")
    section(3, [25, 25, 25], [75, 75], "three_stage_section", "Three-stage variant: d = 25 mm, s = 75 mm (3d), one supply")
    pin_orientations()
    pin_ring_front()
    print("done")
