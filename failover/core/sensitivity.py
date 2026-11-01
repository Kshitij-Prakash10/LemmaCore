"""Sensitivity of 'minutes left' to each assumed parameter, one at a time (plus or minus 20 percent).

It tells the team which assumptions to confirm with a mentor first. Output: outputs/sensitivity.json.
CLI: python -m failover.core.sensitivity --out outputs
"""

from __future__ import annotations

import argparse
import copy
import json
import os

from .config import ROOT, load_config
from .model import CAP_MIN, allocate, limit_times, plant_from_faults, resolve_params
from .simulate import simulate
from .types import Scenario

# (label, kind, key). kind "param" edits the resolved parameter, "limit" edits a config limit value.
PARAMS = [
    ("motor heat capacity (kJ/K)", "param", "C", "thermal.motor.capacity_kj_per_k"),
    ("cooling with blower on (kW/K)", "param", "h_on", "thermal.motor.h_on_kw_per_k"),
    ("cooling with blower off, ratio", "param", "h_off_ratio", "thermal.motor.h_off_ratio"),
    ("motor heat at full load (kW)", "param", "heat_full", "thermal.motor.heat_full_kw"),
    ("brake-air leak (bar/min)", "param", "leak", "air.leak_bar_per_min"),
    ("compressor fill rate (bar/min)", "param", "fill", "air.fill_bar_per_min"),
    ("battery usable fraction", "param", "usable_fraction", "battery.usable_fraction"),
    ("control current (A)", "param", "control_a", "battery.control_current_a"),
    ("motor trip temperature (C)", "limit", "motor_temp_trip_c", "limits.motor_temp_trip_c"),
    ("brake-air minimum (bar)", "limit", "brake_air_min_bar", "limits.brake_air_min_bar"),
]

CASES = [
    ("hot_climb_standby_stuck", ("STANDBY_STUCK",), 45.0, 2.7),
    ("cool_flat_compressor_fail", ("COMPRESSOR_FAIL",), 30.0, 0.0),
    ("hot_climb_blower_fail", ("BLOWER_FAIL",), 45.0, 2.7),
]


def _state_at_plan(cfg: dict, sc: Scenario) -> dict:
    r = simulate(sc, "advisor", cfg)
    k = int((cfg["defaults"]["fault_time_s"] + 10) / 1.0)
    first = next(e for e in r.events if e["type"] == "advice")
    plant = plant_from_faults(sc.faults, sc.units)
    alloc = allocate(cfg, sc.ambient_c, plant["states"], plant["failover_ok"], shed=set(first["shed"]))
    return {"plant": plant, "powered": alloc["powered"], "t_motor": r.true["motor_temp_c"][k],
            "p_air": r.true["air_pressure_bar"][k], "soc": r.true["battery_soc_pct"][k],
            "advice": first}


def _minutes(cfg: dict, p: dict, st: dict, sc: Scenario) -> tuple:
    t = limit_times(cfg, p, st["plant"], st["powered"], st["t_motor"], sc.ambient_c, True, sc.gradient_pct,
                    sc.train_load, st["p_air"], st["soc"])
    m = min(t, key=lambda k: t[k])
    return min(t[m], CAP_MIN), m


def run_sensitivity(config: dict | None = None, out_dir: str = "outputs", delta: float = 0.2) -> dict:
    cfg = config or load_config()
    out_cases = []
    for name, faults, amb, grad in CASES:
        sc = Scenario(id=name, faults=faults, ambient_c=amb, gradient_pct=grad,
                      dist_next_station_km=cfg["defaults"]["dist_next_station_km"], seed=1)
        st = _state_at_plan(cfg, sc)
        base_p = resolve_params(cfg)
        nominal, limiting = _minutes(cfg, base_p, st, sc)
        rows = []
        for label, kind, key, cfg_path in PARAMS:
            res = {}
            for tag, f in (("low", 1 - delta), ("high", 1 + delta)):
                if kind == "param":
                    p = dict(base_p)
                    p[key] = p[key] * f
                    res[tag] = _minutes(cfg, p, st, sc)[0]
                else:
                    c2 = copy.deepcopy(cfg)
                    c2["limits"][key]["value"] = c2["limits"][key]["value"] * f
                    res[tag] = _minutes(c2, base_p, st, sc)[0]
            status = "assumed"
            node = cfg
            for part in cfg_path.split("."):
                node = node.get(part, {}) if isinstance(node, dict) else {}
            if isinstance(node, dict) and node.get("status"):
                status = node["status"]
            else:
                parent = cfg_path.split(".")[0]
                status = cfg.get(parent, {}).get("status", "assumed") if isinstance(cfg.get(parent), dict) else "assumed"
            rows.append({"parameter": label, "config_path": cfg_path, "status": status,
                         "minutes_at_minus_20pct": round(res["low"], 2), "minutes_at_plus_20pct": round(res["high"], 2),
                         "swing_minutes": round(abs(res["high"] - res["low"]), 2)})
        rows.sort(key=lambda r: r["swing_minutes"], reverse=True)
        out_cases.append({"case": name, "faults": list(faults), "ambient_c": amb, "gradient_pct": grad,
                          "decision": st["advice"]["decision"], "nominal_minutes": round(nominal, 2),
                          "limiting_factor": limiting, "parameters": rows})
    data = {"delta": delta, "note": "one parameter at a time, minutes to the first limit with the advisor's load plan",
            "cases": out_cases}
    out = out_dir if os.path.isabs(out_dir) else os.path.join(ROOT, out_dir)
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "sensitivity.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1)
    return data


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="outputs")
    a = ap.parse_args()
    data = run_sensitivity(None, a.out)
    for c in data["cases"]:
        top = c["parameters"][0]
        print(f"{c['case']}: nominal {c['nominal_minutes']} min, limit {c['limiting_factor']}, "
              f"most sensitive: {top['parameter']} (swing {top['swing_minutes']} min)")


if __name__ == "__main__":
    main()
