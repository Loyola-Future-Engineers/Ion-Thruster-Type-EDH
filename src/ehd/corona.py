"""Corona onset, current-voltage and sparkover closures.

All closures here are classical engineering approximations:
  * Peek's empirical onset-field laws for wires and spheres (Peek 1929).
  * The hyperboloid point-to-plane tip-field formula.
  * Townsend's quadratic current law I = C V (V - V0) (Townsend 1914),
    with the exact coaxial coefficient as the reference case.
  * A constant mean-field sparkover criterion (ASSUMED, see constants.Air).
"""
import numpy as np

from .constants import EPS0, Air, STANDARD_AIR


def peek_field_wire(radius_m, air: Air = STANDARD_AIR):
    """Corona onset surface field for a cylindrical wire, V/m.

    Peek: E = 31 m delta (1 + 0.308 / sqrt(delta r_cm)) kV/cm.
    """
    r_cm = np.asarray(radius_m) * 100.0
    d = air.delta
    return 31e5 * air.peek_m * d * (1.0 + 0.308 / np.sqrt(d * r_cm))


def peek_field_sphere(radius_m, air: Air = STANDARD_AIR):
    """Corona onset surface field for a sphere (used for needle tips), V/m.

    Peek: E = 27.2 m delta (1 + 0.54 / sqrt(delta r_cm)) kV/cm.
    """
    r_cm = np.asarray(radius_m) * 100.0
    d = air.delta
    return 27.2e5 * air.peek_m * d * (1.0 + 0.54 / np.sqrt(d * r_cm))


def tip_field_hyperboloid(voltage, tip_radius, gap):
    """Laplacian tip field of a hyperboloidal needle facing a plane, V/m.

    E_tip = 2 V / (r ln(4 d / r)), valid for d >> r.
    """
    return 2.0 * voltage / (tip_radius * np.log(4.0 * gap / tip_radius))


def onset_voltage_needle(tip_radius, gap, air: Air = STANDARD_AIR):
    """Onset voltage of an isolated needle-to-plane gap, V."""
    return peek_field_sphere(tip_radius, air) * tip_radius * np.log(4.0 * gap / tip_radius) / 2.0


def onset_voltage_coax(wire_radius, outer_radius, air: Air = STANDARD_AIR):
    """Onset voltage of a coaxial wire-cylinder gap, V (exact Laplace field)."""
    return peek_field_wire(wire_radius, air) * wire_radius * np.log(outer_radius / wire_radius)


def townsend_coax_current_per_length(voltage, v0, wire_radius, outer_radius, air: Air = STANDARD_AIR):
    """Townsend's coaxial result I/L = 8 pi eps0 mu V (V - V0) / (R^2 ln(R/r)), A/m.

    Zero below onset.
    """
    v = np.asarray(voltage, dtype=float)
    c = 8 * np.pi * EPS0 * air.mobility / (outer_radius**2 * np.log(outer_radius / wire_radius))
    return np.where(v > v0, c * v * (v - v0), 0.0)


def townsend_current(voltage, v0, emitter_length, path_length, wire_radius, air: Air = STANDARD_AIR,
                     k_scale=1.0):
    """Coaxial-equivalent Townsend closure for a line emitter of arbitrary shape, A.

    Uses the coaxial coefficient with R replaced by the flux-weighted mean
    ion path length. This reproduces the coaxial case exactly and is otherwise
    an approximation (uncertainty treated as a factor-of-two band, k_scale).
    """
    return k_scale * emitter_length * townsend_coax_current_per_length(
        voltage, v0, wire_radius, max(path_length, 2 * wire_radius), air)


def sigmond_point_current(voltage, v0, gap, air: Air = STANDARD_AIR, k_scale=1.0):
    """Point-to-plane current, A, using Sigmond's saturation scaling.

    Sigmond (1982): space-charge-limited current I_sat ~ 2 eps0 mu V^2 / d.
    Combined with onset as I = 2 eps0 mu V (V - V0) / d (Townsend-like form).
    """
    v = np.asarray(voltage, dtype=float)
    return np.where(v > v0, k_scale * 2 * EPS0 * air.mobility * v * (v - v0) / gap, 0.0)


def sparkover_voltage(gap, air: Air = STANDARD_AIR):
    """Mean-field sparkover estimate V_sp = E_sp * d, V (ASSUMED criterion)."""
    return air.e_spark * np.asarray(gap)
