"""Plant model helpers shared by the simulator and the advisor.

Units: seconds, C, bar, kW, kVA, percent. Heat model: C dT/dt = Q - h (T - T_amb), with C in kJ/K,
h in kW/K and Q in kW, so the time constant C/h is in seconds.
"""

from __future__ import annotations

import json
import math
import os

from .config import ROOT

CAP_MIN = 120.0  # minutes; "no limit within two hours" is reported as this value


def derate_factor(cfg: dict, ambient_c: float) -> float:
    """Capacity factor of a healthy unit in heat: 1.0 up to the start ambient, falling linearly to factor_at_48c."""
    d = cfg["converters"]["derate"]
    start, f48 = d["start_ambient_c"], d["factor_at_48c"]
    if ambient_c <= start:
        return 1.0
    frac = min(1.0, (ambient_c - start) / (48.0 - start))
    return 1.0 - frac * (1.0 - f48)


def unit_capacity_kw(cfg: dict, ambient_c: float, state: int) -> float:
    """Real power a unit can supply. state: 0 healthy, 1 derated by a fault, 2 tripped."""
    if state >= 2:
        return 0.0
    c = cfg["converters"]
    cap = c["unit_kva"] * c["power_factor"] * derate_factor(cfg, ambient_c)
    if state == 1:
        cap *= c["unit_derate_fault_factor"]
    return cap


def plant_from_faults(faults, n_units: int) -> dict:
    """Translate fault ids into plant flags (see CONTRACT.md for the meaning of each fault)."""
    f = set(faults)
    states = [0] * n_units
    if f & {"U1_TRIP", "STANDBY_STUCK", "MCB_TRIP"}:
        states[0] = 2
    if "U2_TRIP" in f and n_units > 1:
        states[1] = 2
    if "UNIT_DERATE" in f and n_units > 1 and states[1] == 0:
        states[1] = 1
    return {
        "states": states,
        "failover_ok": not (f & {"STANDBY_STUCK", "MCB_TRIP"}),
        "blower_fail": "BLOWER_FAIL" in f,
        "comp_fail": "COMPRESSOR_FAIL" in f,
        "temp_stuck": "TEMP_SENSOR_STUCK" in f,
    }


def allocate(cfg: dict, ambient_c: float, states: list, failover_ok: bool, shed=()) -> dict:
    """Place loads on units in config order: home unit first, then another healthy unit if failover works.

    Home unit of load i is i modulo the unit count. Loads in `shed` are switched off by the crew.
    """
    all_loads = cfg["loads"]
    n = len(states)
    caps = [unit_capacity_kw(cfg, ambient_c, s) for s in states]
    used = [0.0] * n
    powered, dark = set(), []
    for idx, load in enumerate(all_loads):
        if load["name"] in shed:
            continue
        home, kw, placed = idx % n, load["kw"], False
        if states[home] < 2 and used[home] + kw <= caps[home] + 1e-9:
            used[home] += kw
            placed = True
        elif failover_ok:
            for u in sorted(range(n), key=lambda u: caps[u] - used[u], reverse=True):
                if u != home and states[u] < 2 and used[u] + kw <= caps[u] + 1e-9:
                    used[u] += kw
                    placed = True
                    break
        (powered.add(load["name"]) if placed else dark.append(load["name"]))
    demand = sum(l["kw"] for l in all_loads if l["name"] not in shed)
    return {"powered": powered, "dark": dark, "unit_kw": used,
            "available_kw": sum(caps), "demand_kw": demand}


def heat_scale(cfg: dict, gradient_pct: float, train_load: str) -> float:
    key = ("climb" if gradient_pct >= 1.0 else "flat") + "_" + train_load
    return cfg["thermal"]["motor"]["heat_scale"][key]


def _pick(spec, mode, rng):
    if isinstance(spec, dict) and "nominal" in spec:
        if mode == "sample":
            return float(rng.uniform(spec["min"], spec["max"]))
        if mode in ("min", "max"):
            return float(spec[mode])
        return float(spec["nominal"])
    return float(spec)


