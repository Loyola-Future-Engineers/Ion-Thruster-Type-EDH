# EHD physics and governing equations

This document states the physics the models rely on, and the simplifying
assumptions used to reduce it to something computable. Sections marked
**[literature]** summarize established theory; sections marked **[this
project]** are derivations or choices made here.

## 1. Mechanism [literature]

A positive DC corona forms in the thin region around a sharp emitter where the
field is high enough for electron-impact ionization to sustain itself
(roughly a few hundred micrometres thick for thin wires). Outside it, the gap
is a *unipolar drift region*: positive ions drift toward the grounded collector
at velocity `w = mu E`. They collide with neutral molecules, which receive the
ions' momentum. The neutral gas therefore feels a body force

```
f = rho_q E        (N/m^3)
```

and the reaction on the electrodes is the thrust. There is no thrust in vacuum.
This is the corona-wind explanation of the "Biefeld-Brown effect" ([Tajmar 2004](https://doi.org/10.2514/1.9095)).

## 2. Governing equations [literature]

For the drift region with ion mobility `mu`, neglecting ion diffusion:

| Equation | Form |
|---|---|
| Poisson | `div(eps0 grad phi) = -rho_q`, `E = -grad phi` |
| Charge conservation | `div(j) = 0`, `j = rho_q (mu E + u)` |
| Neutral momentum (incompressible) | `rho (u . grad) u = -grad p + mu_air lap u + rho_q E` |
| Mass | `div(u) = 0` |

The ion-drift term `mu E` (around 100 m/s at 0.5 kV/mm) is much larger than
typical ionic-wind speeds (1–5 m/s). The ion transport is therefore close to
one-way coupled to the flow, and the electric problem can be solved first.

Boundary conditions used in the literature (for example [Adamiak & Atten 2004](https://doi.org/10.1016/j.elstat.2004.01.021),
[Coseru et al. 2021](https://doi.org/10.1063/5.0041061)):
- `phi = V` on the emitter, `phi = 0` on the collector.
- Kaptsov's assumption: the emitter surface field stays at the corona onset
  value `E_on` once the corona is on. Charge injection adjusts to hold it there.
- Peek's empirical law gives `E_on`.

## 3. Closures used in this project

### 3.1 Corona onset field [literature]
Peek's laws ([Peek 1929]), with `delta` the relative air density and `m` the
surface-irregularity factor:

- wire, radius `r` in mm: `E_on = 3.1 m delta (1 + 0.974 / sqrt(delta r))` kV/mm
- sphere / needle tip: `E_on = 2.72 m delta (1 + 1.708 / sqrt(delta r))` kV/mm

(Peek's original form uses r in cm and kV/cm. The constants above are the same law rewritten for mm.)

### 3.2 Current-voltage law [literature]
Townsend's coaxial result ([Townsend 1914](https://doi.org/10.1080/14786440708635186)):

```
I / L = 8 pi eps0 mu V (V - V0) / (R^2 ln(R / r))
```

Sigmond's point-to-plane saturation current
([Sigmond 1982](https://doi.org/10.1063/1.330557)) is `I_sat ~ 2 mu eps0 V^2 / d`.

### 3.3 Thrust in the drift limit [literature, with a project derivation]
With `u << mu E`, `j = rho_q mu E`, so `f = j / mu`. Integrating over a single
ion flux tube that carries current `dI` from the emitter to the point where it
lands:

```
F_z(tube) = (1/mu) * integral(j_z dV) = dI * dz / mu
```

Here `dz` is the axial displacement between where the tube starts and where it
ends. **The path shape does not matter, only its end points.** Summing tubes:

```
T = sum_i dI_i dz_i / mu,     P = I V,     T / P = <dz> / (mu V)
```

For a 1-D gap of length `d` this is the result of
[Masuyama & Barrett 2013](https://doi.org/10.1098/rspa.2012.0623),
`T / P = d / (mu V)`. That paper also confirms experimentally that a longer
gap gives more thrust per watt and less thrust per volt.

Consequences used throughout this project:
1. Efficiency (thrust per watt) depends only on the axial lever arm and the
   voltage. Electrode shape matters through the current it draws and its
   onset and sparkover voltages.
2. Ions that drift **backwards** (to the previous stage's collector) have
   `dz < 0` and produce **negative** thrust while still consuming power. This
   is the main electrical interaction between stages.
3. Radial force components cancel by symmetry, but the current they carry
   still costs power. Ions landing on a much larger collector ring therefore
   lower thrust per watt only if they lower `<dz>`.

### 3.4 Ion-slip correction [this project]
With wind speed `u`, `j = rho_q (mu E + u)`, so for a fixed current the
charge density, and with it the force, falls by a factor `1 / (1 + u/(mu E))`.
At `u = 3 m/s` and `mu E = 100 m/s` that is a 3 % effect. Downstream stages see
faster air, so they lose slightly more, but this alone does not justify
large stage-to-stage gap differences (see `docs/results/spacing.md`).

### 3.5 Air-flow model [this project, standard momentum theory]
The bore of radius `R_d` is treated as a duct. Air enters from rest, and the
total EHD force `F` is balanced by exit momentum flux plus pressure losses
from the electrodes in the flow:

```
F = rho A u^2 (1 + K/2),     T_net = rho A u^2,     Q = A u
```

`K` is the sum of loss coefficients for rings (blockage correlation) and
meshes (screen correlation). Both are order-of-magnitude **assumptions**, see
`src/ehd/device.py`. As a consistency check, the jet kinetic power `½ rho A u^3`
must be less than the electrical power. The test suite enforces this.

Multistaged ducted thrusters are modelled with the same 1-D momentum-theory
idea, in much greater depth, by [Gomez-Vega et al. 2023](https://doi.org/10.2514/1.J061948).

## 4. What the model leaves out

| Simplification | Consequence | Direction of error |
|---|---|---|
| Laplace field (no space charge) for ion paths, in the reduced model | Checked with the space-charge solver (Phase H). The reduced model under-predicts back-flow (9 % vs 16 % at s = 2d) and over-predicts current about 2.2× | Now quantified |
| Coaxial-equivalent Townsend closure for non-coaxial shapes | Current magnitude uncertain to roughly a factor of 2 | Treated as uncertainty band `k_scale` |
| Peek onset with `m = 1` | Rough or oxidized electrodes start corona earlier | Onset overestimated for real parts |
| Mean-field sparkover `E_sp = 1 kV/mm` | Real sparkover depends on geometry, humidity and supply | ±40 % band in sensitivity runs |
| Axisymmetric emitter (wire ring) | Discrete pins are handled by a separate 3-D model | See `docs/results/pins.md` |
| 1-D duct flow, fully mixed | Real ionic wind is an annular jet near the ring | Volumetric flow probably overestimated |
| Negative corona, back-corona, streamers, ozone chemistry | Not modelled | — |

These are the reasons the outputs are labelled **numerical simulation
(unvalidated reduced-order model)** everywhere they appear.
