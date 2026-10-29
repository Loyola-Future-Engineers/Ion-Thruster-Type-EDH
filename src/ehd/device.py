"""Reduced-order performance model of a multi-stage, cylindrical EHD thruster.

Pipeline for one geometry (see docs/methodology.md for the derivation):

1. Laplace field of all electrodes at once (csm.solve), emitters at +V, collectors at 0.
2. Corona onset V0 of each emitter from Peek's wire law applied to the peak
   CSM surface field.
3. Ion paths: Laplace field lines traced from each emitter. Each flux tube i
   carries flux fraction f_i, length L_i and axial displacement dz_i, and ends
   on a downstream collector, an upstream collector, or escapes to the
   surroundings.
4. Current: coaxial-equivalent Townsend closure applied tube by tube,
   I = sum_i f_i * I_coax(L_i). Long tubes therefore carry little current.
5. Thrust per stage: T = sum_i dI_i * dz_i / mu_eff (the exact drift-limit
   identity int(j/mu) dV = I dz / mu for each flux tube), with the ion-slip
   correction mu_eff = mu (1 + u / (mu E)).
6. Air: ducted momentum balance rho A u^2 (1 + K/2) = F_EHD, net thrust rho A u^2.

Space charge is neglected in steps 1-3, which is the main modelling limitation.
"""
from dataclasses import dataclass, field

import numpy as np
from scipy.optimize import brentq

from . import csm
from .constants import Air, STANDARD_AIR
from .corona import peek_field_wire, sparkover_voltage, townsend_coax_current_per_length


@dataclass
class Stage:
    gap: float                       # axial distance emitter centre -> collector centre, m
    emitter_radius: float = 0.015    # ring radius, m
    emitter_wire: float = 1e-4       # wire / edge radius of curvature, m
    collector_radius: float = 0.015  # ring centre radius, m
    collector_minor: float = 0.002   # collector cross-section radius (torus), m
    collector_kind: str = "torus"    # "torus", "flat" (washer), "tube", "mesh"
    collector_len: float = 0.0       # axial length for "tube", m
    voltage_scale: float = 1.0       # stage voltage relative to the device voltage


@dataclass
class Device:
    stages: list
    spacing: list = field(default_factory=list)   # collector k -> emitter k+1 axial distance, m
    duct_radius: float = 0.02                     # flow-area radius, m
    k_extra: float = 0.0                          # extra loss coefficient (supports etc.)

    def length(self):
        last = self.stages[-1]
        return sum(s.gap for s in self.stages) + sum(self.spacing) + 2 * last.collector_minor


def build_electrodes(dev: Device, v_unit=1.0):
    els, z = [], 0.0
    for k, st in enumerate(dev.stages):
        if k > 0:
            z += dev.spacing[k - 1]
        els.append(csm.Electrode.torus(f"E{k+1}", st.emitter_radius, z, st.emitter_wire,
                                       v_unit * st.voltage_scale, "emitter", k + 1))
        zc = z + st.gap
        a = st.collector_minor
        if st.collector_kind == "torus":
            el = csm.Electrode.torus(f"C{k+1}", st.collector_radius, zc, a, 0.0, "collector", k + 1)
        elif st.collector_kind == "flat":       # washer: radial width 4a, thickness 2a/2
            el = csm.Electrode(f"C{k+1}", st.collector_radius + a, zc, 2 * a, a / 2, a / 2, 0.0,
                               "collector", k + 1)
        elif st.collector_kind == "tube":       # thin-walled tube starting at zc
            L = max(st.collector_len, 2 * a)
            el = csm.Electrode(f"C{k+1}", st.collector_radius, zc + L / 2 - a, a, L / 2, a, 0.0,
                               "collector", k + 1)
        elif st.collector_kind == "mesh":       # mesh across the bore, treated as a solid disc
            R = st.collector_radius + a
            el = csm.Electrode(f"C{k+1}", R / 2, zc, R / 2, a / 4, a / 4, 0.0, "collector", k + 1)
        else:
            raise ValueError(st.collector_kind)
        els.append(el)
        z = zc
    return els


@dataclass
class Geometry:
    """Voltage-independent results of the electrostatic step for one device."""
    dev: Device
    sol: object
    onset: np.ndarray          # V0 per stage at the device's voltage_scale pattern, V
    lines: list                # per-stage traced flux tubes
    residual: float


def analyse_geometry(dev: Device, air: Air = STANDARD_AIR, n_lines=64, n_per=40):
    els = build_electrodes(dev, 1.0)
    sol = csm.solve(els, n_per)
    onset, lines = [], []
    for k, st in enumerate(dev.stages):
        i = 2 * k
        _, _, en, _ = csm.surface_field(sol, i, 96)
        e_peak_per_volt = en.max()               # field per volt of device voltage
        onset.append(peek_field_wire(st.emitter_wire, air) / e_peak_per_volt)
        lines.append(csm.trace_field_lines(sol, i, n_lines))
    return Geometry(dev, sol, np.array(onset), lines, sol.residual)


