"""STUB core: a shape-correct stand-in for failover.core, per CONTRACT.md v0.1.

Every number here is FAKE and exists only so the app can be built before the
real core lands. Nothing from this module may be shown as a result. The app
labels everything it gets from here with "STUB".
"""
from __future__ import annotations

import itertools
import json
import math
import random
from dataclasses import dataclass, field
from datetime import datetime, timezone

CORE_VERSION = "stub-0.1"
CONTRACT_VERSION = "0.1"

FAULT_IDS = [
    "U1_TRIP", "U2_TRIP", "STANDBY_STUCK", "MCB_TRIP",
    "UNIT_DERATE", "BLOWER_FAIL", "COMPRESSOR_FAIL", "TEMP_SENSOR_STUCK",
]
CONDITION_IDS = ["cool_flat", "hot_flat", "cool_climb", "hot_climb"]
CONDITIONS = {
    "cool_flat": {"ambient_c": 30, "gradient_pct": 0.0, "train_load": "loaded"},
    "hot_flat": {"ambient_c": 45, "gradient_pct": 0.0, "train_load": "loaded"},
    "cool_climb": {"ambient_c": 30, "gradient_pct": 2.7, "train_load": "loaded"},
    "hot_climb": {"ambient_c": 45, "gradient_pct": 2.7, "train_load": "loaded"},
}
POLICIES = ["baseline", "advisor"]
OUTCOMES = ["SAFE", "CONTROLLED_STOP", "UNSAFE"]

SIGNALS = [
    "unit1_state", "unit2_state", "unit1_load_kva", "unit2_load_kva",
    "power_demand_kw", "power_available_kw", "dc_link_v",
    "blower_motor_pct", "blower_oil_pct", "motor_temp_c", "converter_temp_c",
    "air_pressure_bar", "battery_v", "battery_soc_pct", "loads_on",
]


@dataclass(frozen=True)
class Scenario:
    id: str
    faults: tuple[str, ...] = ()
    ambient_c: float = 45.0
    gradient_pct: float = 2.7
    train_load: str = "loaded"
    units: int = 2
    dist_next_station_km: float = 12.0
    speed_kmph: float = 60.0
    noise: float = 0.0
    seed: int = 1
    params: dict = field(default_factory=dict)


@dataclass
class SimResult:
    scenario_id: str
    policy: str
    core_version: str
    t_s: list[float]
    true: dict[str, list[float]]
    observed: dict[str, list[float]]
    events: list[dict]
    outcome: str
    limit_hit: str | None
    t_limit_s: float | None
    reached_station: bool
    minutes_left_true: float | None


@dataclass
class Advice:
    shed: list[str]
    keep: list[str]
    minutes_left_p5: float
    minutes_left_nominal: float
    limiting_factor: str
    decision: str
    reason: str
    confidence: str
    flags: list[str]
    assumptions_used: list[str]


