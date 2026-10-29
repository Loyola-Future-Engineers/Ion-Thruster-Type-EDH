"""3-D charge-simulation model of a ring of discrete emitter pins.

Each pin is a prolate spheroid (semi-axes c along the pin, b across it). Its tip
radius of curvature is r_tip = b^2 / c, so a sharp needle is a slender spheroid.
An isolated equipotential spheroid is represented exactly by a uniform line
charge between its foci. Here the focal segment is split into M sub-segments
with independent densities, so the charge can redistribute under the influence
of neighbouring pins, the mounting ring and the collector.

By rotational symmetry all N pins carry identical charge patterns, so the
unknowns are one pin's M densities plus axisymmetric ring charges for the
mounting ring and the collector torus.

Scope: Laplace field. Used for tip-field enhancement, mutual shielding between
pins, and corona onset. Pin currents use Sigmond's point-to-plane scaling,
capped by the continuous-ring Townsend current. This is a heuristic and is
labelled as such in every output.
"""
from dataclasses import dataclass

import numpy as np

from .constants import EPS0, Air, STANDARD_AIR
from .corona import peek_field_sphere, townsend_coax_current_per_length
from .csm import ring_potential

K_E = 1.0 / (4 * np.pi * EPS0)


def segment_potential(p0, p1, x):
    """Potential per unit line density of segments p0->p1 (S,3) at points x (P,3): (P, S)."""
    r1 = np.linalg.norm(x[:, None, :] - p0[None], axis=2)
    r2 = np.linalg.norm(x[:, None, :] - p1[None], axis=2)
    L = np.linalg.norm(p1 - p0, axis=1)[None]
    return K_E * np.log((r1 + r2 + L) / np.maximum(r1 + r2 - L, 1e-300))


@dataclass
class PinRing:
    n_pins: int = 16
    ring_radius: float = 0.015       # pin-base circle radius, m
    pin_length: float = 0.006        # m
    tip_radius: float = 5e-5         # m
    orientation: str = "axial"       # axial | radial_out | radial_in | angled_out | angled_in
    base_wire: float = 5e-4          # mounting-ring cross-section radius, m
    collector_radius: float = 0.015
    collector_minor: float = 0.002
    gap: float = 0.025               # axial distance mounting ring -> collector centre, m

    def direction(self):
        s = np.sqrt(0.5)
        return {"axial": (0, 0, 1), "radial_out": (1, 0, 0), "radial_in": (-1, 0, 0),
                "angled_out": (s, 0, s), "angled_in": (-s, 0, s)}[self.orientation]

    def tip(self):
        return np.array([self.ring_radius, 0, 0]) + self.pin_length * np.array(self.direction(), float)

    def tip_to_collector(self):
        """Shortest distance from pin tip to the collector torus surface, m."""
        t = self.tip()
        rr = np.hypot(t[0], t[1])
        return np.hypot(rr - self.collector_radius, self.gap - t[2]) - self.collector_minor

    def axial_lever(self):
        return self.gap - self.tip()[2]


