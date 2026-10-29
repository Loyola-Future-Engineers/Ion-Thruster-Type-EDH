"""Reference design and shared operating assumptions for all studies."""
from .device import Device, Stage

V_SUPPLY_MAX = 30e3      # ASSUMED supply limit, V (common commercial HV module class)
SPARK_MARGIN = 0.85      # operate at <= 85 % of the estimated sparkover voltage
P_COMPARE = 2.0          # W, electrical power used for equal-power comparisons

BORE_RADIUS = 0.020      # m (40 mm bore)
EMITTER_RADIUS = 0.015   # m
EMITTER_EDGE = 1e-4      # m, edge/wire radius of curvature (0.1 mm)
COLLECTOR_RADIUS = 0.015 # m
COLLECTOR_MINOR = 0.002  # m (4 mm diameter rounded collector)
GAP = 0.025              # m
SPACING = 0.025          # m, collector -> next emitter

ASSUMPTIONS = (f"Assumptions: positive corona, mu = 200 mm2/(V s), sparkover 1.0 kV/mm mean field, "
               f"Peek m=1, {BORE_RADIUS*2e3:.0f} mm bore, emitter edge r={EMITTER_EDGE*1e3:.1f} mm, "
               f"20 C / 101.3 kPa, no space charge in ion paths.")


def stage(**kw):
    base = dict(gap=GAP, emitter_radius=EMITTER_RADIUS, emitter_wire=EMITTER_EDGE,
                collector_radius=COLLECTOR_RADIUS, collector_minor=COLLECTOR_MINOR)
    base.update(kw)
    return Stage(**base)


def device(n_stages=2, gaps=None, spacings=None, per_stage_supply=False, **stage_kw):
    """Reference device. per_stage_supply=True scales each stage's voltage with its gap,
    so every stage runs at the same mean field (one supply per stage)."""
    gaps = gaps or [GAP] * n_stages
    spacings = spacings if spacings is not None else [SPACING] * (len(gaps) - 1)
    scales = [g / max(gaps) for g in gaps] if per_stage_supply else [1.0] * len(gaps)
    return Device([stage(gap=g, voltage_scale=sc, **stage_kw) for g, sc in zip(gaps, scales)],
                  list(spacings), BORE_RADIUS)


def operating_voltage(dev, air=None):
    from .device import spark_limits
    from .constants import STANDARD_AIR
    return min(V_SUPPLY_MAX, SPARK_MARGIN * spark_limits(dev, air or STANDARD_AIR))
