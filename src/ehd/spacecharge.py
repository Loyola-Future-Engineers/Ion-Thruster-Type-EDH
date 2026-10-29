"""Self-consistent axisymmetric space-charge solver for unipolar (positive) corona drift.

Solves, in the drift region outside the thin ionisation layer,

    div(eps0 grad phi) = -rho                (Poisson)
    div(rho mu E)      = 0,  E = -grad phi   (steady charge conservation, no wind, no diffusion)

on a graded structured (r, z) grid with a node-centred finite-volume discretisation:
axisymmetric face areas 2 pi r dz (radial faces) and pi (r+^2 - r-^2) (axial faces).
Charge transport uses first-order upwinding, giving a sparse linear system in rho for a
given field. The two equations are coupled by under-relaxed fixed-point iteration.

Boundary conditions
  * Electrodes: Dirichlet phi (emitters V x stage scale, collectors 0). Outer box: phi = 0
    (a grounded laboratory far away), or zero-gradient on the z ends for the coax test.
  * Charge injection (Kaptsov's assumption, integral form): each emitter's injected
    density rho_e is adjusted until the charge on that emitter (eps0 times the outward
    field flux, by Gauss's law) equals its Laplacian charge at the corona-onset voltage.
    Equivalently, the emitter surface field is clamped at the onset field. Comparing
    charges computed on the same grid cancels most staircase error at the thin emitter.

Because transport is linear in rho for a fixed field, the converged density is split
exactly into contributions from each emitter. That gives per-emitter current to every
collector, which is how back-flow is measured.

Not included: ionisation-layer physics, ion diffusion, negative ions, wind convection of
ions, and the neutral flow field. Thrust is the volume integral of rho E_z.
"""
from dataclasses import dataclass

import numpy as np
import scipy.sparse as sp
from scipy.sparse.linalg import splu, spsolve

from .constants import EPS0, Air, STANDARD_AIR


def graded_axis(lo, hi, refine, h_max, growth=0.12):
    """1-D coordinates on [lo, hi]. Spacing grows linearly from each refine point (x_k, h_k)."""
    xs = [lo]
    x = lo
    while x < hi:
        h = min([h_max] + [hk + growth * abs(x - xk) for xk, hk in refine])
        x = x + h
        xs.append(min(x, hi))
    return np.unique(np.array(xs))


@dataclass
class Grid:
    r: np.ndarray
    z: np.ndarray

    def __post_init__(self):
        r, z = self.r, self.z
        self.nr, self.nz = len(r), len(z)
        rf = np.concatenate([[0.0], 0.5 * (r[1:] + r[:-1]), [r[-1]]])
        zf = np.concatenate([[z[0]], 0.5 * (z[1:] + z[:-1]), [z[-1]]])
        self.rf, self.zf = rf, zf
        dz = zf[1:] - zf[:-1]
        ring = np.pi * (rf[1:] ** 2 - rf[:-1] ** 2)
        self.vol = np.outer(ring, dz)                        # (nr, nz)
        # conductances a = face area / node distance
        self.ar = (2 * np.pi * rf[1:-1, None] * dz[None, :]) / (r[1:] - r[:-1])[:, None]   # (nr-1, nz)
        self.az = ring[:, None] / (z[1:] - z[:-1])[None, :]                                  # (nr, nz-1)
        self.R, self.Z = np.meshgrid(r, z, indexing="ij")

    def k(self, i, j):
        return i * self.nz + j

    def edges(self):
        """All neighbour pairs (k1, k2) with conductance a, k2 = +r or +z neighbour."""
        nr, nz = self.nr, self.nz
        I, J = np.meshgrid(np.arange(nr - 1), np.arange(nz), indexing="ij")
        k1r, k2r, ar = (I * nz + J).ravel(), ((I + 1) * nz + J).ravel(), self.ar.ravel()
        I, J = np.meshgrid(np.arange(nr), np.arange(nz - 1), indexing="ij")
        k1z, k2z, az = (I * nz + J).ravel(), (I * nz + J + 1).ravel(), self.az.ravel()
        return np.concatenate([k1r, k1z]), np.concatenate([k2r, k2z]), np.concatenate([ar, az])


