# Ion Thruster - Type EDH

[![tests](https://github.com/roosterbrown14/Ion-Thruster-Type-EDH/actions/workflows/tests.yml/badge.svg)](https://github.com/roosterbrown14/Ion-Thruster-Type-EDH/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

A design study of a small **ionic-wind (electrohydrodynamic, EHD) thruster**: a 40 mm tube that
pushes air using high voltage and no moving parts. The repository covers the physics, the
simulations, the recommended design, 3-D models of every part, a costed build plan in Canadian
dollars, and a safe test plan. All units are SI metric (mm, kV, mN, L/s, g, °C, kPa).

> **Status:** design and simulation are complete. **Nothing has been built or measured yet.**
> Every performance number is a simulation estimate; real hardware may differ by 2–3×.
> Full report (PDF, 10 pages): [docs/report/Ion_Thruster_Type_EDH_report.pdf](docs/report/Ion_Thruster_Type_EDH_report.pdf)

![Recommended two-stage layout](diagrams/two_stage_section.png)

## Summary

### How it works
A ring of sharp needles at about +20 kV (the **emitter**) ionizes the air next to the tips. The ions
are pulled toward a grounded ring (the **collector**). On the way they bump into air molecules
and drag the air along. That makes a jet and a small thrust. Stacking two or three of these
emitter–collector **stages** along the tube adds more push.

### The one rule behind everything
```
thrust per watt  =  (distance the ions travel along the tube) ÷ (ion mobility × voltage)
```
Long gaps at low voltage are efficient. High voltage gives more thrust. You cannot maximize both,
and ions that travel the **wrong way** (backwards) subtract thrust.

### What the simulations found
1. **Spacing between stages matters most.** Ions from the second emitter can drift *backwards*
   to the first collector. That happens to 49 % of its current if the stages are as close as the gap,
   16 % at 2× the gap, and 6 % at 3× the gap. **Keep stages at least 3× the gap apart.**
2. **A guard ring fixes it.** A smooth ring wired to the second emitter, placed just upstream of it,
   stops back-flow completely: about **+25 % thrust while cutting the stage spacing from 75 to
   37.5 mm**, with no extra power supply. This is the suggested upgrade (P2).
3. **Use the largest gap your supply can drive.** With a 30 kV supply that is about 25–35 mm. The
   sparkover limit (about 1 kV/mm) sets the voltage.
4. **More stages = more thrust, less efficiency.** A third stage adds about 20 % thrust for about
   53 % more power.
5. **12–16 needles per ring** is the sweet spot (needles closer together than their length shield
   each other). **Thin aluminum tube collectors** block the least air. **Material conductivity
   doesn't matter**; choose stainless needles because they stay sharp.
6. **Expected performance of the recommended build: about 3 mN of thrust at about 1.3 W and
   19.5 kV, with about 1.8 L/s of airflow.** For scale, 3 mN is the weight of about 0.3 g.

### Recommended first build (P1)

| | |
|---|---|
| Layout | 2 stages in a Ø40 mm plastic tube; needle-tip-to-collector gap 25 mm; 75 mm between stages |
| Emitters | 2 brass rings (Ø30 mm), each with 16 stainless steel pins, 6 mm exposed, pointing downstream |
| Collectors | 2 aluminum tubes, Ø30–32 mm × 1 mm wall × 10 mm long, edges rounded |
| Housing | 3-D-printed PETG or ASA, clamped by 3 nylon M3 tie rods |
| Supply | One current-limited 30 kV supply, run at about 19.5 kV (about 78 % of sparkover) |
| Size and mass | 173 mm long, about 129 g (without test stand) |
| Parts cost | **CAD $106–305** (test equipment is usually available in a university lab) |
| Simulated result | ≈ 3 mN thrust, ≈ 1.3 W, ≈ 2.3 mN/W, ≈ 1.8 L/s airflow |

Next steps: build P1, then measure **sparkover voltage** and the **current to each collector separately**
(this measures back-flow directly). See [experiments/test_plan.md](experiments/test_plan.md) and
**[docs/safety.md](docs/safety.md)** first. High voltage can kill.

### What matters most

| Factor | Best choice | Confidence |
|---|---|---|
| Spacing between stages | ≥ 3× the gap, or a guard ring at emitter voltage | Medium–high: both models agree on the trend; numbers need measuring |
| Electrode gap | Largest the supply can drive to about 85 % of sparkover | High (trend matches published experiments) |
| Number of stages | 1 for efficiency, 2 for balance, 3 only for maximum thrust | High in the models |
| Needles | 12–16 sharp stainless pins per Ø30 mm ring; axial for thrust | Medium |
| Collector | Thin aluminum tube, same diameter as the emitter ring | Medium (airflow losses are estimated) |
| Housing | Insulating plastic tube. **Never metal** (it would arc to the emitter) | High |
| Supply | One supply unless the stage gaps differ | Medium |
| Air | Cool, dense air helps; expect about −25 % thrust at 1 km altitude | Medium |

All 16 research questions are answered in **[docs/recommendations.md](docs/recommendations.md)**.

## Designs

| | Design | Where |
|---|---|---|
| **P1** | Two-stage thruster, recommended first build | [prototypes/](prototypes/README.md): drawings, parts, materials, cost, assembly, blank results sheet |
| **P2** | P1 plus a guard ring, shorter stage spacing (37.5 mm) | [docs/results/guard.md](docs/results/guard.md) (simulation only) |
| **P1x3** | Three P1s in a triangle, 60 mm apart, with a 3-into-1 merge joint | [prototypes/](prototypes/README.md#p1x3-compact-triangular-cluster-with-a-3-into-1-merge-joint) |

| P1 assembled (section) | P1 on its test stand | P1x3 with merge joint |
|---|---|---|
| ![](prototypes/P1_assembled_section.png) | ![](diagrams/cad_2stage_exterior.png) | ![](prototypes/P1x3_exterior_with_joint.png) |

Every part is a watertight STL in [`cad/stl/`](cad/stl/), with interactive 3-D viewers
([`cad/viewer_2stage.html`](cad/viewer_2stage.html), [`prototypes/P1x3_viewer.html`](prototypes/P1x3_viewer.html)).

## Key charts

| | |
|---|---|
| ![](charts/H2_spacecharge_backflow.png) **Back-flow vs stage spacing** | ![](charts/I1_guard_electrode.png) **Guard ring vs no guard** |
| ![](charts/H4_charge_density_map.png) **Ion cloud inside the thruster** | ![](charts/E1_pin_count_shielding.png) **Needle count and shielding** |
| ![](charts/B1_single_stage_gap_sweep.png) **Gap sweep, one stage*** | ![](charts/G1_sensitivity_tornado.png) **What the results depend on most*** |

\*Fast reduced model: trends are reliable, absolute values about 2–3× high (see [space-charge results](docs/results/spacecharge.md)).
All charts are in `charts/` as PNG and SVG.

## How the models work

Two levels of simulation, both in [`src/ehd/`](src/ehd/):

1. **Fast reduced model** for the large parameter sweeps. It uses an exact electrostatic field
   solver, Peek's law for corona onset, Townsend's current law along traced ion paths, and a
   simple duct model for the airflow. A separate 3-D model handles the individual needles.
2. **Self-consistent space-charge solver** for the key results. It solves the electric field and the
   ion cloud together. It matches the exact textbook solution for a wire inside a cylinder within
   2 %, and it corrected the fast model's thrust (about 3× too high) and back-flow (too low).

Not simulated: detailed airflow (CFD) and individual needles with space charge. Details are in
[physics.md](docs/physics.md) and [methodology.md](docs/methodology.md).

## Documents

| Read | For |
|---|---|
| [Project report (PDF)](docs/report/Ion_Thruster_Type_EDH_report.pdf) | The whole project in 10 pages |
| [recommendations.md](docs/recommendations.md) | Answers to all research questions, build options, what to test |
| [results/spacecharge.md](docs/results/spacecharge.md) · [results/guard.md](docs/results/guard.md) | The most accurate results |
| [spacing](docs/results/spacing.md) · [geometry](docs/results/geometry.md) · [materials](docs/results/materials.md) · [stages](docs/results/stages.md) · [sensitivity](docs/results/sensitivity_optimization.md) | Detailed parameter studies |
| [physics.md](docs/physics.md) · [methodology.md](docs/methodology.md) | Equations, assumptions, numerical methods, verification |
| [literature_review.md](docs/literature_review.md) | 24 published sources, each checked against its DOI |
| [prototypes/README.md](prototypes/README.md) · [cad/README.md](cad/README.md) | Build package and 3-D models |
| [experiments/test_plan.md](experiments/test_plan.md) | How to test, with CSV templates and an uncertainty script |
| [safety.md](docs/safety.md) | **Read before any high-voltage work** (Canadian requirements included) |

## Repository layout

| Path | Contents |
|---|---|
| `src/ehd/` | Model code |
| `simulations/` | One script per study, plus verification and diagrams |
| `cad/`, `prototypes/` | 3-D models, drawings, parts lists, cost estimate |
| `data/`, `charts/`, `diagrams/` | Generated results and figures |
| `docs/`, `experiments/`, `references/` | Write-ups, test plan, bibliography |
| `tests/` | 14 automated verification tests (run on every push) |

## Reproduce

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt   # see docs/environment.md if pip is missing
.venv/bin/python -m pytest
for s in phase_b_spacing phase_c_geometry phase_d_materials phase_e_pins phase_f_stages \
         phase_g_sensitivity_pareto phase_h_spacecharge phase_i_guard verification diagrams; do
  .venv/bin/python simulations/$s.py
done
.venv/bin/python cad/build.py
.venv/bin/python prototypes/build_drawings.py
.venv/bin/python prototypes/build_cluster.py
.venv/bin/python docs/report/build_report.py
```
About 25 minutes on an 8-core CPU. No GPU needed.

## Limitations
- **Nothing is validated against measurements yet.**
- The space-charge solver treats each needle ring as a continuous ring.
- Sparkover uses a simple average-field limit (0.7–1.4 kV/mm). It sets the operating voltage, so it
  dominates the absolute numbers. Measure it on the real parts.
- Airflow losses from the electrodes are engineering estimates.
- Humidity is covered only through the uncertainty ranges.

## Author and credits
- **Author:** [roosterbrown14](https://github.com/roosterbrown14). Project concept, research brief and design direction.
  Design log: [docs/design_log.md](docs/design_log.md).
- **AI assistance:** the modelling code, analysis, CAD and documentation were developed with the help of
  Claude (Anthropic), an AI assistant.
- **Licence:** [MIT](LICENSE).

## Key references
Masuyama & Barrett 2013 ([doi](https://doi.org/10.1098/rspa.2012.0623)) ·
Gilmore & Barrett 2015 ([doi](https://doi.org/10.1098/rspa.2014.0912)) ·
Xu et al. 2018, *Nature* ([doi](https://doi.org/10.1038/s41586-018-0707-9)) ·
Gomez-Vega et al. 2023 ([doi](https://doi.org/10.2514/1.J061948)) ·
Townsend 1914 · Peek 1929 · Sigmond 1982. Full list: [references.bib](references/references.bib).
