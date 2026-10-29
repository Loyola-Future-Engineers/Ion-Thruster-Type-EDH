# High-voltage safety

This device runs at 10–30 kV DC. High voltage can kill, and lesser shocks cause
involuntary movement that leads to falls, burns and dropped equipment. This document
sets the **minimum** conditions for any test. It does not replace supervision by someone
qualified in high-voltage work, or the rules of your university lab, which take precedence.

**Do not build or operate this device alone, and do not test it outside a supervised lab
with the controls below.**

## 1. Hazards

| Hazard | Source | Control |
|---|---|---|
| Electric shock | Emitters, HV lead, supply output | Interlocked enclosure. Never touch anything while energised. Current-limited supply. |
| Stored charge | Supply output capacitance, cable capacitance, the electrodes themselves, insulators that charge up | Bleeder resistor at the supply output. Grounding stick applied to every HV part before touching. Wait time after switch-off. |
| Arcing / sparks | Gap or inter-stage spacing below sparkover; dust; humidity | Operate at ≤ 85 % of the measured sparkover. Keep combustible material and solvents out of the enclosure. |
| Ozone (O₃) | Corona discharge | Ventilation. Ozone monitor. Short runs. |
| Nitrogen oxides (NOx) | Corona discharge, especially sparks | Ventilation, as for ozone. |
| Fire | Sparks igniting plastic, paper, solvent vapour | No flammables nearby. Fire extinguisher suitable for electrical fires within reach. |
| Damage to instruments | Sparks coupling into meters, balances, laptops | Protective spark gaps or gas-discharge tubes across shunts. Shielded cables. Instruments on the ground side only. |

## 2. Electrical controls

1. **Supply:** use a commercial, regulated, current-limited HV supply with a front-panel or
   remote **enable** input and a voltage monitor. Set the current limit to the lowest value
   the test needs. Do **not** use homemade voltage multipliers, ignition coils,
   flyback transformers, or microwave-oven or neon-sign transformers. They are not
   current-limited in a controlled way, and some store lethal energy.
2. **Enclosure and interlock:** all HV parts sit inside a closed enclosure (grounded metal mesh,
   or acrylic with the inner metalwork grounded). Opening the door must break the supply's
   enable circuit through a door interlock switch. Never defeat the interlock.
3. **Grounding:** a single solid earth point. Collectors return to it through their current shunts.
   The enclosure and all metal fittings are bonded to it.
4. **Discharge before contact:** after switching off, wait at least the supply's stated
   discharge time. Then apply a **grounding stick** (insulated handle, resistor plus
   direct-ground hook) to every emitter, the HV lead and each collector, and leave it
   attached while working inside.
5. **Stored energy estimate:** `E = ½ C V²`. A 1 nF output capacitance at 30 kV stores 0.45 J.
   The supply's own datasheet value must be used. Insulating parts (3-D printed housings)
   can also hold surface charge, so ground-stick them as well.
6. **No energised adjustments.** Gap, pin and probe changes are made only with the supply off,
   discharged, and grounded. If something needs adjusting during a test, switch off and
   go back to step 4.
7. **One-hand practice and clear zone:** no one reaches toward the enclosure while it is
   energised. The person at the supply controls can see the whole rig.

## 3. Ozone and nitrogen oxides

- Corona discharges produce ozone and NOx. Occupational exposure limits for ozone are
  low (for example, the US OSHA permissible exposure limit is 0.1 ppm as an 8-hour
  time-weighted average). Check the limits that apply in your country.
- Run tests in a fume hood or a well-ventilated room with the exhaust vented away from people.
- Use an **ozone monitor**. Stop if its alarm sounds or if ozone can be smelled strongly.
- Sparks produce more NOx than steady corona. Repeated sparking is also a sign the gap is too
  small, so stop and increase the clearance.
- Humid NOx forms nitric acid on electrodes and insulators. Inspect and clean between sessions
  (with the device de-energised, discharged and grounded).

## 4. Measurement safety

- **Measure current on the ground side** of the collectors only. The meter is then near earth
  potential. Protect each shunt with a spark gap or gas-discharge tube rated for the fault current.
- Measure voltage with the supply's monitor output, or a **rated** HV probe connected while
  de-energised. Never touch a probe to a live electrode.
- Airflow probes are positioned only while the supply is off. Their mounts are insulated and
  their metal parts grounded.
- Laptops and data loggers connect through isolated interfaces where possible.

## 5. Before every session

- [ ] Supervisor present. Second person in the room.
- [ ] Interlock tested (opening the door drops the output).
- [ ] Current limit set. Bleeder and grounding stick in place.
- [ ] Ventilation on. Ozone monitor on.
- [ ] No flammables in or near the enclosure. Extinguisher available.
- [ ] Sparkover margin known for this configuration (`experiments/templates/sparkover_test.csv`).
- [ ] Log sheet started (`experiments/templates/session_log.csv`).
