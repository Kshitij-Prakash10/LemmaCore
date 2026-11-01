"""Small command line: python -m failover.core.cli demo"""

from __future__ import annotations

import sys

from .config import load_config
from .simulate import simulate
from .types import Scenario


def demo() -> None:
    cfg = load_config()
    sc = Scenario(id="demo_hot_climb_standby_stuck", faults=("STANDBY_STUCK",), ambient_c=45.0, gradient_pct=2.7,
                  dist_next_station_km=15.0, speed_kmph=40.0, seed=1)
    print(f"Hard case: {', '.join(sc.faults)} on a hot climb, station {sc.dist_next_station_km:.0f} km away")
    for policy in ("baseline", "advisor"):
        r = simulate(sc, policy, cfg)
        print(f"  {policy:9s} outcome={r.outcome:16s} limit={r.limit_hit} t_limit_s={r.t_limit_s} "
              f"reached_station={r.reached_station} minutes_left_true={r.minutes_left_true}")
        for e in r.events:
            if e["type"] == "advice":
                print(f"            advice at {e['t_s']:.0f}s: {e['decision']}, shed {e['shed']}, "
                      f"p5 {e['minutes_left_p5']} min")
                break


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        demo()
    else:
        print("usage: python -m failover.core.cli demo")
