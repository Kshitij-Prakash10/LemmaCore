"""Robustness to our own assumptions: what if the real loco differs from what we assumed?

For each combination (corner) of low and high values of the five most uncertain parameters, the real plant takes
those values while the advisor keeps its configured beliefs, and the whole 144-case harness is rerun. This replaces
mentor-confirmed numbers with a statement of how far the conclusion holds. Output: outputs/robustness.json.
CLI: python -m failover.core.robustness --out outputs
"""

from __future__ import annotations

import argparse
import itertools
import json
import os

from .config import ROOT, load_config
from .harness import run_harness

# parameter key (as in Scenario.params), low value, high value, where the advisor's belief sits
PARAMS = {
    "motor_temp_trip_c": (160.0, 200.0),   # advisor believes 180
    "heat_full": (70.0, 110.0),            # advisor range 70 to 110, nominal 90
    "h_off_ratio": (0.12, 0.20),           # advisor range 0.12 to 0.20, nominal 0.15
    "brake_air_min_bar": (5.0, 7.0),       # advisor believes 6.0
    "leak": (0.04, 0.10),                  # advisor range 0.04 to 0.10, nominal 0.05
}


def run_robustness(config: dict | None = None, out_dir: str = "outputs", workers: int | None = None,
                   max_corners: int | None = None, max_cases: int | None = None, n_mc: int = 100) -> dict:
    cfg = config or load_config()
    keys = list(PARAMS)
    corners = list(itertools.product(*[PARAMS[k] for k in keys]))
    if max_corners:
        corners = corners[:max_corners]
    rows = []
    for vals in corners:
        params = dict(zip(keys, vals))
        cov = run_harness(cfg, out_dir, n_mc=n_mc, workers=workers, max_cases=max_cases,
                          scenario_params=params, write=False)
        s = cov["summary"]
        optimistic = sum("P4_optimistic_minutes_left" in c["properties_failed"] for c in cov["cases"])
        rows.append({"params": params, "runs_per_policy": s["runs_per_policy"],
                     "baseline_unsafe": s["baseline_unsafe"], "advisor_unsafe": s["advisor_unsafe"],
                     "saved_by_advisor": s["saved_by_advisor"], "false_stops": s["false_stops"],
                     "advisor_optimistic_cases": optimistic})

    def span(key):
        vals = [r[key] for r in rows]
        return {"min": min(vals), "max": max(vals)}

    worst = max(rows, key=lambda r: (r["advisor_unsafe"], r["advisor_optimistic_cases"]))
    data = {
        "note": "the real plant takes each corner value; the advisor keeps the configured beliefs",
        "ranges_tested": {k: list(v) for k, v in PARAMS.items()},
        "n_corners": len(rows),
        "summary": {"baseline_unsafe": span("baseline_unsafe"), "advisor_unsafe": span("advisor_unsafe"),
                    "saved_by_advisor": span("saved_by_advisor"), "false_stops": span("false_stops"),
                    "advisor_optimistic_cases": span("advisor_optimistic_cases")},
        "worst_corner_for_advisor": worst,
        "corners": rows,
    }
    out = out_dir if os.path.isabs(out_dir) else os.path.join(ROOT, out_dir)
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "robustness.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1)
    return data


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="outputs")
    ap.add_argument("--workers", type=int, default=None)
    a = ap.parse_args()
    d = run_robustness(None, a.out, a.workers)
    print(json.dumps(d["summary"], indent=1))
    print("worst corner for the advisor:", json.dumps(d["worst_corner_for_advisor"]))


if __name__ == "__main__":
    main()