def stage_current_split(geo: Geometry, k):
    """Fraction of stage-k current to own collector, other collectors, escaping."""
    ln = geo.lines[k]
    w = ln["weight"] / np.maximum(ln["length"], 1e-4) ** 2
    w = w / w.sum()
    own = 2 * k + 1
    return {"own": float(w[ln["end"] == own].sum()),
            "upstream": float(w[(ln["end"] >= 0) & (ln["end"] < 2 * k)].sum()),
            "downstream_other": float(w[ln["end"] > own].sum()),
            "escaped": float(w[ln["end"] < 0].sum())}


def evaluate(geo: Geometry, voltage, air: Air = STANDARD_AIR, k_scale=1.0, iterate_flow=True):
    """Performance at device voltage V (stage k sees V * voltage_scale)."""
    dev = geo.dev
    mu = air.mobility
    res = {"V": voltage, "stages": []}
    area = np.pi * dev.duct_radius**2
    K = dev.k_extra + loss_coefficient(dev)
    u = 0.0
    for _ in range(8 if iterate_flow else 1):
        F, I_tot, P = 0.0, 0.0, 0.0
        stages = []
        for k, st in enumerate(dev.stages):
            V = voltage * st.voltage_scale
            V0 = geo.onset[k] * st.voltage_scale
            ln = geo.lines[k]
            L = np.maximum(ln["length"], 2 * st.emitter_wire)
            Lc = np.maximum(L, 4 * st.emitter_wire)
            per_len = townsend_coax_current_per_length(V, V0, st.emitter_wire, Lc, air)
            dI = k_scale * 2 * np.pi * st.emitter_radius * ln["weight"] * per_len
            E_mean = V / np.maximum(L, 1e-4)
            mu_eff = mu * (1 + abs(u) / np.maximum(mu * E_mean, 1e-9))
            T = float(np.sum(dI * ln["dz"] / mu_eff))
            I = float(dI.sum())
            stages.append({"I": I, "T_ehd": T, "P": I * V, "V0": V0, "V": V})
            F += T; I_tot += I; P += I * V
        u_new = np.sign(F) * np.sqrt(abs(F) / (air.density * area * (1 + K / 2)))
        if abs(u_new - u) < 1e-6:
            u = u_new
            break
        u = u_new
    thrust = np.sign(u) * air.density * area * u**2      # negative if back-flow dominates
    res.update(stages=stages, F_ehd=F, I=I_tot, P=P, u=u, Q=area * u, thrust=thrust,
               T_per_P=thrust / P if P > 0 else 0.0, K=K,
               jet_eff=0.5 * air.density * area * abs(u) ** 3 / P if P > 0 else 0.0)
    return res


def loss_coefficient(dev: Device):
    """Pressure-loss coefficient of all electrodes in the bore (ASSUMED correlations).

    Rings: K = Cd * b / (1 - b)^2 with Cd = 1.2 (circular cross-section) and b the
    blocked fraction of the duct area. Mesh: K = (1 - f) / f^2 with open-area
    fraction f = 0.7 (an order-of-magnitude screen correlation).
    """
    A = np.pi * dev.duct_radius**2
    K = 0.0
    for st in dev.stages:
        for R, a in ((st.emitter_radius, st.emitter_wire), (st.collector_radius, st.collector_minor)):
            inner = max(R - a, 0)
            blocked = max(0.0, np.pi * (min(R + a, dev.duct_radius) ** 2 - inner**2)) / A
            if R + a <= dev.duct_radius:
                K += 1.2 * blocked / (1 - blocked) ** 2
        if st.collector_kind == "mesh":
            f = 0.7
            K += (1 - f) / f**2
    return K


def spark_limits(dev: Device, air: Air = STANDARD_AIR):
    """Device voltage at which each gap (stage gap and inter-stage gap) reaches sparkover."""
    lim = []
    for k, st in enumerate(dev.stages):
        clear = st.gap - st.emitter_wire - st.collector_minor
        lim.append(float(sparkover_voltage(clear, air)) / st.voltage_scale)
        if k > 0:
            prev = dev.stages[k - 1]
            clear_s = dev.spacing[k - 1] - st.emitter_wire - prev.collector_minor
            lim.append(float(sparkover_voltage(clear_s, air)) / st.voltage_scale)
    return min(lim)


def voltage_for_power(geo, p_target, air: Air = STANDARD_AIR, v_cap=None, k_scale=1.0):
    """Device voltage that draws p_target watts (None if unreachable below v_cap)."""
    v_lo = geo.onset.min() * 1.0001
    v_hi = v_cap if v_cap else spark_limits(geo.dev, air)
    f = lambda v: evaluate(geo, v, air, k_scale, iterate_flow=False)["P"] - p_target
    if v_hi <= v_lo or f(v_hi) < 0:
        return None
    return brentq(f, v_lo, v_hi, xtol=1.0)
