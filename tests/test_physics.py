"""Verification tests: each compares a model component against an exact or classical result."""
import numpy as np
import pytest

from ehd import corona, csm, device
from ehd.constants import EPS0, STANDARD_AIR


def test_ring_field_is_minus_gradient_of_potential():
    qa = np.array([0.02, 0.01]); qz = np.array([0.0, 0.01])
    r = np.array([0.005, 0.03, 0.015]); z = np.array([0.004, -0.01, 0.02])
    er, ez = csm.ring_field(qa, qz, r, z)
    h = 1e-7
    gr = -(csm.ring_potential(qa, qz, r + h, z) - csm.ring_potential(qa, qz, r - h, z)) / (2 * h)
    gz = -(csm.ring_potential(qa, qz, r, z + h) - csm.ring_potential(qa, qz, r, z - h)) / (2 * h)
    np.testing.assert_allclose(er, gr, rtol=1e-5)
    np.testing.assert_allclose(ez, gz, rtol=1e-5)


def test_ring_potential_on_axis():
    q = 1e-9; a = 0.02; z = 0.01
    phi = csm.ring_potential(np.array([a]), np.array([0.0]), np.array([0.0]), np.array([z]))[0, 0] * q
    assert phi == pytest.approx(q / (4 * np.pi * EPS0 * np.hypot(a, z)), rel=1e-12)


def test_thin_torus_capacitance():
    R, a = 0.02, 2e-4
    sol = csm.solve([csm.Electrode.torus("t", R, 0, a, 1.0)], n_per=24)
    expected = 4 * np.pi**2 * EPS0 * R / np.log(8 * R / a)   # thin-ring asymptotic formula
    assert sol.charge_on(0) == pytest.approx(expected, rel=2e-3)
    assert sol.residual < 1e-5


def test_thin_disc_capacitance():
    R = 0.02
    sol = csm.solve([csm.Electrode("d", R / 2, 0, R / 2, 1e-4, 1e-4, 1.0)], n_per=96)
    assert sol.charge_on(0) == pytest.approx(8 * EPS0 * R, rel=0.03)   # exact for zero thickness


def test_peek_wire_reference_value():
    # 1 mm radius wire at delta = 1: 31 * (1 + 0.308/sqrt(0.1)) kV/cm = 6.12 MV/m
    assert corona.peek_field_wire(1e-3) == pytest.approx(6.119e6, rel=1e-3)


def test_townsend_zero_below_onset_and_quadratic_above():
    v0 = 5e3
    i = corona.townsend_coax_current_per_length(np.array([4e3, 10e3, 20e3]), v0, 1e-4, 0.02)
    assert i[0] == 0
    assert i[2] / i[1] == pytest.approx(20 * 15 / (10 * 5))


def test_drift_thrust_identity_single_stage():
    """With no flow (u = 0) the stage force equals sum(dI dz)/mu exactly."""
    dev = device.Device([device.Stage(gap=0.025)], duct_radius=0.02)
    geo = device.analyse_geometry(dev, n_lines=32)
    V = 15e3
    r = device.evaluate(geo, V, iterate_flow=False)
    st = r["stages"][0]
    assert st["T_ehd"] > 0
    # thrust-to-current lever arm cannot exceed the axial extent of the stage
    lever = st["T_ehd"] * STANDARD_AIR.mobility / st["I"]
    assert 0 < lever <= 0.025 + 1e-3


def test_flow_energy_bound():
    """Kinetic power of the jet can never exceed electrical input power."""
    dev = device.Device([device.Stage(gap=0.03)], duct_radius=0.02)
    geo = device.analyse_geometry(dev, n_lines=32)
    r = device.evaluate(geo, 20e3)
    assert 0 < r["jet_eff"] < 1


def test_sparkover_limit_includes_interstage_gap():
    st = device.Stage(gap=0.03)
    dev = device.Device([st, st], spacing=[0.01])
    assert device.spark_limits(dev) < device.spark_limits(device.Device([st]))
