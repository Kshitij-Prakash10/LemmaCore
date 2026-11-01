"""Shared air-leak features (train, test and app). Input: raw compressor rows; output: one row per minute.

Loaded threshold: MetroPT-3 motor current has three modes (histogram printed by `python -m failover.ml.leak_features`):
off below 0.5 A, running unloaded at 3.5-4 A, loaded at 5-6.5 A. The valley is at 4.5-5 A, so a row is
"loaded" when current > 4.75 A. COMP agrees: active 0.3 % of the time above 5 A, 99 % below 1 A.
Decay is measured on unloaded minutes (off or running unloaded: no air goes in), recharge on loaded minutes.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# one place for header spelling; MetroPT-2 or other sources map onto these names
COLUMN_MAP = {"DV_electric": "DV_eletric", "Oil_Temperature": "Oil_temperature", "Motor_Current": "Motor_current",
              "Caudal_Impulses": "Caudal_impulses", "Pressure_Switch": "Pressure_switch", "Oil_Level": "Oil_level"}
SIGNALS = ["TP2", "TP3", "H1", "DV_pressure", "Reservoirs", "Motor_current", "Oil_temperature"]
LOADED_A = 4.75
WIN = 60          # minutes, cycle and rate window
SHORT = 10        # minutes, mean/std window
MAX_MISSING = 0.2
FLAT_STD = 1e-4   # bar; Reservoirs this flat for SHORT minutes is a stuck sensor


def normalise(df: pd.DataFrame) -> pd.DataFrame:
    """Rename known header variants to MetroPT-3 names."""
    return df.rename(columns={k: v for k, v in COLUMN_MAP.items() if k in df.columns})


def to_minutes(raw: pd.DataFrame) -> pd.DataFrame:
    """1 min means of the signals, the loaded fraction, COMP and a row count. Index: timestamps."""
    raw = normalise(raw)
    x = raw[SIGNALS + ["COMP"]].astype(float).copy()
    x["loaded_frac"] = (raw["Motor_current"] > LOADED_A).astype(float)
    g = x.resample("1min")
    m = g.mean()
    m["n_rows"] = g["Reservoirs"].count()
    return m


def feature_names() -> list[str]:
    """Order of the model input."""
    names = ["cycles_per_h", "mean_loaded_run_min", "mean_off_min", "decay_bar_per_min",
             "recharge_bar_per_min", "load_duty"]
    return names + [f"{s}_{k}" for s in SIGNALS for k in ("mean10", "std10")]


def features(minute: pd.DataFrame) -> pd.DataFrame:
    """Rolling features per minute plus a `valid` column. Invalid rows must never be scored."""
    have = minute["n_rows"].fillna(0) > 0
    loaded = (minute["loaded_frac"] > 0.5) & have
    unloaded = (~loaded) & have
    start = loaded & ~loaded.shift(1, fill_value=False)
    off_start = unloaded & ~unloaded.shift(1, fill_value=False)
    dp = minute["Reservoirs"].diff()
    both_off = unloaded & unloaded.shift(1, fill_value=False)
    both_on = loaded & loaded.shift(1, fill_value=False)
    r = lambda s: s.astype(float).rolling(WIN, min_periods=1).sum()  # noqa: E731
    n_on, n_off = r(loaded), r(unloaded)
    f = pd.DataFrame(index=minute.index)
    f["cycles_per_h"] = r(start) * 60.0 / WIN
    f["mean_loaded_run_min"] = n_on / r(start).clip(lower=1)
    f["mean_off_min"] = n_off / r(off_start).clip(lower=1)
    # mean minute-to-minute slope over unloaded (or loaded) minutes: a linear fit per pair of minutes
    f["decay_bar_per_min"] = -(dp.where(both_off, 0.0).rolling(WIN, min_periods=1).sum()
                               / r(both_off).replace(0, np.nan))
    f["recharge_bar_per_min"] = (dp.where(both_on, 0.0).rolling(WIN, min_periods=1).sum()
                                 / r(both_on).replace(0, np.nan))
    f["load_duty"] = 1.0 - minute["COMP"].rolling(WIN, min_periods=1).mean()
    for s in SIGNALS:
        rs = minute[s].rolling(SHORT, min_periods=SHORT // 2)
        f[f"{s}_mean10"] = rs.mean()
        f[f"{s}_std10"] = rs.std()
    missing = 1.0 - have.astype(float).rolling(WIN, min_periods=WIN).mean()
    flat = minute["Reservoirs"].rolling(SHORT, min_periods=SHORT).std() < FLAT_STD
    f = f[feature_names()]
    # a missing decay or recharge rate is not bad data: during a leak the compressor never unloads,
    # so there is no off period to measure. Only missing rows and a flat Reservoirs sensor are invalid.
    short_ok = f[[c for c in feature_names() if c.endswith("10")]].notna().all(axis=1)
    f["valid"] = (missing <= MAX_MISSING) & ~flat & short_ok
    f[feature_names()] = f[feature_names()].fillna(0.0)
    return f


def alarm(p: np.ndarray, valid: np.ndarray, theta: float, k: int = 7, n: int = 10) -> np.ndarray:
    """Alert when p > theta in at least k of the last n minutes. Invalid minutes never count."""
    hit = pd.Series(((p > theta) & valid).astype(float))
    return (hit.rolling(n, min_periods=n).sum() >= k).to_numpy() & valid


class IFScorer:
    """IsolationForest fitted on normal data; p = percentile of the score among its training scores.
    Lives here, not in the training script, so a saved model loads in the app."""

    def __init__(self, X: np.ndarray, seed: int = 42):
        from sklearn.ensemble import IsolationForest
        self.m = IsolationForest(n_estimators=200, random_state=seed, n_jobs=-1).fit(X)
        self.m.set_params(n_jobs=1)
        self.ref = np.sort(-self.m.score_samples(X))

    def predict_p(self, X: np.ndarray) -> np.ndarray:
        return np.searchsorted(self.ref, -self.m.score_samples(X)) / len(self.ref)


if __name__ == "__main__":
    from failover.ml import data_metropt as dm
    d = dm.load()
    h, e = np.histogram(d["Motor_current"].to_numpy(), bins=np.arange(0, 10.5, 0.5))
    for a, c in zip(e, h):
        print(f"{a:4.1f}-{a + 0.5:4.1f} A {c:9d}")
    print(f"loaded threshold {LOADED_A} A")
