"""Current leak rate from the latest compressor-off pressure decay (MetroPT-3 style minute data)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from failover.ml.leak_features import LOADED_A  # noqa: F401  (threshold documented there)

LOOKBACK_MIN = 30
MIN_RUN = 3  # minutes


def estimate(minute: pd.DataFrame) -> dict | None:
    """{"bar_per_min" (positive = falling), "r2", "n_minutes", "confidence"} from the latest unloaded run
    of at least 3 minutes in the last 30 minutes; None if there is none. Input: leak_features.to_minutes output."""
    if minute is None or len(minute) == 0:
        return None
    m = minute.iloc[-LOOKBACK_MIN:]
    off = ((m["loaded_frac"] <= 0.5) & (m["n_rows"] > 0) & m["Reservoirs"].notna()).to_numpy()
    if not off.any():
        return None
    end = len(off) - 1 - int(np.argmax(off[::-1]))
    start = end
    while start > 0 and off[start - 1]:
        start -= 1
    n = end - start + 1
    if n < MIN_RUN:
        return None
    y = m["Reservoirs"].to_numpy(float)[start:end + 1]
    x = np.arange(n, dtype=float)
    slope, icpt = np.polyfit(x, y, 1)
    ss = float(((y - y.mean()) ** 2).sum())
    r2 = 1.0 - float(((y - (slope * x + icpt)) ** 2).sum()) / ss if ss > 0 else 0.0
    return {"bar_per_min": round(float(-slope), 4), "r2": round(r2, 3), "n_minutes": n,
            "confidence": "high" if n >= 5 and r2 >= 0.8 else "low"}
