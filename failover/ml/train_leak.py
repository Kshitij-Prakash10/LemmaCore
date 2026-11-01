"""Supervised air-leak flag on MetroPT-3 (real metro compressor data, proxy). Optional input to the app.

Time-based split: train before 2020-07-01 (leaks 1-3), test from 2020-07-01 (leak 4 held out).
Writes models/leak_model.joblib, models/leak_metrics.json, models/leak_test_period.svg,
data/processed/leak_replay.json. CLI: python -m failover.ml.train_leak
"""
from __future__ import annotations

import json
import os

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

from failover.ml import data_metropt as dm

SIGNALS = ["TP2", "TP3", "H1", "DV_pressure", "Reservoirs", "Motor_current", "Oil_temperature"]
SPLIT = pd.Timestamp("2020-07-01")
ROLL = 10  # minutes
MODEL = os.path.join(dm.ROOT, "models", "leak_model.joblib")
METRICS = os.path.join(dm.ROOT, "models", "leak_metrics.json")
PLOT = os.path.join(dm.ROOT, "models", "leak_test_period.svg")
REPLAY = os.path.join(dm.ROOT, "data", "processed", "leak_replay.json")


def feature_names() -> list[str]:
    """Order of the feature row."""
    return [f"{s}_{k}" for s in SIGNALS for k in ("mean10", "std10")] + ["COMP_mean10"]


def features(minute: pd.DataFrame) -> pd.DataFrame:
    """Rolling 10 min mean and std of each signal and 10 min compressor duty, from 1 min means."""
    r = minute.rolling(ROLL, min_periods=ROLL)
    cols = {}
    for s in SIGNALS:
        cols[f"{s}_mean10"] = r[s].mean()
        cols[f"{s}_std10"] = r[s].std()
    cols["COMP_mean10"] = r["COMP"].mean()
    return pd.DataFrame(cols)[feature_names()].dropna()


def labels(index: pd.DatetimeIndex) -> np.ndarray:
    """1 inside a labelled air-leak window, else 0."""
    y = np.zeros(len(index), dtype=int)
    for f in dm.failures():
        y[(index >= f["start"]) & (index <= f["end"])] = 1
    return y


def _svg(t: pd.DatetimeIndex, pres: np.ndarray, prob: np.ndarray, f4: dict) -> str:
    W, H, L, R, T, B = 900, 320, 50, 50, 20, 30
    n = len(t)
    X = lambda i: L + i / max(1, n - 1) * (W - L - R)  # noqa: E731
    plo, phi = float(np.nanmin(pres)), float(np.nanmax(pres))
    Yp = lambda v: T + (1 - (v - plo) / (phi - plo + 1e-9)) * (H - T - B)  # noqa: E731
    Yq = lambda v: T + (1 - v) * (H - T - B)  # noqa: E731
    idx = np.where((t >= f4["start"]) & (t <= f4["end"]))[0]
    step = max(1, n // 2000)
    pts = lambda ys, f: " ".join(f"{X(i):.1f},{f(ys[i]):.1f}" for i in range(0, n, step))  # noqa: E731
    shade = (f'<rect x="{X(idx[0]):.1f}" y="{T}" width="{max(2, X(idx[-1]) - X(idx[0])):.1f}" '
             f'height="{H - T - B}" fill="#d23c3c" fill-opacity="0.2"/>') if len(idx) else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" font-family="sans-serif" font-size="11">'
            f'<rect width="{W}" height="{H}" fill="#fff"/>{shade}'
            f'<polyline fill="none" stroke="#555" stroke-width="1" points="{pts(pres, Yp)}"/>'
            f'<polyline fill="none" stroke="#1f6fd1" stroke-width="1" points="{pts(prob, Yq)}"/>'
            f'<line x1="{L}" x2="{W - R}" y1="{Yq(0.5):.1f}" y2="{Yq(0.5):.1f}" stroke="#000" stroke-dasharray="5,4"/>'
            f'<text x="{L}" y="14">MetroPT-3 test period from 2020-07-01: Reservoirs pressure (grey, bar), leak probability '
            f'(blue, 0-1), threshold 0.5 (dashed), labelled leak 4 (shaded)</text>'
            f'<text x="{L}" y="{H - 8}">{t[0]:%Y-%m-%d}</text><text x="{W - R - 60}" y="{H - 8}">{t[-1]:%Y-%m-%d}</text></svg>')


