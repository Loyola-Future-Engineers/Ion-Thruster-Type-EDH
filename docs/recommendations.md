# Engineering recommendations

**Read this first:** every number here comes from models that have **not been validated against
experiment**. Where the self-consistent space-charge solver ([spacecharge.md](results/spacecharge.md))
was run, its numbers are used. It shows the faster reduced-order model's absolute thrust is about 3×
too high, while trends and rankings hold. Each answer is tagged with its evidence class:
**[Lit]** published literature, **[Sim]** this project's numerical simulation,
**[Ana]** analytical calculation, **[Qual]** qualitative engineering assessment.
There is no exact optimal design. There is a promising starting point and a list of tests.

## Answers to the research questions

| # | Question | Answer | Evidence |
|---|---|---|---|
| 1 | Most promising emitter–collector spacing | The largest gap the supply can drive to about 85 % of sparkover: `d ≈ V_supply / (0.85 E_sp)`, about **30–35 mm for a 30 kV supply** if E_sp ≈ 1 kV/mm. Longer gaps raise thrust per watt but lose thrust once supply-limited. **Measure sparkover on your electrodes first.** | [Lit] trend + [Sim] |
| 2 | Different separation per stage? | Only with **per-stage voltage control**. With one common supply, the smallest gap limits every stage, so use equal gaps. | [Sim] |
| 3 | First stage larger than later stages? | **Yes, conditionally.** With per-stage supplies the best three-stage triple was 32/18/12 mm (at 2 W). The reason is that stage 1 has no upstream collector to lose current to. It is not about changing airflow (ion-slip effect about 2–3 %). | [Sim] |
| 4 | Emitter ring diameter | As large as the bore allows while leaving wall clearance (about 30–36 mm in a 40 mm bore). Thrust scales with emitter perimeter. | [Sim] |
| 5 | Collector ring diameter | Equal to or slightly smaller than the emitter (ratio 0.8–1.0). | [Sim] |
| 6 | Collector larger than emitter? | **No benefit found.** It draws a little more current but blocks more flow near the wall. | [Sim] |
| 7 | Pins outward or parallel to flow? | **Axial (parallel, pointing downstream): most thrust. Radial: best thrust/W** (about +30 %) but about 33 % less thrust at the same gap, and outward pins aim at the housing wall. Avoid inward-pointing pins. Prefer axial in a tight bore. | [Sim] 3-D model |
| 8 | Pin count | Diminishing returns, then loss. Mutual shielding sets in once pin spacing is below about the pin length. **About 12–16 pins on a 30 mm ring** (spacing ≈ pin length ≈ 6 mm). | [Sim] heuristic ceiling |
| 9 | Pin sharpness | Sharper tips lower onset (250 → 0.02 mm: 11.8 → 4.4 kV for 16 pins) and widen the operating window. Little thrust change below about 0.1 mm at fixed voltage. Sharp tips blunt over time. | [Sim] + [Lit] (Peek) |
| 10 | Copper vs stainless emitters | **No performance difference can be claimed.** Conductivity is irrelevant (losses about 10⁻⁸ of input). Stainless keeps its tip and resists ozone/NOx better. | [Ana] + [Qual] |
| 11 | Smooth copper rings vs copper mesh | Electrically similar. The mesh adds flow loss that depends on open area. **A thin tube collector beats both** in the model because of its low frontal area. | [Sim], loss model ASSUMED |
| 12 | Serrated copper emitters | Many small tips give low onset, but teeth shield each other like pins, are hard to make evenly, and copper teeth blunt. A commercial needle ring or a thin tungsten wire is more repeatable. | [Sim] + [Qual] |
| 13 | Effect of a third stage | About +20 % thrust for +53 % power at the same voltage (space-charge solver), plus about 100 mm more length. | [Sim] |
| 14 | Does a third stage improve efficiency? | **No. It mainly increases power consumption.** At equal power, thrust per watt falls slightly with each stage (100 % of Monte-Carlo samples). | [Sim] |
| 15 | Field interaction between stages | **Back-flow:** ions from emitter k+1 drift to collector k, producing *negative* thrust over a lever arm of length s. That is about 49 % of the current at s = d, 16 % at s = 2d and 6 % at s = 3d (space-charge solver). Keep **s ≥ 3d**, or add a guard ring at emitter voltage upstream of each later emitter, which removes back-flow in simulation ([guard.md](results/guard.md)). Shielding between neighbouring pins is the other interaction. | [Sim] |
| 16 | Best trade-off overall | See the configurations below. | [Sim] + [Qual] |

