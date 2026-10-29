"""Helpers that turn a Device into a flat row of metrics for parameter studies."""
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from . import device as D
from . import reference as ref
from .constants import STANDARD_AIR


def _metrics(prefix, r):
    if r is None:
        return {f"{prefix}{k}": np.nan for k in ("V_kV", "I_uA", "P_W", "thrust_mN", "u_ms",
                                                    "Q_m3s", "Q_cfm", "TP_mNW")}
    return {f"{prefix}V_kV": r["V"] / 1e3, f"{prefix}I_uA": r["I"] * 1e6, f"{prefix}P_W": r["P"],
            f"{prefix}thrust_mN": r["thrust"] * 1e3, f"{prefix}u_ms": r["u"],
            f"{prefix}Q_m3s": r["Q"], f"{prefix}Q_cfm": r["Q"] * 2118.88,
            f"{prefix}TP_mNW": r["T_per_P"] * 1e3}


def run(dev, air=STANDARD_AIR, p_target=ref.P_COMPARE, n_lines=48, k_scale=1.0, label=None):
    geo = D.analyse_geometry(dev, air, n_lines=n_lines)
    v_sp = D.spark_limits(dev, air)
    v_op = min(ref.V_SUPPLY_MAX, ref.SPARK_MARGIN * v_sp)
    row = {"label": label, "n_stages": len(dev.stages),
           "gaps_mm": "/".join(f"{s.gap*1e3:.1f}" for s in dev.stages),
           "spacings_mm": "/".join(f"{s*1e3:.1f}" for s in dev.spacing),
           "length_mm": dev.length() * 1e3, "V_onset_kV": geo.onset.max() / 1e3,
           "V_spark_kV": v_sp / 1e3, "csm_residual_V_per_V": geo.residual, "K_loss": D.loss_coefficient(dev)}
    op = D.evaluate(geo, v_op, air, k_scale) if v_op > geo.onset.min() else None
    row.update(_metrics("op_", op))
    row["op_margin"] = 1 - v_op / v_sp
    if op:
        for k, st in enumerate(op["stages"]):
            sp = D.stage_current_split(geo, k)
            row[f"s{k+1}_I_uA"] = st["I"] * 1e6
            row[f"s{k+1}_T_mN"] = st["T_ehd"] * 1e3
            row[f"s{k+1}_backflow"] = sp["upstream"]
            row[f"s{k+1}_escaped"] = sp["escaped"]
    v_eq = D.voltage_for_power(geo, p_target, air, v_cap=min(ref.V_SUPPLY_MAX, ref.SPARK_MARGIN * v_sp), k_scale=k_scale)
    eq = D.evaluate(geo, v_eq, air, k_scale) if v_eq else None
    row.update(_metrics("eqP_", eq))
    row["eqP_margin"] = (1 - v_eq / v_sp) if v_eq else np.nan
    return row


def _run_star(args):
    dev, kw = args
    return run(dev, **kw)


def run_many(devs, workers=6, **kw):
    with ProcessPoolExecutor(workers) as ex:
        return list(ex.map(_run_star, [(d, kw) for d in devs]))