def _rot(theta):
    c, s = np.cos(theta), np.sin(theta)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def solve(pr: PinRing, m_seg=14, n_ring=16, n_coll=24):
    c = pr.pin_length / 2
    b = np.sqrt(pr.tip_radius * c)
    f = np.sqrt(c**2 - b**2)
    u0 = np.array(pr.direction(), float)
    base0 = np.array([pr.ring_radius, 0, 0])
    centre0 = base0 + u0 * c
    # focal sub-segments, finer near the tip (t -> +1)
    edges = -np.cos(np.linspace(0, np.pi, m_seg + 1))
    s0 = centre0 + np.outer(edges[:-1] * f, u0)
    s1 = centre0 + np.outer(edges[1:] * f, u0)
    rots = [_rot(2 * np.pi * k / pr.n_pins) for k in range(pr.n_pins)]

    def pin_matrix(x):
        A = np.zeros((len(x), m_seg))
        for R in rots:
            A += segment_potential(s0 @ R.T, s1 @ R.T, x)
        return A

    # ring charges for the mounting ring and the collector (axisymmetric bodies)
    def ring_set(R0, z0, a, n):
        ang = np.linspace(0, 2 * np.pi, n, endpoint=False)
        q = np.column_stack([R0 + 0.5 * a * np.cos(ang), z0 + 0.5 * a * np.sin(ang)])
        pts = np.column_stack([R0 + a * np.cos(ang + np.pi / n), z0 + a * np.sin(ang + np.pi / n)])
        return q, pts

    qb, pb = ring_set(pr.ring_radius, 0.0, pr.base_wire, n_ring)
    qc, pc = ring_set(pr.collector_radius, pr.gap, pr.collector_minor, n_coll)
    qa = np.concatenate([qb[:, 0], qc[:, 0]]); qz = np.concatenate([qb[:, 1], qc[:, 1]])

    def ring_matrix(x):
        return ring_potential(qa, qz, np.hypot(x[:, 0], x[:, 1]), x[:, 2])

    # collocation on pin 0: spheroid surface, several azimuths around the pin axis
    perp1 = np.cross(u0, [0, 0, 1.0]) if abs(u0[2]) < 0.9 else np.array([0, 1.0, 0])
    perp1 /= np.linalg.norm(perp1); perp2 = np.cross(u0, perp1)
    ts = np.cos(np.linspace(0.02, 0.85 * np.pi, 3 * m_seg))   # skip the buried base end
    pin_pts = []
    for t in ts:
        rad = b * np.sqrt(max(1 - t**2, 0))
        for phi in np.linspace(0, 2 * np.pi, 4, endpoint=False):
            pin_pts.append(centre0 + u0 * c * t + rad * (np.cos(phi) * perp1 + np.sin(phi) * perp2))
    pin_pts.append(centre0 + u0 * c)                          # the tip itself
    pin_pts = np.array(pin_pts)
    half = np.pi / pr.n_pins
    ring_pts = np.vstack([np.column_stack([p[:, 0] * np.cos(a), p[:, 0] * np.sin(a), p[:, 1]])
                          for p in (pb, pc) for a in (0.0, half)])
    X = np.vstack([pin_pts, ring_pts])
    V = np.concatenate([np.ones(len(pin_pts)), np.ones(2 * n_ring), np.zeros(2 * n_coll)])
    A = np.hstack([pin_matrix(X), ring_matrix(X)])
    sc = np.abs(A).max(axis=0)
    sol, *_ = np.linalg.lstsq(A / sc, V, rcond=None)
    sol /= sc

    def potential(x):
        x = np.atleast_2d(x)
        return np.hstack([pin_matrix(x), ring_matrix(x)]) @ sol

    tip = centre0 + u0 * c
    h = pr.tip_radius / 40
    grad = np.array([(potential(tip + h * e) - potential(tip - h * e))[0] / (2 * h) for e in np.eye(3)])
    resid = float(np.abs(potential(X) - V).max())
    return {"E_tip_per_V": float(np.linalg.norm(grad)), "residual": resid, "potential": potential,
            "pin_charge": float(np.sum(sol[:m_seg] * np.linalg.norm(s1 - s0, axis=1)))}


def performance(pr: PinRing, voltage, air: Air = STANDARD_AIR, k_scale=1.0, field=None):
    """Onset, current, thrust and power of a pin ring at the given voltage (single stage)."""
    field = field or solve(pr)
    v0 = peek_field_sphere(pr.tip_radius, air) / field["E_tip_per_V"]
    d_tc = pr.tip_to_collector()
    mu = air.mobility
    i_pins = pr.n_pins * k_scale * 2 * EPS0 * mu * voltage * max(voltage - v0, 0) / d_tc
    # continuous-ring ceiling: a dense pin ring cannot exceed a corona "sheet" of the same perimeter
    i_ring = k_scale * 2 * np.pi * pr.ring_radius * townsend_coax_current_per_length(
        voltage, v0, max(pr.tip_radius, 1e-5), max(d_tc, 1e-3), air)
    current = float(min(i_pins, i_ring))
    thrust = current * pr.axial_lever() / mu
    return {"V0": float(v0), "I": current, "I_pins_uncapped": float(i_pins), "I_ring_cap": float(i_ring),
            "T_ehd": thrust, "P": current * voltage, "E_tip_per_V": field["E_tip_per_V"],
            "d_tip_collector": d_tc, "lever": pr.axial_lever(), "residual": field["residual"]}
