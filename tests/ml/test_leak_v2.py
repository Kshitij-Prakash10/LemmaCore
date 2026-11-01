"""Leak model v2: fallback chain, invalid data, and the air clock never gets more optimistic."""
import json
import os

import numpy as np
import pandas as pd
import pytest

from failover.app import backend
from failover.app.server import create_app
from failover.ml import leak_detector as ld
from failover.ml import leak_features as lf
from failover.ml import leak_rate

CASE = {"faults": ["COMPRESSOR_FAIL"], "ambient_c": 45, "gradient_pct": 2.7}
needs_v2 = pytest.mark.skipif(not os.path.exists(ld.MODEL_V2_PATH), reason="run train_leak_v2")


def _raw(minutes: int, reservoirs) -> pd.DataFrame:
    n = minutes * 6
    idx = pd.date_range("2020-03-01", periods=n, freq="10s")
    d = {s: np.full(n, 1.0) for s in lf.SIGNALS}
    d["Reservoirs"] = reservoirs(n)
    d["Motor_current"] = np.full(n, 0.1)
    d["COMP"] = np.ones(n)
    return pd.DataFrame(d, index=idx)


@pytest.fixture()
def no_models(monkeypatch):
    monkeypatch.setattr(ld, "MODEL_PATH", "/nonexistent/v1.joblib")
    monkeypatch.setattr(ld, "MODEL_V2_PATH", "/nonexistent/v2.joblib")
    ld._cache.clear()
    yield
    ld._cache.clear()


def test_app_works_with_no_model_files(no_models):
    base = backend.run_case(CASE)["advice"]
    out = backend.run_case({**CASE, "leak_replay_i": 5, "leak_features": [0.0] * 15})
    assert out["advice"] == base and out["leak"]["line"] is None and out["leak"]["source"] is None
    c = create_app().test_client()
    assert c.get("/evidence").status_code == 200
    assert c.get("/api/evidence").get_json() is not None


def test_bad_v2_model_falls_back_without_error(monkeypatch):
    monkeypatch.setattr(ld, "_bundle_v2", lambda: (_ for _ in ()).throw(RuntimeError("corrupt")))
    monkeypatch.setattr(ld, "predict_proba", lambda row: None)
    assert ld.assess({"leak_replay_i": 1}) is None


def test_invalid_minutes_never_alarm():
    p = np.ones(50)
    assert not lf.alarm(p, np.zeros(50, dtype=bool), 0.5).any()
    assert lf.alarm(p, np.ones(50, dtype=bool), 0.5).any()


def test_flat_and_missing_data_are_invalid():
    flat = lf.features(lf.to_minutes(_raw(120, lambda n: np.full(n, 8.0))))
    assert not flat["valid"].iloc[-1]
    raw = _raw(120, lambda n: 8.0 + 0.5 * np.sin(np.arange(n) / 30.0))
    assert lf.features(lf.to_minutes(raw))["valid"].iloc[-1]
    gap = raw.drop(raw.index[-40 * 6:-10 * 6])  # 30 of the last 60 minutes missing
    assert not lf.features(lf.to_minutes(gap))["valid"].iloc[-1]


def test_no_off_period_is_not_invalid():
    raw = _raw(120, lambda n: 8.0 + 0.5 * np.sin(np.arange(n) / 30.0))
    raw["Motor_current"] = 5.5
    f = lf.features(lf.to_minutes(raw)).iloc[-1]
    assert f["valid"] and f["cycles_per_h"] == 0.0


@needs_v2
def test_invalid_window_gives_no_flag_and_cautious_line():
    raw = _raw(120, lambda n: np.full(n, 8.0))
    win = {"timestamp": [str(t) for t in raw.index], **{c: raw[c].tolist() for c in raw.columns}}
    res = ld.assess({"leak_window": win})
    assert res["source"] == "v2" and res["valid"] is False and res["flag"] is False
    out = backend.run_case({**CASE, "leak_window": win})
    assert out["leak"]["line"] == "compressor data invalid - using cautious air estimate"
    assert out["advice"]["minutes_left_p5"] <= backend.run_case(CASE)["advice"]["minutes_left_p5"]


@pytest.mark.parametrize("rate", [0.001, 0.05, 0.3, 2.0])
def test_leak_rate_never_more_optimistic(monkeypatch, rate):
    base = backend.run_case(CASE)["advice"]
    monkeypatch.setattr(ld, "assess", lambda req: {"source": "v2", "valid": True, "flag": True, "p": 0.999, "rate": rate,
                                                   "normal_rate": 0.09, "explain": []})
    out = backend.run_case(CASE)
    assert out["advice"]["minutes_left_p5"] <= base["minutes_left_p5"]
    assert out["advice"]["minutes_left_nominal"] <= base["minutes_left_nominal"]
    assert out["leak"]["line"].startswith("Air leak suspected - reservoir falling")


def test_flag_without_rate_uses_multiplier(monkeypatch):
    monkeypatch.setattr(ld, "assess", lambda req: {"source": "v2", "valid": True, "flag": True, "p": 0.999, "rate": None,
                                                   "normal_rate": 0.09, "explain": []})
    out = backend.run_case(CASE)
    assert out["leak"]["line"] == "Air leak suspected (model p=1.00) - air limit shortened"


def test_leak_rate_estimate():
    raw = _raw(30, lambda n: 9.0 - 0.1 * np.arange(n) / 6.0)
    r = leak_rate.estimate(lf.to_minutes(raw))
    assert abs(r["bar_per_min"] - 0.1) < 1e-3 and r["confidence"] == "high"
    loaded = lf.to_minutes(raw.assign(Motor_current=5.5))
    assert leak_rate.estimate(loaded) is None
    assert leak_rate.estimate(None) is None


@needs_v2
def test_replay_alarm_reaches_card():
    with open(ld.REPLAY_V2_PATH, encoding="utf-8") as f:
        r = json.load(f)
    i = r["alarm"].index(True)
    out = backend.run_case({**CASE, "leak_replay_i": i})
    assert out["leak"]["flag"] and out["leak"]["line"].startswith("Air leak suspected")
    assert len(out["leak"]["explain"]) == 3


def test_external_test_skips_cleanly(tmp_path, monkeypatch):
    from failover.ml import external_test as et
    monkeypatch.setattr(et, "CANDIDATES", [str(tmp_path / "absent.csv")])
    monkeypatch.setattr(et, "OUT", str(tmp_path / "ext.json"))
    assert et.main()["available"] is False
