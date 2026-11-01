"""Isolation Forest anomaly detector on MetroPT-3 (real compressor data, proxy).

Train: February 2020 (normal, first month). Threshold: March 2020 (no labelled failures), set to a fixed
false-alarm budget. Test: 1 April onwards, which holds all four labelled air-leak events.
Writes models/anomaly.joblib, models/anomaly_metrics.json, data/processed/anomaly_demo.json.
CLI: python -m failover.ml.train_anomaly
"""
from __future__ import annotations

import json
import os

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from failover.ml import data_metropt as dm

SEED = 13
BIN = "5min"
SMOOTH_BINS = 6            # trailing median over 30 min, so no future data is used
VAL_QUANTILE = 0.999       # alarm threshold: 99.9th percentile of the smoothed March score
LOOKBACK = pd.Timedelta(hours=24)  # an alarm up to 24 h before a failure counts as early warning
MODEL = os.path.join(dm.ROOT, "models", "anomaly.joblib")
METRICS = os.path.join(dm.ROOT, "models", "anomaly_metrics.json")
DEMO = os.path.join(dm.ROOT, "data", "processed", "anomaly_demo.json")
TRAIN = ("2020-02-01", "2020-03-01")
VAL = ("2020-03-01", "2020-04-01")
TEST_FROM = "2020-04-01"
BUDGETS = (0.95, 0.99, 0.995, 0.999)


def bin_features(df: pd.DataFrame) -> pd.DataFrame:
    """Per 5 min bin: mean, std, max - min of each analog signal, and the mean of each digital signal."""
    g = df.groupby(df.index.floor(BIN))
    a = g[dm.ANALOG]
    parts = [a.mean().add_suffix("_mean"), a.std().fillna(0).add_suffix("_std"),
             (a.max() - a.min()).add_suffix("_range"), g[dm.DIGITAL].mean().add_suffix("_frac")]
    out = pd.concat(parts, axis=1)
    return out[g.size() >= 10]  # drop bins with large gaps


def window_features(window: dict[str, list[float]]) -> np.ndarray:
    """Same features from one window of raw rows (dict of signal -> values)."""
    df = pd.DataFrame({k: np.asarray(window.get(k, [0.0]), float) for k in dm.ANALOG + dm.DIGITAL})
    vals = ([df[c].mean() for c in dm.ANALOG] + [df[c].std(ddof=1) if len(df) > 1 else 0.0 for c in dm.ANALOG]
            + [df[c].max() - df[c].min() for c in dm.ANALOG] + [df[c].mean() for c in dm.DIGITAL])
    return np.nan_to_num(np.asarray(vals, float)).reshape(1, -1)


def episodes(alarm: pd.Series) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    """Contiguous runs of alarm bins (a gap over one bin ends a run)."""
    ts = alarm[alarm].index
    if len(ts) == 0:
        return []
    runs, start, prev = [], ts[0], ts[0]
    for t in ts[1:]:
        if t - prev > pd.Timedelta(BIN) * 2:
            runs.append((start, prev))
            start = t
        prev = t
    runs.append((start, prev))
    return runs


