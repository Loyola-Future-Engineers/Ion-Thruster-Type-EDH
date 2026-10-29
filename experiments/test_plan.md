# Experimental validation plan

**Status: no experiments have been performed. This repository contains no measured data.**
Everything below is a plan. Read [`docs/safety.md`](../docs/safety.md) before building anything.

## 1. Purpose

The models in this repository are unvalidated. Physical tests should first check the
model's **structural assumptions**, in priority order:

| # | Model claim | Measurement that tests it | Why it matters |
|---|---|---|---|
| 1 | About 49 / 16 / 6 % of a later stage's current flows back to the previous collector at s/d = 1 / 2 / 3 (space-charge solver) | Current to **each collector measured separately**, at several d/s ratios. Energise emitter 2 alone (emitter 1 at ground through a 10 MΩ resistor) so C1 current is purely stage-2 back-flow, then repeat with both energised | Drives every multi-stage conclusion |
| 2 | Maximum safe operating voltage is set by mean-field sparkover of about 1 kV/mm | Sparkover voltage vs clearance for the real electrodes (`sparkover_test.csv`) | Sets the optimum gap (about 35 mm at 30 kV) |
| 3 | Onset follows Peek's law with the CSM field | Onset voltage per emitter type (I–V knee) | Sets the operating window |
| 4 | Current follows I ∝ V(V − V0) with a closure factor in 0.5–2 | Full I–V sweep | Absolute thrust scale |
| 5 | Thrust = I·⟨dz⟩/μ minus flow losses | Thrust vs current at fixed geometry. The slope gives an effective `<dz>/mu` | Tests the drift identity and the mobility |
| 6 | Pin optimum near spacing ≈ pin length | Thrust and I–V for 8 / 12 / 16 / 24 pins | Pin count recommendation |
| 7 | Collector type matters mainly through flow loss | Torus vs tube vs mesh at equal current | Collector recommendation |

## 2. Rig

- **Supply:** commercial, current-limited, regulated DC high-voltage module with a voltage
  monitor output, at or below 30 kV, with the current limit set as low as the test allows
  (for example 1 mA). No home-built multipliers and no flyback/neon-transformer supplies.
- **Enclosure:** grounded metal-mesh or acrylic enclosure with a door interlock that cuts the
  HV supply enable line (see `docs/safety.md`).
- **Thrust:** the thruster sits on insulating standoffs (at least 100 mm, PTFE or acetal) on a
  precision balance (0.001 g resolution; 1 mg ≈ 9.8 µN), **exhaust pointing up**, so thrust
  reads as a weight reduction. A grounded metal shield plate between the HV parts and the
  balance pan blocks electrostatic forces on the balance. The HV lead is a light, slack
  flexible silicone HV wire, routed so it cannot pull on the device.
- **Current:** measure on the **ground side** of each collector (low voltage relative to earth)
  using a series shunt resistor and meter. Add a protective spark gap or gas-discharge
  tube across each shunt. One shunt per collector gives the back-flow fraction.
- **Voltage:** the supply's calibrated monitor output, cross-checked once with a rated HV divider
  probe while the device is de-energised and set up for measurement.
- **Airflow:** vane anemometer or pitot tube with a micromanometer, at least 100 mm downstream of
  the exit, on an insulated positioning arm. The probe must be grounded or fully insulated, and
  is only repositioned with the supply off and discharged.
- **Environment:** temperature, relative humidity and pressure logged every session.

## 3. Procedure (per configuration)

1. Fill in `templates/configuration.csv`, photograph the electrodes, and measure the tip radius.
2. With the supply **off and discharged**, zero the balance and record it.
3. Close the enclosure and confirm the interlock.
4. Ramp the voltage in 1 kV steps from 0 to the first visible or audible discharge. Hold each step
   30 s, then record all fields in `iv_thrust_sweep.csv`. Stop at the lower of the supply limit
   and **the first spark event**. After any spark, drop to 85 % of that voltage and do not exceed it.
5. Ramp back down. Up/down hysteresis indicates drift or charging.
6. Turn off, wait for discharge, apply the grounding stick, re-zero the balance, and check drift.
7. Repeat the sweep **three times**, and on a second day for repeatability.
8. For airflow, use the voltage set-points from the sweep and traverse the probe radially
   across the exit (`airflow_traverse.csv`). Integrate `Q = ∫ u 2πr dr`.

## 4. Controls and interference checks

| Check | How | What it detects |
|---|---|---|
| No-corona control | Apply voltage just below onset (current < 0.1 µA) | Electrostatic attraction between device and surroundings or balance. Should read zero thrust. |
| Reversed device | Mount the thruster with exhaust down | Sign of the thrust reading. Rules out balance artefacts. |
| HV lead only | Energise with the emitter disconnected | Force from the lead or field on the balance |
| Drafts | Record balance noise with everything off, doors closed | Baseline noise floor |
| Ozone / heat | Long run at fixed V. Watch for creeping readings | Thermal plumes, ozone changing air properties |
| Leakage | Supply current minus the sum of collector currents | Current leaking over insulator surfaces |

## 5. Uncertainty (GUM method)

For each quantity, combine:
- **Type A:** standard deviation of repeated readings / √n.
- **Type B:** instrument specification (resolution/√12, stated accuracy/√3 for rectangular).

`u_c = sqrt(sum u_i^2)`. Report the expanded uncertainty `U = 2 u_c` (≈95 %).

Derived quantities (propagated):
- Thrust `T = g · Δm`: `u_T = g · u_Δm`.
- Power `P = V I`: `u_P/P = sqrt((u_V/V)^2 + (u_I/I)^2)`.
- Thrust/power: `u_TP/TP = sqrt((u_T/T)^2 + (u_P/P)^2)`.
- Back-flow fraction `b = I_upstream / (I_upstream + I_own)`, propagated from both shunt readings.

`experiments/analyse.py` implements these formulas and fills a summary table from
a completed `iv_thrust_sweep.csv`. It refuses to run on the empty templates.

## 6. Model comparison

Once data exists, overlay measured I–V, thrust–power and back-flow on the model curves
(same geometry file) and re-fit only **two** parameters, the current closure factor and the
sparkover field. If back-flow disagrees by more than a factor of 2, the
space-charge-free ion-path assumption is wrong for this geometry, and the multi-stage
conclusions in `docs/results/stages.md` must be revisited.
