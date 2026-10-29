# Multi-stage EHD ionic-wind thruster

Design study and reduced-order modelling of a compact **cylindrical, multi-stage
electrohydrodynamic (EHD) thruster**. Each stage is a ring emitter (pins, wire or serrated
ring) followed by a ring collector, and the stages are stacked along a 40 mm bore so that
air is accelerated through the middle.

> **Status.** Theory, models, a self-consistent space-charge solver, 3-D part models and a test
> plan are done. **No physical prototype has been built and no measurements exist.** All numerical
> results are labelled as numerical simulation. The space-charge solver ([Phase H](docs/results/spacecharge.md))
> shows the earlier reduced-order absolute numbers are about 3× optimistic. Trends and rankings held.

![two-stage section](diagrams/two_stage_section.png)

## Engineering objectives
Maximise useful airflow and thrust while keeping thrust per watt reasonable. Choose between
two and three stages. Pick electrode spacing, diameters, pin layout and materials. Do this
with evidence whose limits are stated.

## Main findings so far

| Topic | Finding | Evidence |
|---|---|---|
| Gap | Use the largest gap the supply can drive to about 85 % of sparkover. That is about 30–35 mm at 30 kV if sparkover is about 1 MV/m. | [spacing](docs/results/spacing.md) |
| Stage interaction | Ions from a later emitter drift **backwards** to the previous collector and produce negative thrust. With space charge: 49 % of the current at s = d, 16 % at s = 2d, 6 % at s = 3d. **Keep s ≥ 3d.** | [space charge](docs/results/spacecharge.md) |
| Absolute performance | Space-charge solver, single 25 mm stage at 19.5 kV: 34 µA, 1.9 mN net thrust, 2.9 mN/W. That is about 3× below the reduced model. | [space charge](docs/results/spacecharge.md) |
| Housing tube | An insulating bore tube adds about 7 % force and makes the device insensitive to its surroundings. It does not stop back-flow. A metal tube would arc. | [space charge](docs/results/spacecharge.md) |
| d1 > d2 > d3? | Helps **only with a separate supply per stage** (best triple 32/18/12 mm), because stage 1 has no back-flow. With one common supply, equal gaps win. | [spacing](docs/results/spacing.md) |
| 2 vs 3 stages | Extra stages raise maximum thrust (+50–75 %, then +23–40 %) but **lower thrust per watt** at equal power. A third stage mainly adds power. | [stages](docs/results/stages.md) |
| Pins | Neighbouring pins shield each other. Best near pin spacing ≈ pin length (12–16 pins on a 30 mm ring). Axial pins give the most thrust; radial pins give the best thrust/W. | [geometry](docs/results/geometry.md) |
| Collector | Electrical differences are small. A **thin aligned tube** has the lowest flow loss. Mesh is roughly neutral at 70 % open area. | [geometry](docs/results/geometry.md) |
| Materials | Conductivity is irrelevant (I²R about 10⁻⁸ of input). Choose for tip stability and ozone resistance: stainless needles + aluminium tube. | [materials](docs/results/materials.md) |

Full answers to all 16 research questions, with starting configurations:
**[docs/recommendations.md](docs/recommendations.md)**.

## Featured charts

| | |
|---|---|
| ![](charts/B1_single_stage_gap_sweep.png) Single-stage gap sweep | ![](charts/B8_heatmap_gap_vs_spacing.png) Gap vs inter-stage spacing |
| ![](charts/F1_stage_count_thrust_vs_power.png) 1 / 2 / 3 stages vs power | ![](charts/G3_pareto_fronts.png) Pareto fronts |
| ![](charts/E1_pin_count_shielding.png) Pin shielding | ![](charts/C3_electric_field_map.png) Field and ion paths |
| ![](charts/G1_sensitivity_tornado.png) Sensitivity | ![](charts/G2_monte_carlo_uncertainty.png) Monte-Carlo uncertainty |
| ![](charts/H2_spacecharge_backflow.png) Back-flow with space charge | ![](charts/H4_charge_density_map.png) Space-charge density |

Every chart is in `charts/` as PNG and SVG. An interactive design-space explorer is in
`charts/interactive_pareto.html`.

## 3-D design

