"""Time-stepping simulation of one scenario under one policy. Deterministic given the scenario seed."""

from __future__ import annotations

import numpy as np

from .advisor import advise
from .config import load_config
from .model import (allocate, derate_factor, heat_scale, limit_times, plant_from_faults, resolve_params,
                    unit_capacity_kw)
from .types import POLICIES, SIGNAL_NAMES, SimResult, Scenario
from .version import CORE_VERSION

# noise is a fraction of these ranges
_RANGE = {"motor_temp_c": 200.0, "converter_temp_c": 150.0, "air_pressure_bar": 10.0, "battery_v": 120.0,
          "dc_link_v": 1500.0, "battery_soc_pct": 100.0, "power_demand_kw": 100.0, "power_available_kw": 200.0,
          "unit1_load_kva": 130.0, "unit2_load_kva": 130.0, "unit3_load_kva": 130.0}
_NOISY = set(_RANGE)


def simulate(scenario: Scenario, policy: str, config: dict | None = None,
             horizon_s: int = 1800, dt_s: float = 1.0) -> SimResult:
    if policy not in POLICIES:
        raise ValueError(f"policy must be one of {POLICIES}")
    cfg = config or load_config()
    d = cfg["defaults"]
    fault_t = float(d["fault_time_s"])
    p = resolve_params(cfg, scenario.params, "nominal")
    rng = np.random.default_rng(scenario.seed)
    n, amb = scenario.units, scenario.ambient_c
    faults = tuple(scenario.faults)
    plant = plant_from_faults(faults, n)
    lim_t = cfg["limits"]["motor_temp_trip_c"]["value"]
    margin = cfg["limits"]["protection_derate_margin_c"]["value"]
    p_min = cfg["limits"]["brake_air_min_bar"]["value"]
    soc_min = cfg["limits"]["battery_min_soc_pct"]["value"]
    hs = heat_scale(cfg, scenario.gradient_pct, scenario.train_load)
    n_loads = len(cfg["loads"])
    conv = cfg["converters"]

    t_motor = amb + p["rise0"]
    p_air, soc = p["normal_bar"], 100.0
    pos, moving, reached, stopped = 0.0, True, False, False
    shed: set = set()
    stop_at = None
    last_advice_t = -1e9
    stuck_val = None
    limit_hit, t_limit = None, None
    minutes_true = None
    events = []

    true = {k: [] for k in SIGNAL_NAMES}
    obs = {k: [] for k in SIGNAL_NAMES}
    ts = []
    steps = int(horizon_s / dt_s)

    for k in range(steps + 1):
        t = k * dt_s
        faulted = t >= fault_t
        states = plant["states"] if faulted else [0] * n
        fo = plant["failover_ok"] if faulted else True
        if faulted and k > 0 and (k - 1) * dt_s < fault_t:
            events += [{"t_s": t, "type": "fault_injected", "fault": f} for f in faults]

        # advisor acts ten seconds after the fault, then re-checks each minute
        if policy == "advisor" and faulted and t >= fault_t + 10 and moving and t - last_advice_t >= 60:
            window = {name: obs[name][-60:] for name in SIGNAL_NAMES}
            ctx = {"ambient_c": amb, "gradient_pct": scenario.gradient_pct, "train_load": scenario.train_load,
                   "units": n, "dist_next_station_km": max(0.0, scenario.dist_next_station_km - pos),
                   "speed_kmph": scenario.speed_kmph, "moving": moving, "shed": sorted(shed)}
            adv = advise({"observed": window, "context": ctx}, cfg, fault_hypothesis=list(faults))
            shed, last_advice_t = set(adv.shed), t
            events.append({"t_s": t, "type": "advice", "decision": adv.decision, "shed": adv.shed,
                           "keep": adv.keep, "minutes_left_p5": adv.minutes_left_p5,
                           "limiting_factor": adv.limiting_factor, "flags": adv.flags})
            if adv.decision == "STOP_NOW":
                stop_at = pos + 0.3
            elif adv.decision == "STOP_AT_NEXT":
                stop_at = min(pos + 3.0, scenario.dist_next_station_km)
            else:
                stop_at = None

        alloc = allocate(cfg, amb, states, fo, shed)
        powered = alloc["powered"]
        blower_ok = "motor_blower" in powered and not (faulted and plant["blower_fail"])
        comp_ok = "brake_compressor" in powered and not (faulted and plant["comp_fail"])

        # minutes to the first limit at the moment the plan is set, for the record
        if minutes_true is None and faulted and t >= fault_t + 10:
            tl = limit_times(cfg, p, plant, powered, t_motor, amb, moving, scenario.gradient_pct,
                             scenario.train_load, p_air, soc)
            m = min(tl.values())
            minutes_true = None if m == float("inf") else round(m, 2)

        # movement
        if moving:
            pos += scenario.speed_kmph * dt_s / 3600.0
            if pos >= scenario.dist_next_station_km:
                moving, reached = False, True
                events.append({"t_s": t, "type": "reached_station"})
            elif stop_at is not None and pos >= stop_at:
                moving, stopped = False, True
                events.append({"t_s": t, "type": "stopped_by_policy"})

        # heat
        h = p["h_on"] * (1.0 if blower_ok else p["h_off_ratio"])
        q = p["heat_full"] * hs if moving else 0.0
        if t_motor >= lim_t - margin:
            q *= 0.5  # loco protection derates before the trip
        t_motor += dt_s * (q - h * (t_motor - amb)) / p["C"]

        # brake air
        if comp_ok and p_air < p["normal_bar"]:
            p_air += p["fill"] * dt_s / 60.0
        p_air = min(p["normal_bar"], max(0.0, p_air - p["leak"] * dt_s / 60.0))

        # battery
        if "control_and_charger" not in powered:
            soc = max(0.0, soc - p["control_a"] / (p["capacity_ah"] * p["usable_fraction"]) * dt_s / 3600.0 * 100.0)

        # limits count only while the train is still moving
        if limit_hit is None and moving:
            if t_motor >= lim_t:
                limit_hit, t_limit = "motor_temp", t
            elif p_air <= p_min:
                limit_hit, t_limit = "brake_air", t
            elif soc <= soc_min:
                limit_hit, t_limit = "battery", t
            if limit_hit:
                events.append({"t_s": t, "type": "limit_hit", "limit": limit_hit})

        # record true signals
        unit_kw = alloc["unit_kw"]
        row = {
            "unit1_state": states[0], "unit2_state": states[1] if n > 1 else 0, "unit3_state": states[2] if n > 2 else 0,
            "unit1_load_kva": unit_kw[0] / conv["power_factor"],
            "unit2_load_kva": (unit_kw[1] / conv["power_factor"]) if n > 1 else 0.0,
            "unit3_load_kva": (unit_kw[2] / conv["power_factor"]) if n > 2 else 0.0,
            "power_demand_kw": alloc["demand_kw"], "power_available_kw": alloc["available_kw"],
            "dc_link_v": 1000.0 * sum(1 for s in states if s < 2) / n,
            "blower_motor_pct": 100.0 if blower_ok else 0.0,
            "blower_oil_pct": 100.0 if "oil_cooling_blower" in powered else 0.0,
            "motor_temp_c": t_motor, "converter_temp_c": amb + 0.6 * (t_motor - amb),
            "air_pressure_bar": p_air, "battery_v": 110.0 * (0.9 + 0.1 * soc / 100.0), "battery_soc_pct": soc,
            "loads_on": float(len(powered)),
        }
        ob = {}
        for name, v in row.items():
            noise = scenario.noise * _RANGE.get(name, 0.0) * rng.standard_normal() if name in _NOISY else 0.0
            ob[name] = v + noise
        if plant["temp_stuck"] and faulted:
            if stuck_val is None:
                stuck_val = obs["motor_temp_c"][-1] if obs["motor_temp_c"] else ob["motor_temp_c"]
            ob["motor_temp_c"] = stuck_val
        for name in SIGNAL_NAMES:
            true[name].append(float(row[name]))
            obs[name].append(float(ob[name]))
        ts.append(t)

    if limit_hit:
        outcome = "UNSAFE"
    elif stopped:
        outcome = "CONTROLLED_STOP"
    else:
        outcome = "SAFE"
    return SimResult(scenario_id=scenario.id, policy=policy, core_version=CORE_VERSION, t_s=ts, true=true,
                     observed=obs, events=events, outcome=outcome, limit_hit=limit_hit, t_limit_s=t_limit,
                     reached_station=reached, minutes_left_true=minutes_true)
