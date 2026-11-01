"""Contract tests: shapes, determinism and the properties Agent B relies on."""

import math

import pytest

from failover.core import CORE_VERSION
from failover.core.advisor import advise
from failover.core.config import load_config
from failover.core.simulate import simulate
from failover.core.types import (DECISIONS, FAULT_IDS, OUTCOMES, POLICIES, SIGNAL_NAMES, Advice, Scenario)

CFG = load_config()


def _sc(faults=(), **kw):
    base = dict(id="t", faults=tuple(faults), ambient_c=45.0, gradient_pct=2.7, dist_next_station_km=15.0, seed=1)
    base.update(kw)
    return Scenario(**base)


def test_core_version_present():
    assert isinstance(CORE_VERSION, str) and CORE_VERSION


@pytest.mark.parametrize("policy", POLICIES)
def test_simulate_shapes(policy):
    r = simulate(_sc(("STANDBY_STUCK",)), policy, CFG)
    n = len(r.t_s)
    assert n == 1801
    assert set(r.true) == set(SIGNAL_NAMES) and set(r.observed) == set(SIGNAL_NAMES)
    assert all(len(v) == n for v in r.true.values()) and all(len(v) == n for v in r.observed.values())
    assert r.outcome in OUTCOMES and r.core_version == CORE_VERSION


def test_deterministic():
    a = simulate(_sc(("U1_TRIP",), noise=0.05), "advisor", CFG)
    b = simulate(_sc(("U1_TRIP",), noise=0.05), "advisor", CFG)
    assert a.observed == b.observed and a.outcome == b.outcome


@pytest.mark.parametrize("fault", FAULT_IDS)
def test_every_fault_runs(fault):
    for policy in POLICIES:
        r = simulate(_sc((fault,)), policy, CFG)
        assert r.outcome in OUTCOMES


def test_stuck_sensor_freezes_observed_temperature():
    r = simulate(_sc(("TEMP_SENSOR_STUCK", "BLOWER_FAIL")), "baseline", CFG)
    after = r.observed["motor_temp_c"][100:]
    assert max(after) - min(after) < 1e-9
    assert r.true["motor_temp_c"][-1] > r.true["motor_temp_c"][100]


def test_advice_shape_and_range():
    sc = _sc(("STANDBY_STUCK",))
    r = simulate(sc, "baseline", CFG)
    window = {k: v[:100][-60:] for k, v in r.observed.items()}
    ctx = {"ambient_c": 45, "gradient_pct": 2.7, "train_load": "loaded", "units": 2,
           "dist_next_station_km": 15, "speed_kmph": 40, "moving": True, "shed": []}
    adv = advise({"observed": window, "context": ctx}, CFG, fault_hypothesis=["STANDBY_STUCK"])
    assert isinstance(adv, Advice)
    assert adv.decision in DECISIONS
    assert 0 <= adv.minutes_left_p5 <= adv.minutes_left_nominal + 1e-6 or adv.minutes_left_p5 <= 120
    assert adv.limiting_factor in ("heat", "air", "battery", "power", "none")
    assert all(x in {l["name"] for l in CFG["loads"]} for x in adv.shed + adv.keep)


def test_hard_case_advisor_not_worse_than_baseline():
    sc = _sc(("STANDBY_STUCK",))
    base, adv = simulate(sc, "baseline", CFG), simulate(sc, "advisor", CFG)
    rank = {"SAFE": 0, "CONTROLLED_STOP": 1, "UNSAFE": 2}
    assert base.outcome == "UNSAFE"
    assert adv.outcome != "UNSAFE"
    assert rank["UNSAFE"] > rank[adv.outcome]


def test_closed_form_matches_stepping():
    from failover.core.model import motor_time_to_limit_min, resolve_params
    p = resolve_params(CFG)
    amb, q, h = 45.0, 70.0, p["h_on"] * p["h_off_ratio"]
    lim = CFG["limits"]["motor_temp_trip_c"]["value"]
    t0 = amb + p["rise0"]
    closed = motor_time_to_limit_min(t0, amb, q, h, p["C"], lim)
    assert math.isfinite(closed)
    t, temp, dt = 0.0, t0, 0.25
    while temp < lim and t < 10 * 3600:
        temp += dt * (q - h * (temp - amb)) / p["C"]
        t += dt
    assert abs(t / 60.0 - closed) / closed < 0.01
