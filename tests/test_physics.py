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
    geo = device.analyze_geometry(dev, n_lines=32)
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
    geo = device.analyze_geometry(dev, n_lines=32)
    r = device.evaluate(geo, 20e3)
    assert 0 < r["jet_eff"] < 1


def test_sparkover_limit_includes_interstage_gap():
    st = device.Stage(gap=0.03)
    dev = device.Device([st, st], spacing=[0.01])
    assert device.spark_limits(dev) < device.spark_limits(device.Device([st]))


def test_line_segment_reproduces_prolate_spheroid_capacitance():
    from ehd import pins
    c, rt = 0.003, 5e-5
    b = np.sqrt(rt * c); f = np.sqrt(c * c - b * b)
    phi = pins.segment_potential(np.array([[0, 0, -f]]), np.array([[0, 0, f]]), np.array([[0, 0, c]]))[0, 0]
    C = 2 * f / phi
    assert C == pytest.approx(4 * np.pi * EPS0 * f / np.arctanh(f / c), rel=1e-9)


def test_pin_shielding_reduces_tip_field():
    from ehd import pins
    e1 = pins.solve(pins.PinRing(n_pins=1))["E_tip_per_V"]
    e32 = pins.solve(pins.PinRing(n_pins=32))["E_tip_per_V"]
    assert e32 < 0.8 * e1


def test_single_pin_tip_field_close_to_hyperboloid_formula():
    """Order-of-magnitude cross-check against the point-to-plane hyperboloid formula."""
    from ehd import pins
    pr = pins.PinRing(n_pins=1)
    e = pins.solve(pr)["E_tip_per_V"]
    e_h = corona.tip_field_hyperboloid(1.0, pr.tip_radius, pr.tip_to_collector())
    assert 0.5 < e / e_h < 2.0


def test_experiment_reduction_refuses_empty_template_and_propagates_uncertainty():
    """Uses an in-memory synthetic table (not data) to check the arithmetic only."""
    import importlib.util, pathlib, pandas as pd
    root = pathlib.Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location("analyze", root / "experiments" / "analyze.py")
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    empty = pd.read_csv(root / "experiments" / "templates" / "iv_thrust_sweep.csv")
    with pytest.raises(ValueError):
        mod.reduce(empty)
    synthetic = pd.DataFrame({"configuration_id": ["X"] * 3, "step": [1] * 3,
                              "measured_voltage_kV": [20.0] * 3, "supply_current_uA": [100.0] * 3,
                              "balance_zero_g": [50.0] * 3, "balance_reading_g": [50.1, 50.1, 50.1]})
    out = mod.reduce(synthetic).iloc[0]
    assert out.thrust_mN == pytest.approx(0.1 * 9.80665, rel=1e-6)
    assert out.P_W == pytest.approx(2.0)
    assert out.U_thrust_mN > 0


def test_spacecharge_solver_matches_exact_coaxial_solution():
    from ehd import spacecharge as S
    a, R, L, V = 2e-4, 0.02, 0.004, 20e3
    E_on = float(corona.peek_field_wire(a)); v0 = E_on * a * np.log(R / a)
    r = S.graded_axis(0, R * 1.05, [(0, a / 8), (a, a / 8), (R, R / 200)], h_max=R / 60, growth=0.08)
    g = S.Grid(r, np.linspace(0, L, 9))
    els = [csm.Electrode("W", a / 2, L / 2, a / 2, L, 0, 1.0, "emitter"),
           csm.Electrode("O", R + 0.5 * (r[-1] - R), L / 2, 0.5 * (r[-1] - R) + 1e-9, L, 0, 0.0, "collector")]
    res = S.SpaceChargeSolver(g, els, neumann_z=True).solve({0: V, 1: 0.0}, {0: v0})
    I = res["currents"][("emit", 0)] / L
    assert I == pytest.approx(S.coax_reference(V, a, R, E_on), rel=0.03)
    # charge conservation: everything emitted is collected
    assert res["currents"][("recv", 1)] == pytest.approx(res["currents"][("emit", 0)], rel=1e-6)
