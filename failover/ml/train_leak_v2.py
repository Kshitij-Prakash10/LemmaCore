"""Air-leak model v2: leave-one-event-out CV over E1-E4, RandomForest vs IsolationForest, alarm rule 7 of 10 minutes.

Writes models/leak_model_v2.joblib, models/leak_v2_metrics.json, models/leak_v2_cv_table.csv,
models/leak_v2_importance.svg, data/processed/leak_replay_v2.json. The v1 model is untouched (fallback).
CLI: python -m failover.ml.train_leak_v2
"""
from __future__ import annotations

import json
import os

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import average_precision_score

from failover.ml import data_metropt as dm
from failover.ml import leak_features as lf
from failover.ml import leak_rate
from failover.ml.leak_features import IFScorer

SEED = 42
BLOCK = pd.Timedelta(days=3)    # test block: event +- 3 days
GUARD = pd.Timedelta(days=1)    # extra gap between test block and training data
EARLY = pd.Timedelta(hours=2)   # an alert up to 2 h before the start counts as a detection
THETAS = (0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99, 0.995, 0.999)
OUT = os.path.join(dm.ROOT, "models")
MODEL = os.path.join(OUT, "leak_model_v2.joblib")
METRICS = os.path.join(OUT, "leak_v2_metrics.json")
CV_TABLE = os.path.join(OUT, "leak_v2_cv_table.csv")
IMPORTANCE = os.path.join(OUT, "leak_v2_importance.svg")
REPLAY = os.path.join(dm.ROOT, "data", "processed", "leak_replay_v2.json")


def labels(index: pd.DatetimeIndex) -> np.ndarray:
    y = np.zeros(len(index), dtype=int)
    for f in dm.failures():
        y[(index >= f["start"]) & (index <= f["end"])] = 1
    return y


def rf() -> RandomForestClassifier:
    return RandomForestClassifier(n_estimators=100, max_depth=8, class_weight="balanced", random_state=SEED, n_jobs=-1)


def fold_result(ti: pd.DatetimeIndex, p: np.ndarray, valid: np.ndarray, ev: dict, theta: float) -> dict:
    """Detection, minutes to first alert and false-alarm episodes per day in one test block."""
    a = lf.alarm(p, valid, theta)
    win = (ti >= ev["start"] - EARLY) & (ti <= ev["end"])
    first = ti[a & win]
    out = a & ~win
    starts = out & ~np.concatenate([[False], out[:-1]])
    days = (valid & ~win).sum() / 1440
    in_ev = (ti >= ev["start"]) & (ti <= ev["end"])
    return {"detected": bool(len(first)),
            "alert_share_of_event": round(float(a[in_ev].mean()), 3) if in_ev.any() else None,
            "minutes_to_first_alert": round((first[0] - ev["start"]).total_seconds() / 60, 1) if len(first) else None,
            "false_alarms_per_day": round(float(starts.sum() / days), 3) if days else None}


def _svg_bars(names: list[str], vals: list[float]) -> str:
    W, row, L = 640, 24, 230
    H = 40 + row * len(names)
    vmax = max(max(vals), 1e-9)
    bars = "".join(
        f'<text x="{L - 6}" y="{36 + i * row}" text-anchor="end">{n}</text>'
        f'<rect x="{L}" y="{24 + i * row}" width="{max(1, (W - L - 60) * max(v, 0) / vmax):.1f}" height="16" fill="#1f6fd1"/>'
        f'<text x="{L + 6 + (W - L - 60) * max(v, 0) / vmax:.1f}" y="{36 + i * row}">{v:.3f}</text>'
        for i, (n, v) in enumerate(zip(names, vals)))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" font-family="sans-serif" font-size="12">'
            f'<rect width="{W}" height="{H}" fill="#fff"/><text x="10" y="16">Permutation importance, held-out folds '
            f'(drop in average precision), top 10</text>{bars}</svg>')