def resolve_params(cfg: dict, overrides: dict | None = None, mode: str = "nominal", rng=None) -> dict:
    """Flat numeric parameters. mode: 'nominal', 'min', 'max' or 'sample' (uniform within min and max)."""
    m, air, bat = cfg["thermal"]["motor"], cfg["air"], cfg["battery"]
    leak_spec = air["leak_bar_per_min"]
    if air.get("use_fitted"):
        fit = os.path.join(ROOT, "data", "processed", "air_params_fit.json")
        if os.path.exists(fit):
            with open(fit, encoding="utf-8") as f:
                leak_spec = json.load(f)["leak_bar_per_min"]
    p = {
        "C": _pick(m["capacity_kj_per_k"], mode, rng),
        "h_on": _pick(m["h_on_kw_per_k"], mode, rng),
        "h_off_ratio": _pick(m["h_off_ratio"], mode, rng),
        "heat_full": _pick(m["heat_full_kw"], mode, rng),
        "rise0": float(m["initial_rise_above_ambient_c"]),
        "leak": _pick(leak_spec, mode, rng),
        "fill": float(air["fill_bar_per_min"]),
        "normal_bar": float(air["normal_bar"]),
        "usable_fraction": _pick(bat["usable_fraction"], mode, rng),
        "control_a": _pick(bat["control_current_a"], mode, rng),
        "capacity_ah": float(bat["capacity_ah"]),
    }
    if overrides:
        p.update({k: float(v) for k, v in overrides.items() if k in p})
    return p


def motor_time_to_limit_min(t0: float, amb: float, q: float, h: float, c: float, limit: float) -> float:
    """Closed-form minutes until T reaches `limit`, for constant heat q (kW) and cooling h (kW/K)."""
    if t0 >= limit:
        return 0.0
    t_ss = amb + q / h
    if t_ss <= limit:
        return math.inf
    tau = c / h
    return (-tau * math.log((limit - t_ss) / (t0 - t_ss))) / 60.0


def air_time_to_limit_min(p0: float, p_min: float, leak: float, comp_on: bool, fill: float) -> float:
    if comp_on and fill > leak:
        return math.inf
    if p0 <= p_min:
        return 0.0
    net = leak - (fill if comp_on else 0.0)
    return (p0 - p_min) / net


def battery_time_min(soc_pct: float, soc_min: float, control_on: bool, p: dict) -> float:
    if control_on:
        return math.inf
    avail_ah = p["capacity_ah"] * p["usable_fraction"] * max(0.0, soc_pct - soc_min) / 100.0
    return avail_ah / p["control_a"] * 60.0


def limit_times(cfg: dict, p: dict, plant: dict, powered: set, t_motor: float, amb: float,
                moving: bool, gradient_pct: float, train_load: str, p_air: float, soc: float) -> dict:
    """Minutes until each limit under the given load plan (math.inf if the limit is never reached)."""
    lim = cfg["limits"]
    blower_on = "motor_blower" in powered and not plant["blower_fail"]
    h = p["h_on"] * (1.0 if blower_on else p["h_off_ratio"])
    q = p["heat_full"] * heat_scale(cfg, gradient_pct, train_load) if moving else 0.0
    comp_on = "brake_compressor" in powered and not plant["comp_fail"]
    return {
        "heat": motor_time_to_limit_min(t_motor, amb, q, h, p["C"], lim["motor_temp_trip_c"]["value"]),
        "air": air_time_to_limit_min(p_air, lim["brake_air_min_bar"]["value"] + lim["emergency_reserve_bar"]["value"],
                                     p["leak"], comp_on, p["fill"]),
        "battery": battery_time_min(soc, lim["battery_min_soc_pct"]["value"], "control_and_charger" in powered, p),
    }
