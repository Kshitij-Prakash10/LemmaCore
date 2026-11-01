"""Generate labelled 60 s windows by calling the core's simulate(). No physics here.

CLI: python -m failover.ml.make_dataset  (writes data/processed/scenarios.csv and scenarios_meta.json)
"""
from __future__ import annotations

import itertools
import json
import os
from datetime import datetime, timezone
from multiprocessing import Pool

import numpy as np
import pandas as pd

import failover.core as core
from failover.core.config import load_config
from failover.core.simulate import simulate
from failover.core.types import FAULT_IDS, Scenario
from failover.ml.features import feature_names, window_features

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT_DIR = os.path.join(ROOT, "data", "processed")
WINDOW_S = 60
WINDOW_ENDS_S = (60, 120, 300, 600)  # fault at 60 s; the first window is pre-fault (healthy)
PARAM_KEYS = ("C", "h_on", "h_off_ratio", "heat_full", "leak")
COMBOS: list[tuple[str, ...]] = [()] + [(f,) for f in FAULT_IDS] + list(itertools.combinations(FAULT_IDS, 2))
SEED = 1


def _nominal_params(cfg: dict) -> dict:
    from failover.core.model import resolve_params
    p = resolve_params(cfg, None, "nominal")
    return {k: p[k] for k in PARAM_KEYS}


def scenario_specs(n_per_combo: int, seed: int, param_scale: tuple[float, float] = (0.8, 1.2),
                   noise: float | None = None, combos: list[tuple[str, ...]] | None = None,
                   ood: bool = False) -> list[dict]:
    """Random scenario specs. param_scale multiplies nominal parameters (domain randomization).
    ood=True draws each scale from the bands outside the training range (0.7-0.8 or 1.2-1.3)."""
    rng = np.random.default_rng(seed)
    nominal = _nominal_params(load_config(os.path.join(ROOT, "config", "loco.json")))
    specs = []
    for combo in combos or COMBOS:
        for _ in range(n_per_combo):
            if ood:
                scale = {k: float(rng.choice([rng.uniform(0.7, 0.8), rng.uniform(1.2, 1.3)])) for k in PARAM_KEYS}
            else:
                scale = {k: float(rng.uniform(*param_scale)) for k in PARAM_KEYS}
            specs.append({
                "faults": list(combo),
                "ambient_c": float(rng.uniform(20, 48)),
                "gradient_pct": float(rng.uniform(0, 3)),
                "train_load": str(rng.choice(["empty", "loaded"])),
                "units": int(rng.choice([2, 3])),
                "dist_next_station_km": float(rng.uniform(1, 30)),
                "speed_kmph": float(rng.uniform(20, 100)),
                "noise": float(rng.uniform(0, 0.1)) if noise is None else float(noise),
                "seed": int(rng.integers(1, 2**31 - 1)),
                "params": {k: nominal[k] * scale[k] for k in PARAM_KEYS},
            })
    return specs


def windows_for(spec: dict) -> list[dict]:
    """Run the baseline policy for one spec and cut labelled windows from the observed signals."""
    sc = Scenario(id=f"s{spec['seed']}", faults=tuple(spec["faults"]), ambient_c=spec["ambient_c"],
                  gradient_pct=spec["gradient_pct"], train_load=spec["train_load"], units=spec["units"],
                  dist_next_station_km=spec["dist_next_station_km"], speed_kmph=spec["speed_kmph"],
                  noise=spec["noise"], seed=spec["seed"], params=spec["params"])
    res = simulate(sc, "baseline", horizon_s=max(WINDOW_ENDS_S))
    t = np.asarray(res.t_s)
    rows = []
    for end in WINDOW_ENDS_S:
        idx = np.where((t > end - WINDOW_S) & (t <= end))[0]
        win = {k: [v[i] for i in idx] for k, v in res.observed.items()}
        active = spec["faults"] if end > 60 else []
        row = dict(zip(feature_names(), window_features(win)))
        row.update({f"y_{f}": int(f in active) for f in FAULT_IDS})
        row.update({"seed": spec["seed"], "combo": "+".join(spec["faults"]) or "healthy",
                    "window_end_s": end, "noise": spec["noise"]})
        rows.append(row)
    return rows


def build(specs: list[dict], processes: int | None = None) -> pd.DataFrame:
    """Windows for all specs, in parallel."""
    with Pool(processes or max(1, (os.cpu_count() or 2) - 1)) as pool:
        chunks = pool.map(windows_for, specs, chunksize=16)
    return pd.DataFrame([r for c in chunks for r in c])


def main(n_per_combo: int = 40) -> pd.DataFrame:
    """Write the training dataset and its metadata."""
    os.makedirs(OUT_DIR, exist_ok=True)
    df = build(scenario_specs(n_per_combo, SEED))
    df.to_csv(os.path.join(OUT_DIR, "scenarios.csv"), index=False)
    meta = {"core_version": core.CORE_VERSION, "seed": SEED, "n_per_combo": n_per_combo,
            "n_windows": len(df), "n_scenarios": int(df["seed"].nunique()),
            "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "synthetic": True, "note": "Simulated by failover.core (baseline policy). Synthetic data."}
    with open(os.path.join(OUT_DIR, "scenarios_meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    print(f"wrote {len(df)} windows from {meta['n_scenarios']} scenarios")
    return df


if __name__ == "__main__":
    main()
