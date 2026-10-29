# Ion Thruster - Type EDH

A design study of a compact, **multi-stage electrohydrodynamic (EHD) ionic-wind thruster**.
Ring-shaped emitters and collectors are stacked along a 40 mm tube. Each stage ionises air and
pushes it through the bore, with no moving parts. The repository contains the physics, the
simulation code, the results, 3-D models of every part, and a plan for testing a prototype safely.

> **Status:** modelling and design are complete. **No prototype has been built and nothing has
> been measured yet.** Every number below comes from simulation and should be treated as an
> estimate, with real hardware possibly differing by 2–3×.

![Recommended two-stage layout](diagrams/two_stage_section.png)

## Summary: what makes the best and most efficient EHD thruster

### The one rule behind everything
For every ion that crosses the gap, the push on the air is fixed by how far it travels along the
axis. The power it costs is fixed by the voltage it falls through:

```
thrust / power  =  (axial distance the ions travel) / (ion mobility × voltage)
```

So **efficiency wants long gaps at low voltage, and thrust wants high voltage and high current.**
You cannot maximise both. Every design choice below either moves you along that trade-off or stops
you wasting power on top of it.

### The factors, in order of importance

| # | Factor | Best choice | Why it matters | Confidence |
|---|---|---|---|---|
| 1 | **Spacing between stages** | At least **3× the electrode gap** | Ions from a later emitter drift *backwards* to the previous collector and push the air the wrong way. Back-flow is 49 % of the current at 1× the gap, 16 % at 2×, 6 % at 3×. | Medium–high: both models agree on the trend; the numbers need measurement |
| 2 | **Electrode gap** | The **largest gap your supply can drive to about 85 % of sparkover**. About 30–35 mm for a 30 kV supply. | A longer gap gives more thrust per watt. Beyond what the supply can drive, thrust collapses. | High for the trend; the exact value depends on the measured sparkover |
| 3 | **Operating voltage** | Lower voltage for efficiency, up to the 85 %-of-sparkover limit for thrust | Sets where you sit on the thrust/efficiency trade-off | Physics |
| 4 | **Number of stages** | **1 stage** for best efficiency. **2 stages** for the best balance. **3 only if thrust matters more than power and length.** | Extra stages add thrust at the same voltage, but each costs more power than it returns (third stage: +20 % thrust for +53 % power) | High in the models |
| 5 | **Emitter sharpness** | Fine tips or wire (about 50 µm radius or less) | Sharper tips start the corona at lower voltage, which widens the usable voltage window | High (Peek's law) |
| 6 | **Pin count** | Pin spacing about equal to pin length. That is **12–16 pins on a 30 mm ring**. | More pins add current until neighbouring pins shield each other. Beyond that, more pins make it worse. | Medium (trend robust, optimum approximate) |
| 7 | **Pin direction** | **Axial** (pointing downstream) for thrust. **Radial** for about 30 % better thrust per watt, but outward pins need a wider bore. Never pointing inward. | Radial tips keep the full axial travel distance. Axial tips are closer to the collector, so they draw more current. | Medium |
| 8 | **Collector shape** | A **thin, smooth tube aligned with the flow**, edges well rounded | Electrically, collector types differ by only about 12 %. What matters is how much they block the air. A mesh gains nothing electrically. | Medium (flow-loss values assumed) |
| 9 | **Ring diameters** | Emitter ring as large as the bore allows, with wall clearance. Collector the same size or slightly smaller. | A bigger ring means more emitting length and more current. A larger collector only blocks more flow. | Medium |
| 10 | **Housing** | An **insulating** (plastic) tube. **Never a metal one.** | The plastic tube adds about 7 % force and makes behaviour predictable. A grounded metal tube would arc to the emitter. | High |
| 11 | **Gap per stage** | Equal gaps on one shared supply. Decreasing gaps (for example 32/18/12 mm) only with a separate supply per stage. | With one supply, the smallest gap limits every stage's voltage | Medium |
| 12 | **Air conditions** | Dense, cool air. Expect less in heat or at altitude. | About −24 % thrust at 90 kPa (about 1 km altitude). Humidity changes sparkover. | Medium |
| 13 | **Electrode material** | Choose for durability (stainless needles, aluminium collectors), not conductivity | Electrode resistance wastes about 10⁻⁸ of the power. Sharp copper tips blunt and tarnish. | High |
| 14 | **Inlet and obstructions** | Rounded inlet, thin spokes, nothing extra in the bore | Every obstruction converts thrust into pressure loss | Medium |

### Two recipes

| Goal | Configuration | Model estimate |
|---|---|---|
| **Most efficient** | 1 stage, 30–35 mm gap, 16 radial needles (needs a wider bore) or a fine wire ring, tube collector, run just above corona onset | About 3–10 mN/W, but under 1 mN of thrust |
| **Best balance** (the recommended build) | 2 stages, 25 mm gaps, 75 mm stage spacing, 16 axial stainless needles, aluminium tube collectors, 40 mm plastic bore, one 30 kV supply run at about 19.5 kV (85 % of sparkover) | About 3 mN at about 1.3 W (about 2.3 mN/W) |

The full answers to all 16 original research questions are in
**[docs/recommendations.md](docs/recommendations.md)**.

## 3-D design

Every part of the recommended build is modelled in [`cad/`](cad/README.md): printed housing
sections, electrode carriers, a brass emitter ring, stainless needles, aluminium collector tubes,
terminals, tie rods and an insulating test stand. Each part is a watertight STL. There are 2- and 3-stage
assemblies, interactive 3-D viewers (`cad/viewer_2stage.html`), a bill of materials, and an
interference check (no clashes). The two-stage thruster is 158 mm long overall (including the inlet flare) and weighs about 121 g.

| Section through the axis | Exterior on the test stand |
|---|---|
| ![](diagrams/cad_2stage_section.png) | ![](diagrams/cad_2stage_exterior.png) |

## Key charts

| | |
|---|---|
| ![](charts/H2_spacecharge_backflow.png) **Back-flow vs stage spacing** (space-charge solver) | ![](charts/H4_charge_density_map.png) **Ion cloud and equipotentials**, two stages |
| ![](charts/B1_single_stage_gap_sweep.png) **Gap sweep**, one stage* | ![](charts/F1_stage_count_thrust_vs_power.png) **1 vs 2 vs 3 stages**, thrust vs power* |
| ![](charts/E1_pin_count_shielding.png) **Pin count and shielding** | ![](charts/G1_sensitivity_tornado.png) **What the results are most sensitive to*** |

\*Reduced-order model: the trends are reliable, but absolute values are about 2–3× high (see [space-charge results](docs/results/spacecharge.md)).
All 27 charts are in `charts/` as PNG and SVG. An interactive design-space explorer is in `charts/interactive_pareto.html`.

## How the models work

Positive corona at the emitter creates ions. In the drift region they move at velocity `mu E` and
pass their momentum to the air. For each stream of ions, the force on the air is exactly
`current × axial distance / mobility`. That is where the "one rule" above comes from, and why ions that
land *upstream* subtract thrust.

Two levels of model are used:

1. **Reduced-order model** (fast; used for the large parameter sweeps). An exact axisymmetric
   electrostatic solver (charge simulation method) gives the field. Peek's law gives corona onset.
   Townsend's current law is applied along traced ion paths. A 1-D duct momentum balance gives airflow.
   A separate 3-D model handles discrete needles.
2. **Self-consistent space-charge solver** (slower; used to check and correct the key results). It
   solves Poisson's equation and ion drift together, with the standard Kaptsov corona condition. It
   matches the exact solution for a wire inside a cylinder to within 2 %.

Navier–Stokes airflow is not simulated. Details: [physics](docs/physics.md) and [methodology](docs/methodology.md).

## Documents

| Read | For |
|---|---|
| [recommendations.md](docs/recommendations.md) | Answers to the research questions, build configurations, what to test |
| [results/spacecharge.md](docs/results/spacecharge.md) | Most accurate results: back-flow, stage count, housing |
| [results/spacing.md](docs/results/spacing.md) · [geometry.md](docs/results/geometry.md) · [materials.md](docs/results/materials.md) · [stages.md](docs/results/stages.md) · [sensitivity_optimisation.md](docs/results/sensitivity_optimisation.md) | Detailed parameter studies |
| [physics.md](docs/physics.md) · [methodology.md](docs/methodology.md) | Equations, assumptions, numerical methods, verification |
| [literature_review.md](docs/literature_review.md) | 24 published sources, each checked against its DOI |
| [prototypes/README.md](prototypes/README.md) | Prototype P1: drawings, parts, materials, assembly steps |
| [experiments/test_plan.md](experiments/test_plan.md) | How to test a prototype, with CSV templates and an uncertainty script |
| [safety.md](docs/safety.md) | **Read before any high-voltage work** |

## Repository layout

| Path | Contents |
|---|---|
| `src/ehd/` | Model code: corona laws, field solver, device model, 3-D pin model, space-charge solver |
| `simulations/` | One script per study, plus verification and diagrams |
| `cad/` | Part models, assemblies, viewers, bill of materials |
| `prototypes/` | Prototype P1 build package: dimensioned assembled and exploded drawings, parts and materials, assembly steps, blank results sheet |
| `data/`, `charts/`, `diagrams/` | Generated results and figures |
| `docs/`, `experiments/`, `references/` | Write-ups, test plan, bibliography |
| `tests/` | 14 automated verification tests |

## Reproduce

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt   # see docs/environment.md if pip is missing
.venv/bin/python -m pytest
for s in phase_b_spacing phase_c_geometry phase_d_materials phase_e_pins phase_f_stages \
         phase_g_sensitivity_pareto phase_h_spacecharge verification diagrams; do
  .venv/bin/python simulations/$s.py
done
.venv/bin/python cad/build.py
```
About 25 minutes on an 8-core CPU. No GPU needed.

## Limitations
- **Nothing is validated against measurements yet.** The two most important tests are
  back-flow (measure each collector's current separately) and sparkover voltage.
- The space-charge solver treats emitters as continuous rings. Discrete needles are modelled
  only without space charge.
- Sparkover uses a simple average-field limit (0.7–1.4 MV/m), and it dominates the absolute numbers.
- Airflow losses from electrodes use rough engineering correlations. These decide which collector shape ranks best.
- Humidity is covered only through the uncertainty ranges.

## Key references
Masuyama & Barrett 2013 ([doi](https://doi.org/10.1098/rspa.2012.0623)) ·
Gilmore & Barrett 2015 ([doi](https://doi.org/10.1098/rspa.2014.0912)) ·
Xu et al. 2018, *Nature* ([doi](https://doi.org/10.1038/s41586-018-0707-9)) ·
Gomez-Vega et al. 2023 ([doi](https://doi.org/10.2514/1.J061948)) ·
Townsend 1914 · Peek 1929 · Sigmond 1982. Full list: [references.bib](references/references.bib).