## Recommended starting configurations

### Two-stage, common supply (simplest electrically)
- **Emitter:** 12–16 stainless steel needles (about 0.05 mm tip), 6 mm long, axial, on a 30 mm
  mounting ring. Alternatively, a 0.1 mm tungsten wire ring.
- **Collector:** aluminium tube, 30 mm diameter, 10 mm long, 1 mm wall, edges rounded to at least 0.5 mm.
- **Gaps:** d1 = d2 = 25 mm. **Spacing s = 75 mm (3d).**
- **Bore:** 40 mm insulating tube (wider if radial pins are used). Length 158 mm overall, including the inlet flare and exit ring.
- **Parts:** every part is modelled in [`cad/`](../cad/README.md).
- **Supply:** one 30 kV current-limited supply. Operate at ≤ 85 % of measured sparkover.
- **Model expectation (space-charge solver):** about 3 mN net thrust at about 1.3 W and 19.5 kV. Treat this as an order of magnitude.

### Two-stage, per-stage supplies (best use of the d1 > d2 idea)
- As above, but **d1 ≈ 32 mm, d2 ≈ 18 mm**, with each stage's voltage set from its own
  measured sparkover limit.
- Adds supply complexity: two HV channels and two interlocks. Do this only after the common-supply
  build has confirmed the back-flow model.

### Two-stage with guard ring (proposed P2)
- As the common-supply build, plus a smooth 4 mm-section ring at Ø30, wired to emitter 2 and placed
  10 mm upstream of it. Stage spacing can then shrink to 37.5 mm.
- Simulation: back-flow 0 %, about 3.7 mN at about 1.4 W (+25 % thrust, 25 % shorter than P1).
- Build only after P1 has measured back-flow. The guard-to-collector-1 gap must be checked for sparkover.

### Three-stage
- Only worthwhile if **thrust or airflow at fixed voltage** matters more than efficiency or length.
- Identical stages, d = 25 mm, s = 75 mm, tube collectors. Length 258 mm overall.
- Per-stage supplies with decreasing gaps, for example 32/18/12 mm, if the electrical complexity is acceptable.

## Manufacturing notes [Qual]
- 3-D-printed housing (PETG or ASA, more ozone-tolerant than PLA) with **insulating** standoffs.
  Keep the creepage path from emitter feed to collector at least 2–3× the air gap along any surface.
- Commercial needles, press-fitted or clamped into a brass or stainless mounting ring.
  Avoid soldering stainless.
- Collectors: cut aluminium tube, deburred and edge-rounded. A sharp collector edge can start
  its own (reverse) corona.
- Make gaps adjustable with spacers, so one housing can test several d and s values.

## Electrical complexity [Qual]
- Common supply: one HV channel, one interlock, one current measurement per collector.
- Per-stage supplies: n HV channels, matching interlocks, and isolation between stages.
  Floating measurements are **not** recommended. Keep all measurements on the ground side.

## Safety
See [`safety.md`](safety.md). Ozone and NOx ventilation, interlocked enclosure,
current-limited commercial supply, and no energised adjustments.

## What must be tested before choosing a final design
1. **Back-flow fraction vs s/d**, using separate collector currents. This decides the stage count and spacing. Prediction to test: 49 / 27 / 16 / 6 % at s/d = 1 / 1.5 / 2 / 3.
2. **Sparkover voltage vs clearance** for the real electrodes and humidity. This decides the gap.
3. **I–V curves per emitter type** (onset and current scale). This calibrates the current closure.
4. **Pin count** 8 / 12 / 16 / 24 at fixed geometry.
5. **Collector type** (torus vs tube vs mesh) at equal current. This tests the flow-loss assumption.
6. **Long-run stability** (10 h) of copper vs stainless emitters: onset drift and tip radius.
