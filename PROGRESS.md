# Progress log

Read this first when resuming work. Last updated 2026-10-28. Units: SI metric (mm, kV, mN, L/s, g, °C, kPa); costs in CAD.

## Status
- Modelling, design and documentation are complete for a first full pass.
- **No experiments have been done. No measured data exists.**
- Repository: https://github.com/roosterbrown14/Ion-Thruster-Type-EDH (private).

## Completed
| Area | Where |
|---|---|
| Physics, governing equations, literature review (24 DOI-checked sources) | `docs/physics.md`, `docs/literature_review.md` |
| Axisymmetric field solver, reduced-order multi-stage model, 3-D pin model | `src/ehd/` |
| Parameter studies: spacing, geometry, materials, pins, stage count, sensitivity, Pareto | `docs/results/` |
| Self-consistent space-charge solver, verified against the exact coaxial solution | `src/ehd/spacecharge.py`, `docs/results/spacecharge.md` |
| Recommendations answering all 16 research questions | `docs/recommendations.md` |
| 3-D models of every part, assemblies, bill of materials | `cad/` |
| Test plan, CSV templates, uncertainty script, high-voltage safety | `experiments/`, `docs/safety.md` |
| Guard-ring study: removes back-flow in simulation | `docs/results/guard.md` |
| Prototype P1 build package and cost estimate | `prototypes/` |
| 10-page project report (PDF) | `docs/report/` |
| 14 automated verification tests, run on GitHub for every push | `tests/`, `.github/workflows/tests.yml` |
| P1x3 compact cluster (60 mm pitch) and 3-into-1 merge joint | `prototypes/` |
| Canadian metric and spelling conventions; costs in CAD; Canadian safety references (CSA Z462, provincial OHS) | whole repository |

## Main findings (model-based, unvalidated)
- Back-flow from each later emitter to the previous collector dominates multi-stage behaviour. Keep stage spacing ≥ 3× the gap.
- More stages give more thrust at a fixed voltage, but less thrust per watt.
- The best gap is set by supply voltage ÷ sparkover field (about 30–35 mm at 30 kV).
- Pins: 12–16 on a 30 mm ring. Axial for thrust, radial for efficiency.
- Single 25 mm stage at 19.5 kV (space-charge solver): about 34 µA, 1.9 mN. The reduced model is about 3× higher.
- An insulating housing helps slightly. A grounded metal housing would arc.
- A guard ring at emitter voltage upstream of each later emitter removes back-flow: +40 % thrust and a 25 % shorter device (simulation).

## Known limitations
- The parameter sweeps (spacing, geometry, stages, sensitivity) use the reduced model. The space-charge solver corrects the key cases only.
- The space-charge solver is axisymmetric: emitters are continuous rings, not discrete needles.
- Electrode flow-loss coefficients are assumed. They decide the collector-shape ranking.
- Three multistage papers (Rickard 2006/2007, Kim 2010) were used from their metadata only.

## Next actions
1. Build the two-stage common-supply rig per `experiments/test_plan.md`, under supervision. Measure back-flow (current to each collector) and sparkover first.
2. Calibrate the current closure and sparkover field against those measurements.
3. Read Rickard 2006/2007, Kim 2010 and Gomez-Vega 2023 in full and compare with the stage-count results.
4. Extend the space-charge solver to 3-D discrete needles (a good use of a GPU).
5. Airflow CFD (axisymmetric RANS with the EHD body force, for example OpenFOAM) to replace the 1-D duct model.
6. Fill in `docs/design_log.md` (author's own account) and add photos and video once P1 is built.
