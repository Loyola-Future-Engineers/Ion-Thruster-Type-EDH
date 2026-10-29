# Literature review

Bibliography: [`references/references.bib`](../references/references.bib) is generated from Crossref by
`references/build_bib.py`. All DOIs below resolve.

**How to read this document.** Each summary reports what a paper states
in its abstract or is widely known for. Where a number is quoted, it comes
from the paper's own abstract. Where I am unsure of a detail, I say so rather
than guess. Nothing here was measured by this project.

## 1. Foundations of corona-driven ionic wind

| Ref | Contribution relevant to this project |
|---|---|
| [Townsend 1914](https://doi.org/10.1080/14786440708635186) | Quadratic current law `I = C V (V - V0)` for coaxial cylinders. Used here as the current closure. |
| Peek 1929 (book) | Empirical corona-onset fields for wires and spheres. Used here for onset voltages. |
| [Robinson 1961](https://doi.org/10.1109/TCE.1961.6373091) | Classic measurements and analysis of electric-wind air movement. Historical basis for momentum-transfer models. |
| [Christenson & Moller 1967](https://doi.org/10.2514/3.4302) | Early analysis of ion-neutral propulsion in air and its efficiency limits. |
| [Sigmond 1982](https://doi.org/10.1063/1.330557) | Unipolar charge-drift formula, Warburg current distribution and the saturation current `I_s ~ 2 mu eps0 V^2 / d` for point-to-plane coronas. Used here for needle current scaling. |
| [Singer et al. 1974](https://doi.org/10.1109/TPAS.1974.293898) | The charge simulation method (CSM) for high-voltage fields. This is the method used in `src/ehd/csm.py`. |
| [Adamiak & Atten 2004](https://doi.org/10.1016/j.elstat.2004.01.021) | Self-consistent numerical simulation of point-plane corona (Poisson plus charge transport). Reference for the space-charge solver listed as future work. |
| [Tajmar 2004](https://doi.org/10.2514/1.9095) | Shows that "Biefeld-Brown" lifter thrust is a corona-wind effect, not a new force. |

## 2. EHD thruster performance

| Ref | Findings (from the abstract) |
|---|---|
| [Masuyama & Barrett 2013](https://doi.org/10.1098/rspa.2012.0623) | Single-stage thrusters agree with a 1-D theory. A longer gap requires higher onset voltage, gives less thrust per volt, more thrust per current, and more thrust per power. Thrust-to-power up to about 100 N/kW was obtained. They also tested dual-stage designs with an intermediate electrode. |
| [Gilmore & Barrett 2015](https://doi.org/10.1098/rspa.2014.0912) | Thrust density of wire-to-cylinder pairs in parallel and in series. Estimated maximum about 3.3 N/m² and 15 N/m³. Reports a trade-off between thrust density and thrust-to-power ratio. Inter-pair and stage spacings were varied. |
| [Xu et al. 2018](https://doi.org/10.1038/s41586-018-0707-9) | First sustained flight of a fixed-wing aeroplane propelled by EAD (corona wire-to-airfoil electrodes). |
| [Xu, He & Barrett 2019](https://doi.org/10.1063/1.5100524) | Using a dielectric-barrier-discharge ion source with a separate DC accelerating field breaks the corona thrust/efficiency trade-off. Up to 20 N/kW at 50 mN/m reported. |
| [Gomez-Vega et al. 2023](https://doi.org/10.2514/1.J061948) | Proposes and models multistaged ducted EAD thrusters (stages in series in a duct with inlet and nozzle) using 1-D momentum theory with ideal-stage and wire-to-airfoil stage limits. This is the closest published analogue of this project. |
| [Moreau et al. 2013](https://doi.org/10.1088/0022-3727/46/47/475204) | Direct force measurements of a wire-to-cylinder DC corona in atmospheric air. |
| [Moreau et al. 2015](https://doi.org/10.1016/j.elstat.2015.05.025) | Force from one wire emitter facing several cylinder collectors, applied to electric propulsion. |
| [Monrolin et al. 2017](https://doi.org/10.2514/1.J055928), [2018](https://doi.org/10.1103/PhysRevFluids.3.063701) | EHD thrust experiments and an estimate of effective ion mobility from force/current measurements in wire-to-cylinders corona. |
| [Coseru et al. 2021](https://doi.org/10.1063/5.0041061) | Numerical electro-drift model with the Kaptsov approximation. Reports good agreement with many experiments for current and force, and confirms optimal configurations for staggered emitter/collector arrays. Air drag and the Kaptsov approximation explain some discrepancies. |
| [Einat & Kalderon 2014](https://doi.org/10.1063/1.4890353) | Lifter geometry study. Stronger electrode asymmetry increases force. Reports about 9× improvement through geometry choices. |

## 3. Multi-stage ionic wind

| Ref | Relevance |
|---|---|
| [Rickard et al. 2006](https://doi.org/10.1016/j.elstat.2005.09.005) | Ion-driven gas flows maximized by staging. Directly relevant to stage count and stage spacing. No abstract in Crossref, so details are not summarized here. |
| [Rickard & Dunn-Rankin 2007](https://doi.org/10.1016/j.elstat.2007.04.003) | Numerical simulation of a **tubular** ion-driven wind generator. Closest geometry to a cylindrical thruster. |
| [Kim et al. 2010](https://doi.org/10.1016/j.elstat.2009.09.001) | Velocity and energy-conversion efficiency of a multistage ionic wind generator. Relevant to two- versus three-stage comparisons. |
| [Moreau & Touchard 2008](https://doi.org/10.1016/j.elstat.2007.08.006) | Methods for enhancing the mechanical efficiency of electric wind. |

**Gap in this review.** The three multistage papers above have no abstracts in
Crossref, and their full texts were not accessible in this session. Their
quantitative findings are therefore **not** used to calibrate or check the
model. Reading them is the first follow-up task in `PROGRESS.md`.

## 4. Small-scale EHD flyers

| Ref | Relevance |
|---|---|
| [Drew & Pister 2017](https://doi.org/10.1109/MARSS.2017.8001934) | Ionocraft microrobot take-off with no moving parts. |
| [Prasad et al. 2020](https://doi.org/10.1371/journal.pone.0231362) | Laser-microfabricated EHD thruster for centimetre-scale aerial robots. |

## 5. What the literature does and does not settle for this design

| Question | Literature position | Status |
|---|---|---|
| Longer gap → better thrust per watt | Established experimentally (Masuyama & Barrett 2013) | Literature |
| Thrust density vs efficiency trade-off | Established (Gilmore & Barrett 2015; Xu et al. 2019) | Literature |
| Stage spacing must avoid back-flow to the previous collector | Follows from the drift identity (section 3.3 of physics.md). Gilmore & Barrett 2015 varied stage spacing experimentally; their detailed results were not accessed here | Analyzed here (`docs/results/spacing.md`) |
| Ring-to-ring axisymmetric multi-stage geometry with pins | No direct published dataset found in this session | Open: requires testing |
| Copper vs stainless emitters | No quantitative comparison found. Bulk conductivity is irrelevant at µA–mA currents. Surface condition and erosion dominate. | Qualitative only |
| Mesh vs ring collectors | No direct dataset found for this geometry | Modelled here; open |
