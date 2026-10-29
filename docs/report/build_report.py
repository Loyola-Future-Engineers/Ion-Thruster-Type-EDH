"""Build the project report PDF (docs/report/Ion_Thruster_Type_EDH_report.pdf) from the repository's results.

Run: .venv/bin/python docs/report/build_report.py
"""
from pathlib import Path

import matplotlib
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "report" / "Ion_Thruster_Type_EDH_report.pdf"
FONT_DIR = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
pdfmetrics.registerFont(TTFont("DV", str(FONT_DIR / "DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont("DVB", str(FONT_DIR / "DejaVuSans-Bold.ttf")))
pdfmetrics.registerFont(TTFont("DVI", str(FONT_DIR / "DejaVuSans-Oblique.ttf")))
pdfmetrics.registerFontFamily("DV", normal="DV", bold="DVB", italic="DVI")

ss = getSampleStyleSheet()
BODY = ParagraphStyle("body", parent=ss["BodyText"], fontName="DV", fontSize=9.5, leading=13.5, spaceAfter=5)
SMALL = ParagraphStyle("small", parent=BODY, fontSize=7.5, leading=10, textColor=colors.HexColor("#444"))
H1 = ParagraphStyle("h1", parent=ss["Heading1"], fontName="DVB", fontSize=16, spaceBefore=4, spaceAfter=8,
                    textColor=colors.HexColor("#1e3a8a"))
H2 = ParagraphStyle("h2", parent=ss["Heading2"], fontName="DVB", fontSize=12, spaceBefore=8, spaceAfter=4)
TITLE = ParagraphStyle("title", parent=H1, fontSize=26, leading=32, alignment=TA_CENTER)
SUB = ParagraphStyle("sub", parent=BODY, fontSize=12, leading=16, alignment=TA_CENTER)
CELL = ParagraphStyle("cell", parent=BODY, fontSize=7.8, leading=10, spaceAfter=0)
CELLB = ParagraphStyle("cellb", parent=CELL, fontName="DVB")
W = A4[0] - 36 * mm


def P(t, st=BODY):
    return Paragraph(t, st)


def img(rel, width=W, caption=None):
    path = ROOT / rel
    im = Image(str(path))
    ratio = im.imageHeight / im.imageWidth
    h = width * ratio
    max_h = 205 * mm
    if h > max_h:
        width, h = max_h / ratio, max_h
    im.drawWidth, im.drawHeight = width, h
    parts = [im]
    if caption:
        parts.append(P(caption, SMALL))
    return KeepTogether(parts + [Spacer(1, 4)])


def table(rows, widths, header=True):
    data = [[P(str(c), CELLB if (header and i == 0) else CELL) for c in r] for i, r in enumerate(rows)]
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    style = [("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#bbb")), ("VALIGN", (0, 0), (-1, -1), "TOP"),
             ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3)]
    if header:
        style.append(("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8eef9")))
    t.setStyle(TableStyle(style))
    return t


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("DV", 7.5)
    canvas.setFillColor(colors.HexColor("#666"))
    canvas.drawString(18 * mm, 10 * mm, "Ion Thruster - Type EDH: design study (simulation results, not yet validated by experiment)")
    canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {doc.page}")
    canvas.restoreState()


