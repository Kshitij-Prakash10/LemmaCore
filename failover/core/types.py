"""Shared names and types. Units: seconds, degrees C, bar, kW, kVA, volts, percent."""

from __future__ import annotations

from dataclasses import dataclass, field

FAULT_IDS = [
    "U1_TRIP",            # converter unit 1 trips off; the standby takes over unless STANDBY_STUCK
    "U2_TRIP",            # converter unit 2 trips off
    "STANDBY_STUCK",      # unit 1 is lost and the standby does NOT take over its loads
    "MCB_TRIP",           # front-panel MCB trips: unit 1 cut off, load does not shift
    "UNIT_DERATE",        # unit 2 capacity falls to the derate factor in the config
    "BLOWER_FAIL",        # the motor cooling blower stops (cooling falls to its off value)
    "COMPRESSOR_FAIL",    # the brake-air compressor stops, so air pressure decays
    "TEMP_SENSOR_STUCK",  # the observed motor temperature freezes at its last good value
]

CONDITION_IDS = ["cool_flat", "hot_flat", "cool_climb", "hot_climb"]
POLICIES = ["baseline", "advisor"]
OUTCOMES = ["SAFE", "CONTROLLED_STOP", "UNSAFE"]

SIGNAL_NAMES = [
    "unit1_state", "unit2_state", "unit3_state",
    "unit1_load_kva", "unit2_load_kva", "unit3_load_kva",
    "power_demand_kw", "power_available_kw", "dc_link_v",
    "blower_motor_pct", "blower_oil_pct",
    "motor_temp_c", "converter_temp_c",
    "air_pressure_bar", "battery_v", "battery_soc_pct", "loads_on",
]

DECISIONS = ["CONTINUE", "STOP_AT_NEXT", "STOP_NOW"]


@dataclass(frozen=True)
class Scenario:
    id: str
    faults: tuple = ()
    ambient_c: float = 45.0
    gradient_pct: float = 2.7
    train_load: str = "loaded"
    units: int = 2
    dist_next_station_km: float = 9.0
    speed_kmph: float = 40.0
    noise: float = 0.0
    seed: int = 0
    params: dict = field(default_factory=dict)


@dataclass
class SimResult:
    scenario_id: str
    policy: str
    core_version: str
    t_s: list
    true: dict
    observed: dict
    events: list
    outcome: str
    limit_hit: str | None
    t_limit_s: float | None
    reached_station: bool
    minutes_left_true: float | None


@dataclass
class Advice:
    shed: list
    keep: list
    minutes_left_p5: float
    minutes_left_nominal: float
    limiting_factor: str
    decision: str
    reason: str
    confidence: str
    flags: list
    assumptions_used: list
