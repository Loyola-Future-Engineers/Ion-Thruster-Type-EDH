"""Axisymmetric electrostatic solver by the Charge Simulation Method (CSM).

Each electrode is a body of revolution whose (r, z) cross-section is a rounded
rectangle (a torus, a flat ring, a tube or a disc). Its surface charge is
replaced by ring charges placed inside the body; their magnitudes are chosen so
the electrode contour sits at the prescribed potential (least-squares
collocation). The potential of a ring charge is exact in 3-D free space:

    phi(r, z) = q / (4 pi eps0) * (2/pi) K(m) / sqrt((r + a)^2 + (z - z0)^2),
    m = 4 a r / ((r + a)^2 + (z - z0)^2)

so the far-field boundary condition (phi -> 0 at infinity) is satisfied by
construction and no mesh or outer boundary is needed.

Scope: Laplace field only (no space charge). This is valid at corona onset and
is used here for onset voltages, field shapes and ion-path geometry. It is not
a solution of the coupled EHD problem; see docs/methodology.md.
"""
from dataclasses import dataclass, field

import numpy as np
from scipy.special import ellipe, ellipk

from .constants import EPS0

K_E = 1.0 / (4 * np.pi * EPS0)


@dataclass
class Electrode:
    """Rounded-rectangle body of revolution.

    r_c, z_c: centre of the cross-section (m). half_w: radial half-width,
    half_h: axial half-height, corner: corner radius (<= min(half_w, half_h)).
    A torus of minor radius a is half_w = half_h = corner = a.
    """
    name: str
    r_c: float
    z_c: float
    half_w: float
    half_h: float
    corner: float
    potential: float
    kind: str = "collector"          # "emitter" or "collector"
    stage: int = 0

    @classmethod
    def torus(cls, name, ring_radius, z, minor_radius, potential, kind="collector", stage=0):
        return cls(name, ring_radius, z, minor_radius, minor_radius, minor_radius, potential, kind, stage)

    def sdf(self, r, z):
        """Signed distance from (r, z) to the cross-section boundary (negative inside)."""
        qx = np.abs(r - self.r_c) - (self.half_w - self.corner)
        qy = np.abs(z - self.z_c) - (self.half_h - self.corner)
        outside = np.hypot(np.maximum(qx, 0), np.maximum(qy, 0))
        inside = np.minimum(np.maximum(qx, qy), 0)
        return outside + inside - self.corner

    def contour(self, n):
        """n points evenly spaced in arc length on the boundary, with outward normals."""
        w, h, c = self.half_w - self.corner, self.half_h - self.corner, self.corner
        segs = []  # straight segments and arcs, counter-clockwise from +r side
        L_str = [2 * h, 2 * w, 2 * h, 2 * w]
        L_arc = np.pi * c / 2
        total = sum(L_str) + 4 * L_arc
        s = (np.arange(n) + 0.5) * total / n
        pts, nrm = [], []
        corners = [(w, h), (-w, h), (-w, -h), (w, -h)]
        for si in s:
            rem = si
            for k in range(4):
                if rem <= L_str[k]:
                    t = rem
                    if k == 0:
                        p, nv = (w + c, -h + t), (1, 0)
                    elif k == 1:
                        p, nv = (w - t, h + c), (0, 1)
                    elif k == 2:
                        p, nv = (-w - c, h - t), (-1, 0)
                    else:
                        p, nv = (-w + t, -h - c), (0, -1)
                    break
                rem -= L_str[k]
                if rem <= L_arc:
                    ang = (k * np.pi / 2) + rem / c if c > 0 else k * np.pi / 2
                    cx, cy = corners[k]
                    nv = (np.cos(ang), np.sin(ang))
                    p = (cx + c * nv[0], cy + c * nv[1])
                    break
                rem -= L_arc
            pts.append(p)
            nrm.append(nv)
        pts = np.array(pts) + [self.r_c, self.z_c]
        return pts, np.array(nrm, dtype=float), total / n


def ring_potential(qa, qz, r, z):
    """Potential per unit charge (1 C) of ring charges (radius qa, height qz) at points (r, z).

    Broadcasts: qa, qz shape (M,), r, z shape (N,) -> (N, M).
    """
    r = np.asarray(r)[:, None]
    z = np.asarray(z)[:, None]
    dz = z - qz[None, :]
    rho2 = (r + qa[None, :]) ** 2 + dz**2
    m = np.clip(4 * qa[None, :] * r / rho2, 0, 1 - 1e-15)
    return K_E * (2 / np.pi) * ellipk(m) / np.sqrt(rho2)


def ring_field(qa, qz, r, z):
    """Field (E_r, E_z) per unit charge of ring charges at points; each (N, M)."""
    r = np.asarray(r)[:, None]
    z = np.asarray(z)[:, None]
    a = qa[None, :]
    dz = z - qz[None, :]
    rho2 = (r + a) ** 2 + dz**2
    d2 = (a - r) ** 2 + dz**2
    m = np.clip(4 * a * r / rho2, 0, 1 - 1e-15)
    K, E = ellipk(m), ellipe(m)
    rho = np.sqrt(rho2)
    pref = K_E * (2 / np.pi)
    ez = pref * dz * E / (rho * d2)
    with np.errstate(divide="ignore", invalid="ignore"):
        er = pref / (2 * r * rho) * (K - (a**2 - r**2 + dz**2) / d2 * E)
    er = np.where(r < 1e-12, 0.0, er)
    return er, ez


