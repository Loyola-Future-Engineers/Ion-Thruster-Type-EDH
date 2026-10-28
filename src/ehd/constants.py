"""Physical constants and ambient-air properties.

Every value carries a source tag. Values tagged ASSUMED are modelling inputs
whose uncertainty is propagated in simulations/sensitivity.py; they are not
measurements made by this project.
"""
from dataclasses import dataclass, replace

EPS0 = 8.8541878128e-12  # F/m, CODATA 2018
R_AIR = 287.05           # J/(kg K), specific gas constant of dry air
P_REF = 101_325.0        # Pa, standard atmosphere
T_REF = 293.15           # K, Peek's reference temperature (20 C)


@dataclass(frozen=True)
class Air:
    """Ambient air state plus the transport/breakdown parameters the models need.

    mobility_ref: positive-ion mobility at reference density, m^2/(V s).
        ASSUMED 2.0e-4 with a 1.8e-4 to 2.2e-4 band, the range commonly used for
        positive corona ions in air (see docs/literature_review.md).
    e_spark_ref: average field V/d at which a positive corona gap sparks over, V/m.
        ASSUMED 1.0e6 with a 0.7e6 to 1.4e6 band. Sparkover depends strongly on
        geometry, humidity and supply impedance and must be measured on the rig.
    peek_m: Peek surface-irregularity factor (1.0 polished, ~0.8 rough/oxidised).
    """
    temperature_K: float = T_REF
    pressure_Pa: float = P_REF
    relative_humidity: float = 0.5
    mobility_ref: float = 2.0e-4
    e_spark_ref: float = 1.0e6
    peek_m: float = 1.0

    @property
    def density(self) -> float:
        """Dry-air ideal-gas density, kg/m^3 (humidity correction < 1 % and ignored)."""
        return self.pressure_Pa / (R_AIR * self.temperature_K)

    @property
    def delta(self) -> float:
        """Peek relative air density, 1.0 at 101.325 kPa and 20 C."""
        return (self.pressure_Pa / P_REF) * (T_REF / self.temperature_K)

    @property
    def mobility(self) -> float:
        """Ion mobility scaled inversely with gas number density (standard scaling)."""
        return self.mobility_ref / self.delta

    @property
    def e_spark(self) -> float:
        """Sparkover field scaled linearly with relative density (similarity law)."""
        return self.e_spark_ref * self.delta

    def with_(self, **kw) -> "Air":
        return replace(self, **kw)


STANDARD_AIR = Air()

# Bulk electrical conductivity at ~20 C, S/m (handbook values, e.g. CRC Handbook
# of Chemistry and Physics). Used only to show that electrode resistance is
# irrelevant at corona currents.
CONDUCTIVITY = {
    "copper": 5.96e7,
    "aluminium": 3.77e7,
    "stainless_304": 1.39e6,
    "tungsten": 1.79e7,
}
