"""Shared chart style: consistent colours, provenance footer, PNG + SVG export."""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
CHARTS = ROOT / "charts"
DATA = ROOT / "data"

# One colour per recurring configuration, used in every chart.
COLORS = {
    "1-stage": "#6b7280",
    "2-stage": "#2563eb",
    "3-stage": "#d97706",
    "equal": "#2563eb",
    "decreasing": "#dc2626",
    "increasing": "#059669",
    "optimised": "#7c3aed",
    "thrust": "#2563eb",
    "efficiency": "#dc2626",
    "power": "#d97706",
    "flow": "#059669",
    "margin": "#7c3aed",
}

SOURCE_TAGS = {
    "sim": "Source: numerical simulation, reduced-order CSM + Townsend model (unvalidated)",
    "analytic": "Source: analytical calculation",
    "qual": "Source: qualitative engineering assessment (not measured data)",
    "illus": "Source: illustrative hypothetical example",
}

plt.rcParams.update({
    "figure.dpi": 110, "savefig.dpi": 160, "font.size": 10, "axes.titlesize": 12,
    "axes.titleweight": "bold", "axes.grid": True, "grid.alpha": 0.3,
    "axes.spines.top": False, "axes.spines.right": False, "legend.frameon": False,
})


def footer(fig, source="sim", assumptions=""):
    text = SOURCE_TAGS[source]
    if assumptions:
        text += "\n" + assumptions
    fig.text(0.01, 0.005, text, fontsize=7, color="#555", va="bottom", ha="left", wrap=True)


def save(fig, name, source="sim", assumptions="", bottom=0.16):
    footer(fig, source, assumptions)
    fig.subplots_adjust(bottom=bottom)
    CHARTS.mkdir(exist_ok=True)
    for ext in ("png", "svg"):
        fig.savefig(CHARTS / f"{name}.{ext}", bbox_inches="tight")
    plt.close(fig)
    return CHARTS / f"{name}.png"