@dataclass
class Solution:
    electrodes: list
    qa: np.ndarray
    qz: np.ndarray
    q: np.ndarray
    owner: np.ndarray
    residual: float = 0.0           # max |phi - V| on check points, V
    extras: dict = field(default_factory=dict)

    def potential(self, r, z):
        return ring_potential(self.qa, self.qz, np.ravel(r), np.ravel(z)) @ self.q

    def field(self, r, z):
        er, ez = ring_field(self.qa, self.qz, np.ravel(r), np.ravel(z))
        return er @ self.q, ez @ self.q

    def charge_on(self, i):
        return float(self.q[self.owner == i].sum())


def solve(electrodes, n_per=48):
    """Solve for ring charges that put every electrode at its potential."""
    qa, qz, cr, cz, cv, owner = [], [], [], [], [], []
    for i, el in enumerate(electrodes):
        pts, nrm, ds = el.contour(n_per)
        thick = min(el.half_w, el.half_h)
        off = min(1.5 * ds, 0.6 * thick)
        cp = pts - off * nrm
        cp[:, 0] = np.maximum(cp[:, 0], 1e-6)      # ring charges need radius > 0
        qa.append(cp[:, 0]); qz.append(cp[:, 1]); owner.append(np.full(n_per, i))
        # two collocation points per charge for a well-conditioned least-squares fit
        pts2, _, _ = el.contour(2 * n_per)
        cr.append(pts2[:, 0]); cz.append(pts2[:, 1]); cv.append(np.full(2 * n_per, el.potential))
    qa, qz, owner = map(np.concatenate, (qa, qz, owner))
    cr, cz, cv = map(np.concatenate, (cr, cz, cv))
    A = ring_potential(qa, qz, cr, cz)
    scale = np.abs(A).max()
    q, *_ = np.linalg.lstsq(A / scale, cv, rcond=None)
    q = q / scale
    sol = Solution(list(electrodes), qa, qz, q, owner)
    # independent check points midway between collocation points
    chk = [el.contour(3 * n_per + 1)[0] for el in electrodes]
    chk_v = np.concatenate([np.full(len(c), el.potential) for c, el in zip(chk, electrodes)])
    chk = np.vstack(chk)
    sol.residual = float(np.abs(sol.potential(chk[:, 0], chk[:, 1]) - chk_v).max())
    return sol


def surface_field(sol, i, n=96):
    """Normal field, positions and area weights on electrode i's surface."""
    el = sol.electrodes[i]
    pts, nrm, ds = el.contour(n)
    er, ez = sol.field(pts[:, 0], pts[:, 1])
    en = er * nrm[:, 0] + ez * nrm[:, 1]
    area = 2 * np.pi * pts[:, 0] * ds
    return pts, nrm, en, area


def trace_field_lines(sol, emitter_index, n_lines=64, r_max=0.3, z_span=(-0.3, 0.5),
                      max_steps=6000, ds_min=2e-6, ds_max=1.5e-3):
    """Trace ion paths (along +E) from an emitter until they hit an electrode or escape.

    Returns dict with per-line flux weight, end electrode index (-1 = escaped),
    axial displacement dz and path length. All lines are advanced together with
    a vectorised RK4 whose step scales with distance to the nearest electrode.
    """
    pts, nrm, en, area = surface_field(sol, emitter_index, n_lines)
    w = np.maximum(en, 0) * area
    el0 = sol.electrodes[emitter_index]
    p = pts + nrm * 0.02 * min(el0.half_w, el0.half_h)
    alive = w > 0
    end = np.full(len(p), -1)
    length = np.zeros(len(p))
    start = p.copy()
    others = [k for k in range(len(sol.electrodes))]

    def dist(pp):
        return np.min([sol.electrodes[k].sdf(pp[:, 0], pp[:, 1]) for k in others], axis=0)

    def direction(pp):
        er, ez = sol.field(np.abs(pp[:, 0]), pp[:, 1])
        mag = np.hypot(er, ez) + 1e-30
        return np.column_stack([er / mag, ez / mag])

    for _ in range(max_steps):
        idx = np.flatnonzero(alive)
        if idx.size == 0:
            break
        pp = p[idx]
        h = np.clip(0.25 * dist(pp), ds_min, ds_max)[:, None]
        k1 = direction(pp)
        k2 = direction(pp + 0.5 * h * k1)
        k3 = direction(pp + 0.5 * h * k2)
        k4 = direction(pp + h * k3)
        new = pp + h * (k1 + 2 * k2 + 2 * k3 + k4) / 6
        new[:, 0] = np.abs(new[:, 0])               # reflect through the axis
        length[idx] += h[:, 0]
        p[idx] = new
        for k in others:
            hit = sol.electrodes[k].sdf(new[:, 0], new[:, 1]) <= 0
            if k == emitter_index:
                hit &= length[idx] > 4 * min(el0.half_w, el0.half_h)
            sel = idx[hit & alive[idx]]
            end[sel] = k
            alive[sel] = False
        out = (new[:, 0] > r_max) | (new[:, 1] < z_span[0]) | (new[:, 1] > z_span[1])
        alive[idx[out]] = False
    dz = p[:, 1] - start[:, 1]
    return {"weight": w / w.sum(), "end": end, "dz": dz, "length": length,
            "start": start, "stop": p}