def build():
    s = []
    s += [Spacer(1, 45 * mm), P("Ion Thruster - Type EDH", TITLE),
          P("Design study of a compact multi-stage electrohydrodynamic (EHD) ionic-wind thruster", SUB),
          Spacer(1, 8 * mm), img("diagrams/cad_2stage_exterior.png", width=85 * mm), Spacer(1, 6 * mm),
          P("Author: roosterbrown14 · October 2026", SUB),
          P("Repository: github.com/roosterbrown14/Ion-Thruster-Type-EDH", SUB), Spacer(1, 10 * mm),
          P("<b>Status.</b> Modelling and design are complete. No prototype has been built and nothing has been "
            "measured yet. All numbers are simulation estimates; real hardware may differ by 2–3×. The modelling "
            "code, analysis and documentation were developed with the help of Claude (Anthropic), an AI assistant.",
            SMALL), PageBreak()]

    s += [P("1. Summary", H1),
          P("The thruster stacks ring-shaped emitters and collectors along a 40 mm tube. A positive corona at "
            "each emitter creates ions, which drift to the next collector and drag air with them, so the device "
            "produces thrust with no moving parts. The study asked how to choose the electrode gap, the stage "
            "spacing, the ring diameters, the pin layout, the materials and the number of stages."),
          P("<b>The one rule behind everything.</b> For every ion stream, the force on the air equals "
            "current × axial distance ÷ ion mobility, and the power equals current × voltage. Thrust per watt is "
            "therefore <i>(axial distance travelled) ÷ (mobility × voltage)</i>. Efficiency favours long gaps at "
            "low voltage; thrust favours high voltage. Ions that drift backwards subtract thrust."),
          P("<b>Main findings</b>", H2)]
    s.append(table([
        ["Finding", "Detail"],
        ["Stage spacing dominates multi-stage design", "Ions from a later emitter drift back to the previous collector: 49 % of its "
         "current at spacing = gap, 16 % at 2×, 6 % at 3×. Keep spacing ≥ 3× the gap."],
        ["A guard ring removes back-flow", "A smooth ring wired to the later emitter, 10–12 mm upstream, cuts back-flow to 0 %: "
         "+40 % thrust, and a 25 % shorter device. No extra supply needed."],
        ["Gap", "Use the largest gap the supply can drive to about 85 % of sparkover (about 30–35 mm at 30 kV)."],
        ["Stage count", "More stages = more thrust at a fixed voltage, but lower thrust per watt. A third stage gave "
         "+20 % thrust for +53 % power."],
        ["Pins", "Neighbouring needles shield each other: best at spacing ≈ pin length (12–16 pins on a 30 mm ring)."],
        ["Collector", "A thin, smooth aluminium tube aligned with the flow. Collector types differ little electrically."],
        ["Materials", "Conductivity is irrelevant (losses about 10⁻⁸ of input). Stainless needles keep their tips."],
        ["Absolute performance", "Recommended two-stage build: about 3 mN at about 1.3 W (about 2.3 mN/W) at 19.5 kV."],
    ], [48 * mm, W - 48 * mm]))
    s.append(PageBreak())

    s += [P("2. Concept and design", H1),
          img("diagrams/two_stage_section.png", caption="Recommended two-stage layout: 25 mm gaps, 75 mm stage "
              "spacing, 30 mm rings, 40 mm insulating bore."),
          P("Each stage carries 16 stainless needles on a brass ring (emitter) and a thin aluminium tube "
            "(collector). Both are held on three thin insulating spokes inside a 3-D-printed PETG/ASA housing, "
            "clamped by nylon tie rods. A rounded inlet reduces entry loss. One current-limited 30 kV supply "
            "feeds both emitters; collectors return to ground through separate current shunts, so back-flow can "
            "be measured directly."),
          PageBreak()]

    s += [P("3. Physics and models", H1),
          P("Two levels of model were used. The <b>reduced-order model</b> combines an exact axisymmetric "
            "electrostatic solver (charge simulation method), Peek's law for corona onset, Townsend's current law "
            "applied along traced ion paths, and a 1-D duct momentum balance. It is fast enough for parameter sweeps. "
            "A separate 3-D model handles discrete needles."),
          P("The <b>self-consistent space-charge solver</b> solves Poisson's equation and ion drift together on a "
            "graded axisymmetric grid, with Kaptsov's corona condition. It matches the exact solution for a wire in a "
            "cylinder to within 2 %, and its results do not depend on grid size or boundary placement. It showed the "
            "reduced model's absolute thrust is about 3× too high and its back-flow too low; the trends and rankings held."),
          img("charts/H1_spacecharge_validation_and_IV.png", caption="Left: solver validation against the exact "
              "coaxial solution. Middle and right: single-stage current and force, space-charge solver vs reduced model."),
          img("charts/H4_charge_density_map.png", caption="Ion cloud (colour) and equipotentials in the two-stage "
              "device: back-flow is visible as charge leaking upstream from emitter 2."),
          PageBreak()]

    s += [P("4. Key results", H1),
          img("charts/H2_spacecharge_backflow.png", caption="Back-flow and per-stage force vs stage spacing "
              "(space-charge solver)."),
          img("charts/I1_guard_electrode.png", caption="Guard ring at emitter voltage (purple) vs no guard (grey)."),
          img("charts/H3_spacecharge_stage_count.png", caption="Stage count at the same voltage."),
          img("charts/B1_single_stage_gap_sweep.png", caption="Gap sweep (reduced model; trends reliable, absolute "
              "values about 2–3× high)."),
          img("charts/E1_pin_count_shielding.png", caption="Needle count, shielding and orientation (3-D model)."),
          img("charts/G1_sensitivity_tornado.png", caption="Sensitivity: sparkover field and current scale dominate "
              "the absolute numbers; gap and spacing dominate among design choices."),
          PageBreak()]

    s += [P("5. Recommendations", H1)]
    s.append(table([
        ["Factor", "Best choice"],
        ["Stage spacing", "≥ 3× the gap, or a guard ring at emitter voltage upstream of each later emitter"],
        ["Electrode gap", "Largest the supply can drive to 85 % of sparkover (≈ 30–35 mm at 30 kV)"],
        ["Number of stages", "1 for efficiency, 2 for balance, 3 only for maximum thrust"],
        ["Emitter", "12–16 stainless needles (tip ≈ 50 µm) on a Ø30 ring; axial for thrust, radial for efficiency"],
        ["Collector", "Thin aluminium tube, same diameter as the emitter ring, edges rounded"],
        ["Housing", "Insulating tube (PETG/ASA). Never metal: it would arc."],
        ["Supply", "One current-limited supply, unless per-stage gaps differ"],
    ], [40 * mm, W - 40 * mm]))
    s += [Spacer(1, 6), P("Configurations", H2)]
    s.append(table([
        ["Build", "Configuration", "Simulated performance"],
        ["P1 (first build)", "2 stages, d = 25 mm, s = 75 mm, 16 axial needles, Al tube collectors, 19.5 kV",
         "≈ 3.0 mN, 1.3 W, 2.3 mN/W"],
        ["P2 (after P1)", "As P1 + guard ring wired to emitter 2, 10 mm upstream, s = 37.5 mm",
         "≈ 3.7 mN, 1.4 W, 2.6 mN/W"],
        ["Most efficient", "1 stage, 30–35 mm gap, run just above onset", "≈ 3–10 mN/W, under 1 mN"],
    ], [30 * mm, 90 * mm, W - 120 * mm]))
    s.append(PageBreak())

    s += [P("6. Prototype P1", H1),
          img("prototypes/P1_assembled_section.png", width=135 * mm, caption="Fully assembled P1 on its test "
              "stand, section through the axis, coloured by material (design dimensions in mm).")]
    s += [PageBreak(), img("prototypes/P1_parts_sheet.png", caption="Every P1 part, separated, with material, "
                           "quantity and dimensions.")]
    s.append(KeepTogether([P("Parts and materials", H2), table([
        ["Part", "Qty", "Material", "Key dimensions (mm)"],
        ["Emitter needle", "32", "Stainless steel 304", "Ø0.8 × 9, 6 exposed, tip ≈ 0.05"],
        ["Emitter mounting ring", "2", "Brass", "Ø30, 2.5 × 3 section, 16 holes"],
        ["Collector tube", "2", "Aluminium 6061", "Ø30, 1 wall, 10 long"],
        ["Carriers, spacers, inlet, exit ring", "9", "PETG or ASA (printed)", "Ø40 bore / Ø46 outside"],
        ["Terminal pins", "4", "Brass", "Ø1.2 × 8"],
        ["Tie rods", "3", "Nylon", "M3 × 156"],
        ["Standoffs / base plate", "3 / 1", "PTFE or acetal / polycarbonate", "Ø12 × 100 / 140 × 140 × 6"],
    ], [50 * mm, 12 * mm, 50 * mm, W - 112 * mm])]))
    s += [Spacer(1, 4), P("Thruster mass about 121 g. Indicative parts cost £45–125; test equipment is "
                          "normally available in a university lab.", BODY), Spacer(1, 8)]

    s += [P("7. Testing plan and safety", H1),
          P("The models are unvalidated. The tests are ranked by how much they would change the conclusions:"),
          table([["#", "Measurement", "Why"],
                 ["1", "Current to each collector separately, at several spacing/gap ratios", "Back-flow decides stage count and spacing"],
                 ["2", "Sparkover voltage vs clearance", "Sets the optimum gap and the operating voltage"],
                 ["3", "I–V curve per emitter type", "Calibrates the current scale"],
                 ["4", "Thrust on a precision balance (exhaust up, insulated stand)", "Direct check of the main output"],
                 ["5", "Needle count 8/12/16/24; collector type", "Checks shielding and flow-loss assumptions"]],
                [8 * mm, 85 * mm, W - 93 * mm]),
          Spacer(1, 6),
          P("<b>Safety.</b> 10–30 kV DC can kill. Testing must be supervised, using a commercial current-limited "
            "supply inside an interlocked, grounded enclosure, with a grounding stick and no energised adjustments. "
            "Corona produces ozone and nitrogen oxides, so ventilation and an ozone monitor are required. Full "
            "procedure: docs/safety.md."),
          P("8. Limitations", H1),
          P("• Nothing is validated against measurements yet.<br/>"
            "• The space-charge solver treats needle rings as continuous rings.<br/>"
            "• Sparkover uses a simple average-field limit (0.7–1.4 MV/m), which dominates the absolute numbers.<br/>"
            "• Electrode flow-loss coefficients are engineering estimates.<br/>"
            "• Airflow is a 1-D duct model; no CFD."),
          P("9. Key references", H1),
          P("Masuyama K., Barrett S.R.H. (2013) On the performance of electrohydrodynamic propulsion. Proc. R. Soc. A 469, "
            "20120623. doi:10.1098/rspa.2012.0623<br/>"
            "Gilmore C.K., Barrett S.R.H. (2015) Electrohydrodynamic thrust density using positive corona-induced ionic "
            "winds for in-atmosphere propulsion. Proc. R. Soc. A 471, 20140912. doi:10.1098/rspa.2014.0912<br/>"
            "Xu H. et al. (2018) Flight of an aeroplane with solid-state propulsion. Nature 563, 532–535. "
            "doi:10.1038/s41586-018-0707-9<br/>"
            "Gomez-Vega N. et al. (2023) Model of multistaged ducted thrusters for high-thrust-density electroaerodynamic "
            "propulsion. AIAA J. 61, 767–779. doi:10.2514/1.J061948<br/>"
            "Sigmond R.S. (1982) J. Appl. Phys. 53, 891–898. doi:10.1063/1.330557 · Townsend J.S. (1914) Phil. Mag. 28, "
            "83–90 · Peek F.W. (1929) Dielectric Phenomena in High-Voltage Engineering.<br/>"
            "Full list (24 sources): references/references.bib", SMALL)]

    doc = SimpleDocTemplate(str(OUT), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm,
                            bottomMargin=18 * mm, title="Ion Thruster - Type EDH", author="roosterbrown14")
    doc.build(s, onFirstPage=footer, onLaterPages=footer)


if __name__ == "__main__":
    build()
    print(OUT)
