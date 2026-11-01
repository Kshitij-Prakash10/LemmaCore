"""Numerical checks: time-step convergence and speed limits from CONTRACT.md."""

import time

from failover.core.advisor import advise
from failover.core.config import load_config
from failover.core.simulate import simulate
from failover.core.types import Scenario

CFG = load_config()
SC = Scenario(id="num", faults=("STANDBY_STUCK",), ambient_c=45.0, gradient_pct=2.7, dist_next_station_km=12.0, seed=1)


def test_time_step_halving_changes_limit_time_under_one_percent():
    a = simulate(SC, "baseline", CFG, dt_s=1.0)
    b = simulate(SC, "baseline", CFG, dt_s=0.5)
    assert a.t_limit_s is not None and b.t_limit_s is not None
    assert abs(a.t_limit_s - b.t_limit_s) / a.t_limit_s < 0.01


def test_advise_is_fast():
    r = simulate(SC, "baseline", CFG)
    window = {k: v[:100][-60:] for k, v in r.observed.items()}
    ctx = {"ambient_c": 45, "gradient_pct": 2.7, "train_load": "loaded", "units": 2,
           "dist_next_station_km": 12, "speed_kmph": 40, "moving": True, "shed": []}
    t = time.perf_counter()
    advise({"observed": window, "context": ctx}, CFG, fault_hypothesis=["STANDBY_STUCK"])
    assert time.perf_counter() - t < 0.05


def test_simulate_is_fast():
    t = time.perf_counter()
    simulate(SC, "baseline", CFG)
    assert time.perf_counter() - t < 0.5
