"""The advisor: which loads to switch off, how many minutes are left, continue or stop.

Physics-first. It tries every subset of loads, keeps those the converters can feed, and picks the plan with the
most minutes before the first limit (heat, brake air or battery). The 5th percentile over the parameter ranges
is reported as the minutes left, so the number is cautious.
"""

from __future__ import annotations

import numpy as np

from .config import assumed_blocks, load_config
from .model import (CAP_MIN, allocate, heat_scale, limit_times, plant_from_faults, resolve_params)
from .types import Advice

SAFE_PLACE_KM = 3.0  # assumed distance to the nearest place where the train can be stopped safely


def _last(obs: dict, name: str, default: float) -> float:
    series = obs.get(name)
    return float(series[-1]) if series else float(default)


def infer_faults(cfg: dict, obs: dict, ctx: dict) -> list:
    """Rough fault inference from observed signals. The ML diagnosis (failover.ml) is the better source."""
    n = int(ctx["units"])
    f = set()
    st = [_last(obs, f"unit{i + 1}_state", 0) for i in range(n)]
    if st[0] >= 2:
        f.add("U1_TRIP")
    if n > 1 and st[1] >= 2:
        f.add("U2_TRIP")
    if n > 1 and st[1] == 1:
        f.add("UNIT_DERATE")
    expected_on = len(cfg["loads"]) - len(ctx.get("shed", []))
    if any(s >= 2 for s in st) and _last(obs, "loads_on", expected_on) < expected_on - 0.5:
        f.add("STANDBY_STUCK")  # loads went dark with a tripped unit: assume the worst
    if _last(obs, "blower_motor_pct", 100.0) < 1.0:
        f.add("BLOWER_FAIL")
    return sorted(f)


def advise(observation: dict, config: dict | None = None, fault_hypothesis: list | None = None) -> Advice:
    cfg = config or load_config()
    obs, ctx = observation["observed"], observation["context"]
    n = int(ctx["units"])
    amb = float(ctx["ambient_c"])
    grad, load = float(ctx["gradient_pct"]), ctx["train_load"]
    moving = bool(ctx.get("moving", True))
    speed = float(ctx.get("speed_kmph", 40.0))
    dist = float(ctx["dist_next_station_km"])

    flags = []
    if fault_hypothesis is None:
        faults = infer_faults(cfg, obs, ctx)
        flags.append("faults_inferred_from_signals")
    else:
        faults = list(fault_hypothesis)
    plant = plant_from_faults(faults, n)

    p = resolve_params(cfg, None, "nominal")
    lim_t = cfg["limits"]["motor_temp_trip_c"]["value"]
    t_obs = _last(obs, "motor_temp_c", amb + p["rise0"])
    p_air = _last(obs, "air_pressure_bar", p["normal_bar"])
    soc = _last(obs, "battery_soc_pct", 100.0)

    # wrong-data check: a temperature that is flat while the model says it should be moving
    t0 = t_obs
    series = obs.get("motor_temp_c", [])
    if len(series) >= 30 and moving:
        slope = (series[-1] - series[-30]) / 29.0
        base = allocate(cfg, amb, plant["states"], plant["failover_ok"])
        on = "motor_blower" in base["powered"] and not plant["blower_fail"]
        h = p["h_on"] * (1.0 if on else p["h_off_ratio"])
        pred = (p["heat_full"] * heat_scale(cfg, grad, load) - h * (t_obs - amb)) / p["C"]
        if abs(slope) < 0.01 and abs(pred) > 0.05:
            flags.append("temp_sensors_disagree")
            t0 = min(lim_t - 5.0, t_obs + 25.0)

    names = [l["name"] for l in cfg["loads"]]
    prio = {l["name"]: l["priority"] for l in cfg["loads"]}
    kw = {l["name"]: l["kw"] for l in cfg["loads"]}
    now = allocate(cfg, amb, plant["states"], plant["failover_ok"])

    def times_for(subset, params):
        return limit_times(cfg, params, plant, subset, t0, amb, moving, grad, load, p_air, soc)

    best = None
    for mask in range(1 << len(names)):
        subset = {names[i] for i in range(len(names)) if mask >> i & 1}
        alloc = allocate(cfg, amb, plant["states"], plant["failover_ok"], shed=set(names) - subset)
        if alloc["powered"] != subset:
            continue  # the converters cannot feed exactly this set
        t = times_for(subset, p)
        score = (sum(1 for x in subset if prio[x] == "essential"),
                 min(min(t.values()), CAP_MIN), sum(kw[x] for x in subset))
        if best is None or score > best[0]:
            best = (score, subset, t)
    _, keep_set, t_nom = best

    rng = np.random.default_rng(0)
    runs = int(cfg["advisor"]["mc_runs"])
    mins = [min(min(times_for(keep_set, resolve_params(cfg, None, "sample", rng)).values()), CAP_MIN)
            for _ in range(runs)]
    p5 = float(np.percentile(mins, cfg["advisor"]["percentile"]))
    nominal = float(min(min(t_nom.values()), CAP_MIN))
    limiting = min(t_nom, key=lambda k: t_nom[k]) if nominal < CAP_MIN else "none"
    if now["dark"] and limiting == "none":
        limiting = "power"

    shed = sorted(x for x in now["powered"] if x not in keep_set)
    dark = sorted(now["dark"])
    if dark:
        flags.append("dark_loads:" + ",".join(dark))

    # decision
    sf = float(cfg["advisor"]["safety_factor"])
    t_station = dist / speed * 60.0 if speed > 0 else float("inf")
    t_safe = min(SAFE_PLACE_KM, dist) / speed * 60.0 if speed > 0 else float("inf")
    if not moving:
        decision = "STOP_NOW"
    elif t_station <= sf * p5:
        decision = "CONTINUE"
    elif t_safe <= sf * p5:
        decision = "STOP_AT_NEXT"
    else:
        decision = "STOP_NOW"

    where = {"CONTINUE": f"Continue: the next station is {t_station:.0f} min away.",
             "STOP_AT_NEXT": f"Stop at the nearest safe place ({t_safe:.0f} min), the station is {t_station:.0f} min away.",
             "STOP_NOW": "Stop now and call for assistance."}[decision]
    shed_txt = ("Switch off " + ", ".join(shed) + ". ") if shed else "No load needs switching off. "
    left_txt = ("No limit within 2 hours. " if p5 >= CAP_MIN
                else f"At least {p5:.0f} min until {limiting} limit. ")
    reason = shed_txt + left_txt + where

    return Advice(
        shed=shed, keep=sorted(keep_set), minutes_left_p5=round(p5, 1), minutes_left_nominal=round(nominal, 1),
        limiting_factor=limiting, decision=decision, reason=reason,
        confidence="low" if ("temp_sensors_disagree" in flags or "faults_inferred_from_signals" in flags) else "high",
        flags=flags, assumptions_used=assumed_blocks(cfg),
    )
