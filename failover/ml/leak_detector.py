"""Optional air-leak flag. Never raises: any problem returns None and the app behaves as if it did not exist."""
from __future__ import annotations

import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MODEL_PATH = os.path.join(ROOT, "models", "leak_model.joblib")
_cache: dict = {}


def predict_proba(feature_row: list[float] | None) -> float | None:
    """Leak probability 0..1 for one feature row (order: train_leak.feature_names()), or None."""
    try:
        if feature_row is None or not os.path.exists(MODEL_PATH):
            return None
        if "m" not in _cache:
            import joblib
            _cache["m"] = joblib.load(MODEL_PATH)
        b = _cache["m"]
        if len(feature_row) != len(b["features"]):
            return None
        return float(b["model"].predict_proba([list(map(float, feature_row))])[0][1])
    except Exception:
        return None


# ---------- v2: IsolationForest with alarm rule, data-quality check and leak rate ----------
MODEL_V2_PATH = os.path.join(ROOT, "models", "leak_model_v2.joblib")
REPLAY_V2_PATH = os.path.join(ROOT, "data", "processed", "leak_replay_v2.json")


def _bundle_v2() -> dict | None:
    if not os.path.exists(MODEL_V2_PATH):
        return None
    if "v2" not in _cache:
        import joblib
        _cache["v2"] = joblib.load(MODEL_V2_PATH)
    return _cache["v2"]


def explain(row, b: dict, top: int = 3) -> list[dict]:
    """Top features by absolute z-score against normal training minutes."""
    out = []
    for name, x, mu, sd in zip(b["features"], row, b["normal_mean"], b["normal_std"]):
        out.append({"feature": name, "value": round(float(x), 3), "z": round((float(x) - mu) / sd, 1) if sd > 0 else 0.0})
    return sorted(out, key=lambda d: abs(d["z"]), reverse=True)[:top]


def _score(b: dict, X):
    m = b["model"]
    return m.predict_p(X) if hasattr(m, "predict_p") else m.predict_proba(X)[:, 1]


def _from_window(window: dict, b: dict) -> dict:
    """Raw rows {"timestamp": [...], signal: [...]} -> flag, validity, rate, explanation."""
    import numpy as np
    import pandas as pd

    from failover.ml import leak_features as lf
    from failover.ml import leak_rate

    raw = pd.DataFrame(window)
    raw.index = pd.to_datetime(raw.pop("timestamp"))
    minute = lf.to_minutes(raw)
    F = lf.features(minute)
    X, valid = F[b["features"]].to_numpy(float), F["valid"].to_numpy()
    p = _score(b, X)
    flag = bool(lf.alarm(p, valid, b["theta"])[-1])
    r = leak_rate.estimate(minute)
    return {"valid": bool(valid[-1]), "flag": flag and bool(valid[-1]), "p": round(float(np.ravel(p)[-1]), 3),
            "rate": r["bar_per_min"] if r and r["confidence"] == "high" else None, "row": X[-1].tolist()}


def _from_replay(i: int, b: dict) -> dict:
    """One minute of the precomputed held-out replay (p from a model that never saw that event)."""
    import json

    if "replay" not in _cache:
        with open(REPLAY_V2_PATH, encoding="utf-8") as f:
            _cache["replay"] = json.load(f)
    r = _cache["replay"]
    return {"valid": r["valid"][i], "flag": r["alarm"][i] and r["valid"][i], "p": r["p"][i],
            "rate": r["leak_rate_bar_per_min"][i], "row": r["features"][i]}


def assess(req: dict) -> dict | None:
    """Fallback chain: v2 model, then v1 flag, then None (no ML). Never raises.
    Result: {"source", "valid", "flag", "p", "rate", "normal_rate", "explain"}."""
    try:
        b = _bundle_v2()
        if b is not None and (req.get("leak_window") is not None or req.get("leak_replay_i") is not None):
            res = _from_window(req["leak_window"], b) if req.get("leak_window") is not None \
                else _from_replay(int(req["leak_replay_i"]), b)
            row = res.pop("row")
            return {**res, "source": "v2", "normal_rate": round(b["normal_decay_bar_per_min"], 4),
                    "explain": explain(row, b) if res["flag"] else []}
    except Exception:
        pass
    p = predict_proba(req.get("leak_features"))
    if p is None:
        return None
    return {"source": "v1", "valid": True, "flag": p > 0.5, "p": round(p, 3), "rate": None,
            "normal_rate": None, "explain": []}
