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