def load_config(path: str = "config/loco.json") -> dict:
    """Read the loco config as a dict."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _severity(faults: tuple[str, ...], ambient_c: float, gradient_pct: float) -> float:
    """Fake 0..1 severity used to shape stub curves."""
    s = 0.15 * len(faults) + (ambient_c - 20) / 100 + gradient_pct / 10
    if "STANDBY_STUCK" in faults or "BLOWER_FAIL" in faults:
        s += 0.3
    return min(1.0, s)


def simulate(scenario: Scenario, policy: str, config: dict | None = None,
             horizon_s: int = 1800, dt_s: float = 1.0) -> SimResult:
    """FAKE simulation: smooth made-up curves, seconds and degrees C."""
    rng = random.Random(scenario.seed)
    n = int(horizon_s / dt_s) + 1
    t = [i * dt_s for i in range(n)]
    sev = _severity(scenario.faults, scenario.ambient_c, scenario.gradient_pct)
    rate = sev * (0.45 if policy == "advisor" else 1.0)  # C per minute, fake
    temp = [scenario.ambient_c + 40 + rate * 60 * (1 - math.exp(-ti / 900)) * 2 + ti / 60 * rate * 0.5 for ti in t]
    leak = 0.08 if "COMPRESSOR_FAIL" in scenario.faults else 0.0
    air = [max(4.0, 9.0 - leak * ti / 60) for ti in t]
    true: dict[str, list[float]] = {s: [0.0] * n for s in SIGNALS}
    true["motor_temp_c"] = temp
    true["converter_temp_c"] = [x - 20 for x in temp]
    true["air_pressure_bar"] = air
    true["unit1_state"] = [2.0 if "U1_TRIP" in scenario.faults and ti >= 10 else 0.0 for ti in t]
    true["unit2_state"] = [2.0 if "U2_TRIP" in scenario.faults and ti >= 10 else 0.0 for ti in t]
    true["blower_motor_pct"] = [0.0 if "BLOWER_FAIL" in scenario.faults else 100.0] * n
    true["blower_oil_pct"] = [100.0] * n
    true["battery_v"] = [110.0] * n
    true["battery_soc_pct"] = [90.0] * n
    true["dc_link_v"] = [600.0] * n
    true["loads_on"] = [5.0 if policy == "advisor" else 7.0] * n
    true["power_demand_kw"] = [62.0 if policy == "advisor" else 85.0] * n
    true["power_available_kw"] = [104.0 if not scenario.faults else 52.0] * n
    observed = {k: [x + rng.gauss(0, scenario.noise * max(1.0, abs(x))) for x in v] for k, v in true.items()}
    if "TEMP_SENSOR_STUCK" in scenario.faults:
        observed["motor_temp_c"] = [observed["motor_temp_c"][0] if ti >= 10 else x
                                    for ti, x in zip(t, observed["motor_temp_c"])]
    limit = 180.0
    t_limit = next((ti for ti, x in zip(t, temp) if x >= limit), None)
    if t_limit is not None:
        outcome, hit = "UNSAFE", "motor_temp"
    elif policy == "advisor" and sev > 0.5:
        outcome, hit = "CONTROLLED_STOP", None
    else:
        outcome, hit = "SAFE", None
    return SimResult(
        scenario_id=scenario.id, policy=policy, core_version=CORE_VERSION, t_s=t,
        true=true, observed=observed,
        events=[{"t_s": 10.0, "type": "fault_injected", "fault": f} for f in scenario.faults],
        outcome=outcome, limit_hit=hit, t_limit_s=t_limit,
        reached_station=outcome == "SAFE",
        minutes_left_true=(t_limit / 60 if t_limit else None),
    )


def advise(observation: dict, config: dict | None = None,
           fault_hypothesis: list[str] | None = None) -> Advice:
    """FAKE advice with the contract's shape."""
    ctx = observation.get("context", {})
    obs = observation.get("observed", {})
    faults = tuple(fault_hypothesis or [])
    sev = _severity(faults, ctx.get("ambient_c", 45), ctx.get("gradient_pct", 2.7))
    flags = ["STUB_CORE"]
    temps = obs.get("motor_temp_c") or []
    if len(temps) > 5 and max(temps) - min(temps) < 1e-6:
        flags.append("temp_sensors_disagree")
    p5 = round(max(1.0, 30 * (1 - sev)) * (0.7 if "temp_sensors_disagree" in flags else 1.0), 1)
    decision = "CONTINUE" if sev < 0.4 else ("STOP_AT_NEXT" if sev < 0.8 else "STOP_NOW")
    return Advice(
        shed=["cab_ac", "lighting_and_fans"] if faults else [],
        keep=["brake_compressor", "control_and_charger", "motor_blower", "oil_cooling_blower", "oil_pump"],
        minutes_left_p5=p5, minutes_left_nominal=round(p5 * 1.4, 1),
        limiting_factor="air" if "COMPRESSOR_FAIL" in faults else "heat",
        decision=decision,
        reason="STUB: fake advice for building the app, not a real result.",
        confidence="low" if "temp_sensors_disagree" in flags else "high",
        flags=flags, assumptions_used=["limits.motor_temp_trip_c"],
    )


def fault_combinations() -> list[tuple[str, ...]]:
    """The 36 harness combinations: 8 singles then 28 pairs."""
    return [(f,) for f in FAULT_IDS] + list(itertools.combinations(FAULT_IDS, 2))


def stub_coverage() -> dict:
    """FAKE coverage.json in the CONTRACT.md schema."""
    cases = []
    for combo in fault_combinations():
        for cid in CONDITION_IDS:
            c = CONDITIONS[cid]
            sc = Scenario(id="__".join(combo) + "__" + cid, faults=combo, ambient_c=c["ambient_c"],
                          gradient_pct=c["gradient_pct"])
            b = simulate(sc, "baseline", horizon_s=1800, dt_s=10)
            a = simulate(sc, "advisor", horizon_s=1800, dt_s=10)
            adv = advise({"context": c, "observed": {}}, fault_hypothesis=list(combo))
            cases.append({
                "case_id": sc.id, "faults": list(combo), "condition": cid,
                "baseline": {"outcome": b.outcome, "limit_hit": b.limit_hit,
                             "t_limit_s": b.t_limit_s, "reached_station": b.reached_station},
                "advisor": {"outcome": a.outcome, "minutes_left_p5": adv.minutes_left_p5,
                            "decision": adv.decision, "shed": adv.shed,
                            "limiting_factor": adv.limiting_factor, "reached_station": a.reached_station},
                "properties_ok": True,
            })
    return {
        "core_version": CORE_VERSION, "stub": True,
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "seed": 1,
        "conditions": [{"id": k, **v} for k, v in CONDITIONS.items()],
        "faults": FAULT_IDS, "cases": cases,
        "summary": {"runs_per_policy": len(cases),
                    "baseline_unsafe": sum(c["baseline"]["outcome"] == "UNSAFE" for c in cases),
                    "advisor_unsafe": sum(c["advisor"]["outcome"] == "UNSAFE" for c in cases),
                    "properties_failed": 0},
    }