class SpaceChargeSolver:
    """Coupled Poisson / drift solver on a grid with electrodes given as signed-distance bodies."""

    def __init__(self, grid: Grid, electrodes, air: Air = STANDARD_AIR, neumann_z=False, blocked=None):
        """blocked: optional boolean (nr, nz) mask of nodes inside an insulating body. Edges into
        it are removed, which imposes zero normal field and zero ion flux on its surface (the
        steady state of a fully charged-up dielectric wall)."""
        self.g, self.els, self.air = grid, electrodes, air
        g = grid
        N = g.nr * g.nz
        tag = np.full(N, -1)                                  # -1 gas, else electrode index
        for idx, el in enumerate(electrodes):
            inside = (el.sdf(g.R, g.Z) <= 0).ravel()
            tag[inside & (tag < 0)] = idx
        self.tag = tag
        outer = np.zeros((g.nr, g.nz), bool)
        outer[-1, :] = True
        if not neumann_z:
            outer[:, 0] = outer[:, -1] = True
        self.outer = outer.ravel() & (tag < 0)
        self.dirichlet = (tag >= 0) | self.outer
        self.k1, self.k2, self.a = g.edges()
        self.blocked = np.zeros(N, bool) if blocked is None else blocked.ravel() & (tag < 0)
        keep = ~(self.blocked[self.k1] | self.blocked[self.k2])
        self.k1, self.k2, self.a = self.k1[keep], self.k2[keep], self.a[keep]
        self.outer &= ~self.blocked
        self.dirichlet = (tag >= 0) | self.outer | self.blocked
        # Poisson matrix: rows of Dirichlet nodes are identity
        d = self.dirichlet
        rows, cols, vals = [], [], []
        for p, q in ((self.k1, self.k2), (self.k2, self.k1)):
            m = ~d[p]
            rows += [p[m], p[m]]; cols += [q[m], p[m]]; vals += [self.a[m], -self.a[m]]
        rows.append(np.flatnonzero(d)); cols.append(np.flatnonzero(d)); vals.append(np.ones(d.sum()))
        A = sp.csc_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(N, N))
        self.lu = splu(A)
        self.N = N
        self.emitters = [i for i, el in enumerate(electrodes) if el.kind == "emitter"]
        self.vol = g.vol.ravel()

    # ------------------------------------------------------------------ field
    def potential(self, voltages, rho):
        b = -rho * self.vol / EPS0
        b[self.dirichlet] = 0.0
        for idx, v in voltages.items():
            b[self.tag == idx] = v
        return self.lu.solve(b)

    def electrode_charge(self, phi, idx):
        """eps0 x outward field flux from electrode idx into gas (Gauss): its surface charge."""
        k1, k2, a = self.k1, self.k2, self.a
        q = 0.0
        for p, s in ((k1, k2), (k2, k1)):
            m = (self.tag[p] == idx) & (self.tag[s] != idx)
            q += np.sum(EPS0 * a[m] * (phi[p[m]] - phi[s[m]]))
        return q

    # ------------------------------------------------------------------ transport
    def transport(self, phi, sources):
        """Steady upwind drift. sources: {emitter_idx: rho_e}. Returns rho (N,) incl. source nodes."""
        mu = self.air.mobility
        k1, k2, a = self.k1, self.k2, self.a
        flow = mu * a * (phi[k1] - phi[k2])                  # >0: charge moves k1 -> k2 (per unit rho)
        up = np.where(flow > 0, k1, k2)
        dn = np.where(flow > 0, k2, k1)
        f = np.abs(flow)
        fixed = (self.tag >= 0) | self.outer | self.blocked   # rho prescribed (sources) or absorbing (0)
        rho_fixed = np.zeros(self.N)
        for idx, val in sources.items():
            rho_fixed[self.tag == idx] = val
        # unknown gas nodes: rho_k * sum(out) - sum(in from upwind gas nodes) = sum(in from fixed sources)
        out_sum = np.bincount(up, weights=f, minlength=self.N)
        gas = ~fixed
        m_in = gas[dn] & gas[up]
        rows = np.concatenate([np.flatnonzero(gas), dn[m_in]])
        cols = np.concatenate([np.flatnonzero(gas), up[m_in]])
        vals = np.concatenate([out_sum[gas] + 1e-30 + 1e-12 * out_sum.max(), -f[m_in]])
        m_src = gas[dn] & ~gas[up]
        b = np.bincount(dn[m_src], weights=f[m_src] * rho_fixed[up[m_src]], minlength=self.N)
        gi = np.flatnonzero(gas)
        pos = np.full(self.N, -1); pos[gi] = np.arange(len(gi))
        M = sp.csr_matrix((vals, (pos[rows], pos[cols])), shape=(len(gi), len(gi)))
        rho = rho_fixed.copy()
        rho[gi] = spsolve(M.tocsc(), b[gi])
        return rho, (up, dn, f)

    def currents(self, rho, flows):
        """Current leaving each emitter and arriving at each electrode/boundary (A)."""
        up, dn, f = flows
        I = f * rho[up]
        src_tag, dst_tag = self.tag[up], self.tag[dn]
        out = {}
        for idx in range(len(self.els)):
            out[("emit", idx)] = float(I[(src_tag == idx) & (dst_tag != idx)].sum())
            out[("recv", idx)] = float(I[(dst_tag == idx) & (src_tag != idx)].sum())
        out[("recv", "outer")] = float(I[self.outer[dn] & ~self.outer[up]].sum())
        return out

    def body_force_z(self, phi, rho):
        P = phi.reshape(self.g.nr, self.g.nz)
        Ez = -np.gradient(P, self.g.z, axis=1).ravel()
        gas = (self.tag < 0) & ~self.blocked
        return float(np.sum((rho * Ez * self.vol)[gas]))

    # ------------------------------------------------------------------ coupled solve
    def solve(self, voltages, onset, rho_e0=None, relax=0.3, tol=1e-3, max_iter=300, verbose=False):
        """voltages: {electrode_idx: V} for every electrode; onset: {emitter_idx: device-level V0 in volts
        at which that emitter starts corona, expressed in that emitter's own potential}.
        """
        # Laplacian charge per volt of each emitter with all emitters at their own potential pattern
        phi_L = self.potential(voltages, np.zeros(self.N))
        q_target = {}
        for i in onset:
            q_at_V = self.electrode_charge(phi_L, i)
            q_target[i] = q_at_V * onset[i] / voltages[i] if voltages[i] > onset[i] else None
        active = [i for i in onset if q_target[i] is not None]
        rho_e = {i: (rho_e0 or 1e-4) for i in active}
        rho = np.zeros(self.N)
        hist = []
        for it in range(max_iter):
            phi = self.potential(voltages, rho)
            # Kaptsov update of injection densities
            err = 0.0
            for i in active:
                q = self.electrode_charge(phi, i)
                ratio = q / q_target[i]
                rho_e[i] *= 0.5 if ratio <= 0 else float(np.clip(ratio, 0.5, 2.0)) ** 1.5
                err = max(err, abs(ratio - 1))
            rho_new, flows = self.transport(phi, rho_e)
            change = np.linalg.norm(rho_new - rho) / max(np.linalg.norm(rho_new), 1e-30)
            rho = relax * rho_new + (1 - relax) * rho
            err = max(err, change)
            hist.append(err)
            if verbose and it % 10 == 0:
                print(it, err, rho_e)
            if err < tol and it > 5:
                break
        phi = self.potential(voltages, rho)
        rho, flows = self.transport(phi, rho_e)
        # exact per-emitter decomposition (transport is linear in the sources for fixed phi)
        parts = {i: self.transport(phi, {i: rho_e[i]})[0] for i in active}
        return {"phi": phi, "rho": rho, "flows": flows, "rho_e": rho_e, "iterations": it + 1,
                "kaptsov_error": hist[-1] if hist else 0.0, "history": hist, "parts": parts,
                "currents": self.currents(rho, flows),
                "per_emitter": {i: self.currents(parts[i], flows) for i in active},
                "force_z": self.body_force_z(phi, rho),
                "force_z_per_emitter": {i: self.body_force_z(phi, parts[i]) for i in active}}