Every part of the recommended build is modelled in [`cad/`](cad/README.md): printed housing
sections, electrode carriers, brass emitter ring, stainless needles, aluminium collector tubes,
terminals, tie rods and an insulating test stand. Each part is a watertight STL, with 2- and 3-stage
assemblies, interactive viewers and a bill of materials. It is a design proposal and has not been built.

| | |
|---|---|
| ![](diagrams/cad_2stage_section.png) | ![](diagrams/cad_2stage_exterior.png) |

## Physics and models in one paragraph
Positive corona at the emitter creates ions. In the drift region they move at `mu E` and pass
their momentum to neutral air. For each ion flux tube, the force is exactly `dI · dz / mu`, where
`dz` is the axial distance between where the tube starts and where it lands. So thrust per watt
is `<dz>/(mu V)`, and ions that land upstream subtract thrust. The repository computes:
the Laplace field of all electrodes with an axisymmetric **charge simulation method**; corona
onset from **Peek's law**; current from **Townsend's** quadratic law applied tube by tube along
traced ion paths; and airflow from a 1-D duct momentum balance with electrode loss coefficients.
A separate **3-D model** handles discrete pins. A **self-consistent space-charge solver**
(Poisson + upwind ion drift with Kaptsov injection, verified against the exact coaxial solution)
checks the reduced model. Navier–Stokes flow is **not** modelled. See [physics](docs/physics.md) and [methodology](docs/methodology.md).

## Repository layout

| Path | Contents |
|---|---|
| `src/ehd/` | Models: `corona.py` (closures), `csm.py` (axisymmetric field solver), `device.py` (multi-stage performance), `pins.py` (3-D pins), `spacecharge.py` (self-consistent solver), `study.py`, `reference.py`, `plotting.py` |
| `simulations/` | One script per study phase (B spacing, C geometry, D materials, E pins, F stages, G sensitivity/Pareto, H space charge), verification, diagrams |
| `data/` | CSV output of every study |
| `charts/`, `diagrams/` | Generated figures (PNG + SVG) |
| `docs/` | Physics, literature review, methodology, results per phase, recommendations, safety, environment |
| `cad/` | Parametric 3-D models of every part (STL), assemblies, interactive viewers, bill of materials |
| `experiments/` | Test plan, CSV templates, uncertainty-reduction script (no data yet) |
| `references/` | Crossref-generated BibTeX and its build script |
| `tests/` | Verification tests (`pytest`) |
| `PROGRESS.md` | Progress log for resuming work |

## Reproduce

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt   # see docs/environment.md if pip is missing
.venv/bin/python -m pytest
for s in phase_b_spacing phase_c_geometry phase_d_materials phase_e_pins phase_f_stages \
         phase_g_sensitivity_pareto phase_h_spacecharge verification diagrams; do .venv/bin/python simulations/$s.py; done
```
About 25 minutes on 8 CPU cores. No GPU needed.

## Limitations
- Phases B–G use the reduced model (no space charge). Phase H corrects the key numbers, but only for a few axisymmetric cases.
- The space-charge solver is axisymmetric (ring emitters). Discrete pins in 3-D are not solved self-consistently.
- Sparkover is a mean-field criterion (0.7–1.4 MV/m band). It dominates absolute predictions.
- Flow losses use order-of-magnitude correlations, which decide the collector-type ranking.
- Humidity is represented only through parameter ranges.
- The pin model has no housing wall. Radial-outward pins do not fit the 40 mm bore as modelled.

## Future testing
[experiments/test_plan.md](experiments/test_plan.md) ranks the measurements by how much they
would change the conclusions. Most important: **separate current measurement on each collector**
(back-flow) and **sparkover vs clearance**. Read [docs/safety.md](docs/safety.md) before any
high-voltage work.

## References
[Literature review](docs/literature_review.md) and [`references/references.bib`](references/references.bib)
(24 DOI-verified works). Key sources: Masuyama & Barrett 2013 (doi:10.1098/rspa.2012.0623),
Gilmore & Barrett 2015 (doi:10.1098/rspa.2014.0912), Xu et al. 2018 (doi:10.1038/s41586-018-0707-9),
Gomez-Vega et al. 2023 (doi:10.2514/1.J061948), Townsend 1914, Peek 1929, Sigmond 1982.
