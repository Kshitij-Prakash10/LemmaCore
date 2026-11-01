"""Optional leak flag: missing model leaves advice unchanged; a confident flag only shortens the air clock."""
import os

import pytest

from failover.app import backend
from failover.ml import leak_detector

HARD = {"faults": ["COMPRESSOR_FAIL"], "ambient_c": 45, "gradient_pct": 2.7}


def test_missing_model_gives_identical_advice(monkeypatch):
    base = backend.run_case(HARD)["advice"]
    monkeypatch.setattr(leak_detector, "MODEL_PATH", "/nonexistent/leak_model.joblib")
    leak_detector._cache.clear()
    out = backend.run_case({**HARD, "leak_features": [0.0] * 15})
    assert out["advice"] == base and out["leak"]["p"] is None and out["leak"]["line"] is None


def test_bad_input_returns_none():
    assert leak_detector.predict_proba(None) is None
    assert leak_detector.predict_proba([1.0, 2.0]) is None
    assert leak_detector.predict_proba(["x"] * 15) is None


def test_flag_never_lengthens_air_time(monkeypatch):
    base = backend.run_case(HARD)["advice"]
    monkeypatch.setattr(leak_detector, "predict_proba", lambda row: 0.9)
    out = backend.run_case({**HARD, "leak_features": [0.0] * 15})
    assert out["leak"]["line"].startswith("Air leak suspected (model p=0.90)")
    assert out["advice"]["minutes_left_p5"] <= base["minutes_left_p5"]


@pytest.mark.skipif(not os.path.exists(leak_detector.MODEL_PATH), reason="run train_leak")
def test_model_returns_probability():
    p = leak_detector.predict_proba([0.0] * 15)
    assert p is not None and 0.0 <= p <= 1.0