def coax_reference(V, wire_r, outer_R, E_on, air: Air = STANDARD_AIR):
    """Exact 1-D coaxial unipolar space-charge solution with Kaptsov's condition E(wire) = E_on.

    Gauss: d(rE)/dr = r rho / eps0. Continuity: I/L = 2 pi r rho mu E = 2 pi mu J, so
    d(rE)/dr = J / (eps0 E). Shoot on J until the integral of E equals V. Returns I/L in A/m.
    """
    from scipy.integrate import solve_ivp
    from scipy.optimize import brentq

    def volts(J):
        sol = solve_ivp(lambda r, y: [J / (EPS0 * (y[0] / r))], (wire_r, outer_R), [wire_r * E_on],
                        rtol=1e-10, atol=1e-14, dense_output=True)
        rr = np.geomspace(wire_r, outer_R, 6000)
        return np.trapezoid(sol.sol(rr)[0] / rr, rr)

    if V <= E_on * wire_r * np.log(outer_R / wire_r):
        return 0.0
    J = brentq(lambda J: volts(J) - V, 1e-12, 1e4, xtol=1e-15, rtol=1e-10)
    return 2 * np.pi * air.mobility * J


def device_solver(dev, air: Air = STANDARD_AIR, h_max=1.5e-3, h_far=8e-3, growth=0.1, box=0.25, emit_cells=5,
                  housing=None, wall=3e-3, overhang=0.010):
    """Build a graded grid and solver for a device.Device (axisymmetric ring electrodes).

    housing: None (open rings in a large grounded box), "insulating" (charged-up dielectric bore
    wall: zero-flux), or "grounded" (metal bore wall at 0 V, an extra collector).
    """
    from . import csm
    from .device import build_electrodes
    els = build_electrodes(dev, 1.0)
    z0 = min(el.z_c - el.half_h for el in els) - overhang
    z1 = max(el.z_c + el.half_h for el in els) + overhang
    Rb = dev.duct_radius
    rr, zr = [(0.0, h_max / 3), (Rb, h_max / 3), (Rb + wall, h_max / 3)], [(z0, h_max / 3), (z1, h_max / 3)]
    for el in els:
        h = (min(el.half_w, el.half_h) / emit_cells) if el.kind == "emitter" else min(el.half_w, el.half_h) / 3
        rr += [(el.r_c - el.half_w, h), (el.r_c + el.half_w, h), (el.r_c, h)]
        zr += [(el.z_c - el.half_h, h), (el.z_c + el.half_h, h), (el.z_c, h)]
    def axis(lo, hi, ref):
        x = graded_axis(lo, hi, ref, h_far, growth)
        return x
    grid = Grid(axis(0.0, Rb + wall + box, rr), axis(z0 - box, z1 + box, zr))
    blocked = None
    if housing == "grounded":
        els = els + [csm.Electrode("wall", Rb + wall / 2, (z0 + z1) / 2, wall / 2, (z1 - z0) / 2, 0.0, 0.0,
                                   "collector", 0)]
    elif housing == "insulating":
        blocked = (grid.R >= Rb) & (grid.R <= Rb + wall) & (grid.Z >= z0) & (grid.Z <= z1)
    elif housing is not None:
        raise ValueError(housing)
    return SpaceChargeSolver(grid, els, air, blocked=blocked), els


def run_device(dev, voltage, onset_device, air: Air = STANDARD_AIR, **kw):
    """Space-charge solution of a device at device voltage V. onset_device: per-stage onset (device volts)."""
    solver, els = device_solver(dev, air, **kw)
    volts = {}
    onset = {}
    for i, el in enumerate(els):
        st = dev.stages[el.stage - 1] if el.stage > 0 else None
        volts[i] = voltage * st.voltage_scale if el.kind == "emitter" else 0.0
        if el.kind == "emitter":
            onset[i] = onset_device[el.stage - 1] * st.voltage_scale
    res = solver.solve(volts, onset)
    res["solver"], res["electrodes"] = solver, els
    return res
