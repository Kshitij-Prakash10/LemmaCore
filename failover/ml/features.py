"""Window features for the fault classifier. Uses observed signals only (CONTRACT.md section 3)."""
from __future__ import annotations

import numpy as np

from failover.core.types import SIGNAL_NAMES

STATS = ("mean", "std", "slope", "min", "max", "last")


def _stats(x: np.ndarray) -> list[float]:
    if x.size == 0:
        return [0.0] * len(STATS)
    slope = float(np.polyfit(np.arange(x.size), x, 1)[0]) if x.size > 1 else 0.0  # units per sample
    return [float(x.mean()), float(x.std()), slope, float(x.min()), float(x.max()), float(x[-1])]


def feature_names() -> list[str]:
    """Names in the order window_features returns them."""
    names = [f"{s}__{st}" for s in SIGNAL_NAMES for st in STATS]
    return names + ["margin_kw_mean", "unit_load_diff_kva", "temp_minus_conv_slope", "temp_flat_vs_conv"]


def window_features(window: dict[str, list[float]]) -> np.ndarray:
    """Feature vector from a dict of observed series (about 60 samples, 1 s apart). Missing signals count as zeros."""
    arrs = {s: np.asarray(window.get(s, []), dtype=float) for s in SIGNAL_NAMES}
    feats: list[float] = []
    for s in SIGNAL_NAMES:
        feats += _stats(arrs[s])
    avail, dem = arrs["power_available_kw"], arrs["power_demand_kw"]
    margin = float((avail - dem).mean()) if avail.size and avail.size == dem.size else 0.0
    u1, u2 = arrs["unit1_load_kva"], arrs["unit2_load_kva"]
    load_diff = float((u1 - u2).mean()) if u1.size and u1.size == u2.size else 0.0
    tm, tc = _stats(arrs["motor_temp_c"]), _stats(arrs["converter_temp_c"])
    flat = 1.0 if arrs["motor_temp_c"].size > 5 and tm[1] < 1e-6 and abs(tc[2]) > 1e-4 else 0.0
    feats += [margin, load_diff, tm[2] - tc[2], flat]
    return np.asarray(feats, dtype=float)