def main() -> dict:
    """Train, evaluate on the held-out leak, save model, metrics, plot and replay."""
    raw = dm.load()[SIGNALS + ["COMP"]]
    minute = raw.resample("1min").mean()
    X = features(minute)
    y = labels(X.index)
    tr, te = X.index < SPLIT, X.index >= SPLIT
    model = RandomForestClassifier(n_estimators=100, max_depth=8, class_weight="balanced",
                                   random_state=42, n_jobs=-1).fit(X[tr].to_numpy(), y[tr])
    model.set_params(n_jobs=1)
    prob = model.predict_proba(X[te].to_numpy())[:, 1]
    alert = prob > 0.5
    yt = y[te]
    ti = X.index[te]
    f4 = dm.failures()[3]
    in4 = (ti >= f4["start"]) & (ti <= f4["end"])
    first = ti[in4 & alert]
    out_alerts = alert & (yt == 0)
    # alert episodes outside the leak: a new episode starts after a gap of more than 10 min
    ep_t = ti[out_alerts]
    n_eps = int(1 + (np.diff(ep_t.values).astype("timedelta64[m]").astype(int) > 10).sum()) if len(ep_t) else 0
    days = (ti[-1] - ti[0]).total_seconds() / 86400
    metrics = {
        "data": "MetroPT-3 (metro compressor, Porto): proxy, not a loco. Labels: the four air-leak windows.",
        "model": "RandomForestClassifier(n_estimators=100, max_depth=8, class_weight=balanced, random_state=42)",
        "features": "1 min means; rolling 10 min mean and std of 7 signals; rolling 10 min COMP duty",
        "split": "time-based: train before 2020-07-01 (leaks 1-3), test from 2020-07-01 (leak 4 held out)",
        "n_train_minutes": int(tr.sum()), "n_test_minutes": int(te.sum()),
        "leak4_recall": round(float(alert[in4].mean()), 3) if in4.any() else None,
        "precision": round(float((alert & (yt == 1)).sum() / alert.sum()), 3) if alert.any() else None,
        "false_alarm_minutes_outside_leak": int(out_alerts.sum()),
        "false_alarm_episodes_per_day": round(n_eps / days, 3),
        "minutes_to_first_alert_in_leak4": round((first[0] - f4["start"]).total_seconds() / 60, 1) if len(first) else None,
        "threshold": 0.5, "test_days": round(days, 1),
    }
    joblib.dump({"model": model, "features": feature_names()}, MODEL, compress=3)
    with open(METRICS, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=1)
    pres = minute["Reservoirs"].reindex(ti).to_numpy()
    with open(PLOT, "w", encoding="utf-8") as f:
        f.write(_svg(ti, pres, prob, f4))
    # replay: leak 4 with 2 h either side, 1 min steps, feature rows the app sends to the detector
    w = (ti >= f4["start"] - pd.Timedelta(hours=2)) & (ti <= f4["end"] + pd.Timedelta(hours=2))
    replay = {"label": "MetroPT-3 held-out leak 4 (2020-07-15 14:30 to 19:00), 2 h either side",
              "t": [str(x) for x in ti[w]], "reservoirs_bar": [round(float(v), 3) for v in pres[w]],
              "features": [[round(float(v), 5) for v in row] for row in X[te].to_numpy()[w]],
              "in_leak": [int(v) for v in in4[w]]}
    with open(REPLAY, "w", encoding="utf-8") as f:
        json.dump(replay, f)
    print(json.dumps(metrics, indent=1))
    return metrics


if __name__ == "__main__":
    main()