def main() -> dict:
    minute = lf.to_minutes(dm.load())
    F = lf.features(minute)
    names = lf.feature_names()
    X, valid, ti = F[names].to_numpy(float), F["valid"].to_numpy(), F.index
    y = labels(ti)
    events = dm.failures()
    e1 = events[0]["start"]
    if_train = valid & (ti < e1 - GUARD)
    rng = np.random.default_rng(SEED)
    idx_if = rng.choice(np.where(if_train)[0], size=min(60000, int(if_train.sum())), replace=False)
    iso = IFScorer(X[idx_if])

    preds: dict[str, dict[int, tuple]] = {"RandomForest": {}, "IsolationForest": {}}
    fold_models = {}
    for ev in events:
        test = (ti >= ev["start"] - BLOCK) & (ti <= ev["end"] + BLOCK)
        train = valid & ~((ti >= ev["start"] - BLOCK - GUARD) & (ti <= ev["end"] + BLOCK + GUARD))
        m = rf().fit(X[train], y[train])
        m.set_params(n_jobs=1)
        fold_models[ev["nr"]] = m
        preds["RandomForest"][ev["nr"]] = (test, m.predict_proba(X[test])[:, 1])
        preds["IsolationForest"][ev["nr"]] = (test, iso.predict_p(X[test]))

    rows, chosen = [], {}
    for model_name, by_ev in preds.items():
        best = None
        for th in THETAS:
            res = [fold_result(ti[t], p, valid[t], ev, th) for ev in events for t, p in [by_ev[ev["nr"]]]]
            det = sum(r["detected"] for r in res)
            fa = float(np.mean([r["false_alarms_per_day"] or 0 for r in res]))
            if best is None or (det, -fa) > (best[1], -best[2]):
                best = (th, det, fa, res)
        chosen[model_name] = {"theta": best[0], "events_detected": best[1], "mean_false_alarms_per_day": round(best[2], 3)}
        for ev, r in zip(events, best[3]):
            rows.append({"model": model_name, "theta": best[0], "held_out_event": f"E{ev['nr']}", **r})
    table = pd.DataFrame(rows)
    table.to_csv(CV_TABLE, index=False)

    winner = max(chosen, key=lambda k: (chosen[k]["events_detected"], -chosen[k]["mean_false_alarms_per_day"]))
    theta = chosen[winner]["theta"]
    final = rf().fit(X[valid], y[valid])
    final.set_params(n_jobs=1)
    normal = valid & (y == 0)
    bundle = {"kind": winner, "theta": theta, "features": names,
              "normal_mean": X[normal].mean(axis=0).tolist(), "normal_std": X[normal].std(axis=0).tolist(),
              "normal_decay_bar_per_min": float(np.median(F.loc[normal & (F["decay_bar_per_min"] > 0).to_numpy(),
                                                              "decay_bar_per_min"]))}
    bundle["model"] = final if winner == "RandomForest" else iso
    joblib.dump(bundle, MODEL, compress=3)

    # permutation importance of the chosen model, on each held-out block (drop in average precision)
    imps = []
    for ev in events:
        test = (ti >= ev["start"] - BLOCK) & (ti <= ev["end"] + BLOCK)
        score = iso.predict_p if winner == "IsolationForest" else (lambda A, m=fold_models[ev["nr"]]: m.predict_proba(A)[:, 1])
        tv = np.where(test & valid)[0]
        pos, neg = tv[y[tv] == 1], tv[y[tv] == 0]
        sub = np.concatenate([pos, rng.choice(neg, size=min(3000, len(neg)), replace=False)])
        Xs, ys = X[sub].copy(), y[sub]
        base = average_precision_score(ys, score(Xs))
        drops = []
        for j in range(Xs.shape[1]):
            keep = Xs[:, j].copy()
            d = []
            for _ in range(2):
                Xs[:, j] = rng.permutation(keep)
                d.append(base - average_precision_score(ys, score(Xs)))
            Xs[:, j] = keep
            drops.append(float(np.mean(d)))
        imps.append(drops)
    imp = np.mean(imps, axis=0)
    order = np.argsort(imp)[::-1][:10]
    with open(IMPORTANCE, "w", encoding="utf-8") as f:
        f.write(_svg_bars([names[i] for i in order], [float(imp[i]) for i in order]))

    # replay of held-out E4: p from the fold model that never saw E4
    e4 = events[3]
    test, p4 = preds[winner][4]
    w = (ti[test] >= e4["start"] - pd.Timedelta(hours=3)) & (ti[test] <= e4["end"] + pd.Timedelta(hours=2))
    tt, pv, vv = ti[test][w], p4[w], valid[test][w]
    al = lf.alarm(p4, valid[test], theta)[w]
    rates = []
    for t in tt:
        r = leak_rate.estimate(minute.loc[t - pd.Timedelta(minutes=30):t])
        rates.append(r["bar_per_min"] if r is not None and r["confidence"] == "high" else None)
    replay = {"label": f"MetroPT-3 E4 (2020-07-15 14:30 to 19:00), held out: p from a {winner} that never saw E4",
              "t": [str(x) for x in tt], "p": [round(float(x), 4) for x in pv], "valid": [bool(x) for x in vv],
              "alarm": [bool(x) for x in al], "theta": theta,
              "reservoirs_bar": [round(float(x), 3) for x in minute["Reservoirs"].reindex(tt).fillna(0)],
              "leak_rate_bar_per_min": rates,
              "in_event": [bool(e4["start"] <= x <= e4["end"]) for x in tt],
              "features": [[round(float(v), 5) for v in row] for row in X[test][w]]}
    with open(REPLAY, "w", encoding="utf-8") as f:
        json.dump(replay, f)

    metrics = {
        "data": "MetroPT-3 (metro compressor, Porto; UCI, CC BY 4.0). Proxy, not a loco.",
        "features": "leak_features.py: 1 min means; 60 min cycles/h, run and off durations, decay and recharge "
                    "rates, load duty; 10 min mean/std of 7 signals. Loaded if motor current > 4.75 A.",
        "cv": "leave-one-event-out over E1-E4. Test block = event +- 3 days; training excludes a further 1 day guard.",
        "alarm_rule": "p > theta in >= 7 of the last 10 minutes; invalid minutes never alarm",
        "theta_note": "theta chosen on the same CV folds that are reported, so these numbers are optimistic",
        "isolation_forest": "fit only on valid data before E1 minus 1 day; p = percentile of its training scores",
        "chosen": chosen, "winner": winner, "theta": theta,
        "cv_table": rows,
        "importance_top10": {names[i]: round(float(imp[i]), 4) for i in order},
        "final_model": ("IsolationForest fit only on valid data before E1 (no labels, so 'trained on all four events' "
                        "does not apply); saved unchanged." if winner == "IsolationForest" else
                        "RandomForest on all valid minutes (all four events). It has no held-out test of its own."),
        "importance_of": winner,
        "false_alarm_note": "False alarms are measured only in the +-3 day blocks around events. For the "
                            "IsolationForest the block before E1 overlaps its training period.",
        "valid_fraction": round(float(valid.mean()), 3),
    }
    with open(METRICS, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=1)
    print(table.to_string(index=False))
    print(json.dumps(chosen, indent=1))
    return metrics


if __name__ == "__main__":
    main()
