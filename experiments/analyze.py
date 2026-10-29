"""Reduce a completed iv_thrust_sweep.csv to per-step means with GUM-style uncertainties.

Usage: python experiments/analyze.py path/to/iv_thrust_sweep.csv [--res-g 0.001] [--acc-v 0.01] [--acc-i 0.02]

Uncertainty components:
  balance: Type A (repeat scatter) + Type B resolution res/sqrt(12)
  voltage: Type B relative accuracy acc_v/sqrt(3)
  current: Type B relative accuracy acc_i/sqrt(3)
Expanded uncertainty U = 2 u_c is reported.
"""
import argparse
import sys

import numpy as np
import pandas as pd

G = 9.80665


def reduce(df, res_g=0.001, acc_v=0.01, acc_i=0.02):
    if df.empty:
        raise ValueError("No measurements in file: the template is empty. Nothing to analyze.")
    df = df.copy()
    df["dm_g"] = df.balance_reading_g - df.balance_zero_g          # exhaust up: the jet pushes the device down, so the reading rises
    rows = []
    for (cfg, step), g in df.groupby(["configuration_id", "step"]):
        n = len(g)
        V = g.measured_voltage_kV.mean() * 1e3
        I = g.supply_current_uA.mean() * 1e-6
        dm = g.dm_g.mean()
        uA_dm = g.dm_g.std(ddof=1) / np.sqrt(n) if n > 1 else 0.0
        u_dm = np.hypot(uA_dm, res_g / np.sqrt(12))
        T = G * dm * 1e-3
        u_T = G * u_dm * 1e-3
        P = V * I
        rel_P = np.hypot(acc_v / np.sqrt(3), acc_i / np.sqrt(3))
        TP = T / P if P > 0 else np.nan
        rel_TP = np.hypot(u_T / T, rel_P) if T > 0 else np.nan
        row = {"configuration_id": cfg, "step": step, "n_repeats": n, "V_kV": V / 1e3, "I_uA": I * 1e6,
               "thrust_mN": T * 1e3, "U_thrust_mN": 2 * u_T * 1e3, "P_W": P, "U_P_W": 2 * rel_P * P,
               "TP_mNW": TP * 1e3, "U_TP_mNW": 2 * rel_TP * TP * 1e3}
        cols = [c for c in ("collector1_current_uA", "collector2_current_uA", "collector3_current_uA") if c in g]
        cur = g[cols].mean()
        if len(cols) >= 2 and cur.notna().sum() >= 2:
            # back-flow of stage 2 = current arriving at collector 1 from emitter 2 cannot be separated from
            # emitter 1's own current without a second run; we report the raw split for later analysis.
            row.update({f"{c}_mean": cur[c] for c in cols})
        rows.append(row)
    return pd.DataFrame(rows)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("csv"); ap.add_argument("--res-g", type=float, default=0.001)
    ap.add_argument("--acc-v", type=float, default=0.01); ap.add_argument("--acc-i", type=float, default=0.02)
    a = ap.parse_args(argv)
    try:
        out = reduce(pd.read_csv(a.csv), a.res_g, a.acc_v, a.acc_i)
    except ValueError as e:
        print(e, file=sys.stderr)
        return 1
    print(out.round(4).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