def main() -> dict:
    """Train, threshold, test, save."""
    feats = bin_features(dm.load())
    train = feats.loc[TRAIN[0]:TRAIN[1]].iloc[:-1]
    model = IsolationForest(n_estimators=200, random_state=SEED).fit(train.to_numpy())
    score = pd.Series(-model.score_samples(feats.to_numpy()), index=feats.index)
    smooth = score.rolling(SMOOTH_BINS, min_periods=1).median()
    thr = float(smooth.loc[VAL[0]:VAL[1]].iloc[:-1].quantile(VAL_QUANTILE))

    test = smooth.loc[TEST_FROM:]
    alarm = test > thr
    fails = dm.failures()
    in_warn = pd.Series(False, index=test.index)
    in_fail = pd.Series(False, index=test.index)
    events = []
    for f in fails:
        w = (test.index >= f["start"] - LOOKBACK) & (test.index <= f["end"])
        in_warn |= w
        in_fail |= (test.index >= f["start"]) & (test.index <= f["end"])
        hits = test.index[w & alarm.to_numpy()]
        first = hits[0] if len(hits) else None
        events.append({"nr": f["nr"], "start": str(f["start"]), "end": str(f["end"]), "detected": first is not None,
                       "first_alarm": str(first) if first is not None else None,
                       "lead_time_h": round((f["start"] - first).total_seconds() / 3600, 2) if first is not None else None})
    eps = episodes(alarm)
    false_eps = [e for e in eps if not in_warn.loc[e[0]:e[1]].any()]
    days = (test.index[-1] - test.index[0]).total_seconds() / 86400
    n_alarm = int(alarm.sum())
    metrics = {
        "data": "MetroPT-3, real compressor data from a metro train in Porto (proxy, not a loco)",
        "model": f"IsolationForest(200 trees, seed {SEED}) on {BIN} bin features, {SMOOTH_BINS}-bin trailing median",
        "train": list(TRAIN), "threshold_set_on": list(VAL), "test_from": TEST_FROM,
        "threshold": round(thr, 4), "false_alarm_budget": f"{VAL_QUANTILE} quantile of the smoothed March score",
        "events_detected": f"{sum(e['detected'] for e in events)} of {len(events)}",
        "events": events,
        "alarm_bin_precision": round(float((alarm & in_warn).sum() / n_alarm), 3) if n_alarm else None,
        "failure_bin_recall": round(float((alarm & in_fail).sum() / in_fail.sum()), 3) if in_fail.any() else None,
        "false_alarm_episodes": len(false_eps),
        "false_alarm_episodes_per_day": round(len(false_eps) / days, 3),
        "test_days": round(days, 1),
        "note": "Precision counts alarm bins inside [failure start - 24 h, failure end]. Lead time is hours "
                "from the first such alarm to the failure start (positive = before).",
    }
    # sensitivity: other budgets fixed in advance, all reported, none chosen on the test months
    val = smooth.loc[VAL[0]:VAL[1]].iloc[:-1]
    table = []
    for q in BUDGETS:
        th = float(val.quantile(q))
        al = test > th
        det = 0
        for f in fails:
            w = (test.index >= f["start"] - LOOKBACK) & (test.index <= f["end"])
            det += bool((al.to_numpy() & w).any())
        fe = [e for e in episodes(al) if not in_warn.loc[e[0]:e[1]].any()]
        table.append({"val_quantile": q, "threshold": round(th, 4), "events_detected": det,
                      "false_alarm_episodes_per_day": round(len(fe) / days, 3),
                      "alarm_bin_precision": round(float((al & in_warn).sum() / al.sum()), 3) if al.any() else None})
    metrics["budget_table"] = table
    metrics["score_median_inside_failures"] = round(float(test[in_fail].median()), 4)
    metrics["score_median_outside_warning_windows"] = round(float(test[~in_warn].median()), 4)
    metrics["score_p99_outside_warning_windows"] = round(float(test[~in_warn].quantile(0.99)), 4)
    hourly = test.resample("1h").max().dropna()
    fidx = []
    for f in fails:
        pos = np.where((hourly.index >= f["start"]) & (hourly.index <= f["end"]))[0]
        if len(pos):
            fidx.append([int(pos[0]), int(pos[-1])])
    demo = {"label": "MetroPT-3 anomaly score, hourly max (shaded: labelled air leaks, dashed: alarm threshold)",
            "t": [str(t) for t in hourly.index], "score": [round(float(x), 4) for x in hourly],
            "threshold": round(thr, 4), "failure_idx": fidx}
    os.makedirs(os.path.dirname(MODEL), exist_ok=True)
    joblib.dump({"model": model, "threshold": thr, "features": list(feats.columns)}, MODEL, compress=3)
    for path, obj in ((METRICS, metrics), (DEMO, demo)):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=1)
    print(json.dumps({k: v for k, v in metrics.items() if k not in ("note",)}, indent=1))
    return metrics


if __name__ == "__main__":
    main()
