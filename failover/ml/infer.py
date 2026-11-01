"""Inference API used by the app (CONTRACT.md section 4, ML interface)."""
from __future__ import annotations

import os
from functools import lru_cache

import joblib

from failover.ml.features import window_features

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MODEL_PATH = os.path.join(ROOT, "models", "fault_clf.joblib")
LOW_CONFIDENCE = 0.6


@lru_cache(maxsize=1)
def _bundle() -> dict:
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(MODEL_PATH)
    return joblib.load(MODEL_PATH)


def diagnose(observed_window: dict[str, list[float]]) -> dict:
    """{"faults": {fault_id: probability}, "predicted": [...], "confidence": float, "low_confidence": bool}.
    confidence is the least certain per-fault decision, max(p, 1 - p), over all faults."""
    from failover.ml.train_fault_clf import predict_proba

    b = _bundle()
    p = predict_proba(b["model"], window_features(observed_window).reshape(1, -1))[0]
    probs = {f: round(float(x), 3) for f, x in zip(b["faults"], p)}
    conf = float(min(max(x, 1 - x) for x in p))
    return {"faults": probs, "predicted": [f for f, x in probs.items() if x >= 0.5],
            "confidence": round(conf, 3), "low_confidence": conf < LOW_CONFIDENCE,
            "core_version": b["core_version"]}


def compressor_anomaly(window: dict[str, list[float]]) -> float:
    """Anomaly score for the MetroPT-3 demo. Not built yet."""
    raise NotImplementedError("anomaly detector not trained yet")


def minutes_left_p5(features: dict) -> float | None:
    """Surrogate (stretch). None: no model file, so the advisor uses physics only."""
    return None
