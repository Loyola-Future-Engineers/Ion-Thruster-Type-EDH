# Progress log

Read this first when resuming. Last updated 2026-10-28.

## Status
- All planned research phases have a first complete pass: models, studies, charts, docs, tests.
- **No experiments have been done and no measured data exists.** All results are numerical
  simulation or analytical/qualitative, and labelled as such.
- The Claude Code session was **not** inside tmux/screen, so it does not survive a terminal or SSH disconnect.
- **No GitHub remote is configured.** All commits are local. Pushing needs the owner to create or
  authorise a repository (for example `gh repo create <name> --private --source . --push`).
- Host was a local WSL2 workstation, not Vast.ai (`docs/environment.md`).

## Completed milestones
1. Framework, isolated environment, environment record.
2. Physics and governing-equation document. Literature review (24 Crossref-verified DOIs).
3. Axisymmetric CSM solver plus multi-stage device model, verified (`tests/`, 13 tests).
4. Phase B spacing: single-stage sweep, d–s heatmap, gap patterns (common vs per-stage supply), 3-stage gap search.
5. Phase C geometry: diameters, ratio, collector cross-section and type, field map.
6. Phase D materials: resistive loss and mass (analytical), qualitative durability matrix.
7. Phase E pins: 3-D CSM, pin count/shielding, orientation, tip radius.
8. Phase F stages: 1/2/3 stages at equal geometry, equal length, low-loss collectors.
9. Phase G: tornado sensitivity, paired Monte-Carlo, Pareto search, interactive explorer.
10. Verification and convergence (V1). Trend check against Masuyama & Barrett 2013.
11. Experimental test plan, CSV templates, GUM reduction script. HV safety document.
12. Engineering diagrams, recommendations, README.

## Important findings (model-based, unvalidated)
- Back-flow from emitter k+1 to collector k dominates multi-stage behaviour. Keep s ≥ 2d.
- More stages = more thrust at fixed voltage, but lower thrust per watt at equal power.
- d1 > d2 > d3 helps only with per-stage supplies.
- Optimum gap is set by supply voltage / sparkover field (about 30–35 mm at 30 kV).
- Pins: about 12–16 on a 30 mm ring. Axial for thrust, radial for thrust/W.
- Absolute thrust uncertain by about ×3. Rankings robust to parameter uncertainty.

## Known problems / limitations
- No space charge in ion paths (affects the back-flow fraction).
- Current closure is heuristic (k_scale band 0.5–2). The pin model uses a different closure,
  so do not compare pin and ring absolute numbers.
- Flow-loss coefficients are assumed. They decide the collector ranking.
- The pin model has no housing wall. Radial-out pins as modelled do not fit a 40 mm bore.
- Three multistage papers (Rickard 2006/2007, Kim 2010) were not read in full. Only their metadata is used.

## Next recommended actions
1. Owner: create a GitHub remote and push.
2. Read Rickard et al. 2006, Rickard & Dunn-Rankin 2007, Kim et al. 2010 and Gomez-Vega et al. 2023
   in full. Compare their staging results with Phase F.
3. Implement a self-consistent 2-D axisymmetric space-charge solver (Poisson + charge transport with
   the Kaptsov condition) to check the back-flow fraction. This is where GPU or sparse solvers become useful.
4. Add the housing wall (dielectric) to the pin model.
5. Build the common-supply two-stage rig per `experiments/test_plan.md` under supervision. Measure
   back-flow and sparkover first.
