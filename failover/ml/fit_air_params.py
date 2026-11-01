"""Fit the brake-air pressure decay rate from MetroPT-3 compressor-off segments (proxy for a loco leak rate).

Writes data/processed/air_params_fit.json. CLI: python -m failover.ml.fit_air_params
"""
from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd

from failover.ml import data_metropt as dm

OUT = os.path.join(dm.ROOT, "data", "processed", "air_params_fit.json")
SEED = 11
OFF_CURRENT_A = 1.0     # motor current below this means the compressor is off (PDF: about 0 A when off)
MIN_SEGMENT_MIN = 3.0   # shortest off segment used, minutes
MARGIN = pd.Timedelta(days=1)  # keep away from labelled failures


def segment_rates(df: pd.DataFrame) -> np.ndarray:
    """Decay rate (bar per minute, positive = falling) of reservoir pressure in each compressor-off segment."""
    off = (df["Motor_current"] < OFF_CURRENT_A).to_numpy()
    gap = df.index.to_series().diff().dt.total_seconds().fillna(10).to_numpy() > 60
    seg_id = np.cumsum((np.diff(off.astype(int), prepend=0) != 0) | gap)
    t_min = (df.index - df.index[0]).total_seconds().to_numpy() / 60
    p = df["Reservoirs"].to_numpy(float)
    rates = []
    for sid in np.unique(seg_id[off]):
        idx = np.where((seg_id == sid) & off)[0]
        if len(idx) < 3 or t_min[idx[-1]] - t_min[idx[0]] < MIN_SEGMENT_MIN:
            continue
        rates.append(-np.polyfit(t_min[idx], p[idx], 1)[0])
    return np.asarray(rates)


def main() -> dict:
    """Fit and write the leak-rate range."""
    df = dm.load()
    keep = np.ones(len(df), dtype=bool)
    for f in dm.failures():
        keep &= ~((df.index >= f["start"] - MARGIN) & (df.index <= f["end"] + MARGIN))
    rates = segment_rates(df[keep])
    rates = rates[np.isfinite(rates)]
    rng = np.random.default_rng(SEED)
    boot = [np.median(rng.choice(rates, size=len(rates), replace=True)) for _ in range(1000)]
    lo, hi = np.percentile(boot, [2.5, 97.5])
    out = {
        "leak_bar_per_min": {"min": round(float(np.percentile(rates, 10)), 4),
                             "nominal": round(float(np.median(rates)), 4),
                             "max": round(float(np.percentile(rates, 90)), 4)},
        "median_ci95_bar_per_min": [round(float(lo), 4), round(float(hi), 4)],
        "n_segments": int(len(rates)),
        "method": f"Linear slope of Reservoirs pressure in compressor-off segments (motor current < {OFF_CURRENT_A} A, "
                  f">= {MIN_SEGMENT_MIN} min), excluding +-1 day around labelled failures. min/max: 10th and 90th "
                  f"percentile across segments. median_ci95: bootstrap (1000 resamples, seed {SEED}).",
        "source": "MetroPT-3 proxy", "status": "fitted_proxy",
        "limits": "Metro train in Porto, not a loco. Off-segment decay includes normal air use (brakes, doors), "
                  "so it is an upper bound on pure leakage. The median is above the loco dispatch limit "
                  "in config/loco.json (0.067 bar/min), which fits that reading.",
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(json.dumps(out, indent=1))
    return out


if __name__ == "__main__":
    main()
