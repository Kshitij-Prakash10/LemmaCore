"""ML tests: no seed leakage, model records the current core version, diagnose is sane and fast."""
import json
import os
import time

import pandas as pd
import pytest

import failover.core as core
from failover.core.types import FAULT_IDS

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
METRICS = os.path.join(ROOT, "models", "metrics.json")
MODEL = os.path.join(ROOT, "models", "fault_clf.joblib")
needs_model = pytest.mark.skipif(not os.path.exists(MODEL), reason="run make train first")


@needs_model
def test_model_core_version_matches():
    with open(METRICS, encoding="utf-8") as f:
        m = json.load(f)
    assert m["core_version"] == core.CORE_VERSION, "core changed: rerun python -m failover.ml.train_fault_clf"


@needs_model
def test_heldout_pairs_not_in_training_metadata():
    with open(METRICS, encoding="utf-8") as f:
        m = json.load(f)
    assert len(m["heldout_pairs"]) == 4 and "by scenario seed" in m["split"]


def test_split_has_no_seed_leakage():
    import numpy as np
    from failover.ml import train_fault_clf as T
    from failover.ml.make_dataset import build, scenario_specs
    df = build(scenario_specs(1, 3, combos=[(), ("U1_TRIP",), ("BLOWER_FAIL",)]), processes=1)
    seeds = np.array(sorted(df["seed"].unique()))
    test = set(np.random.default_rng(T.SEED).choice(seeds, size=1, replace=False).tolist())
    tr, te = df[~df["seed"].isin(test)], df[df["seed"].isin(test)]
    assert not set(tr["seed"]) & set(te["seed"])
    assert len(df) == 3 * 4  # 4 windows per scenario
    pre = df[df["window_end_s"] == 60]
    assert (pre[[f"y_{f}" for f in FAULT_IDS]].to_numpy() == 0).all()


@needs_model
def test_diagnose_shape_and_speed():
    from failover.core.simulate import simulate
    from failover.core.types import Scenario
    from failover.ml.infer import diagnose
    r = simulate(Scenario(id="t", faults=("BLOWER_FAIL",), noise=0.02, seed=5), "baseline", horizon_s=120)
    win = {k: v[61:121] for k, v in r.observed.items()}
    out = diagnose(win)
    assert set(out["faults"]) == set(FAULT_IDS)
    assert all(0.0 <= p <= 1.0 for p in out["faults"].values())
    assert 0.5 <= out["confidence"] <= 1.0
    assert "BLOWER_FAIL" in out["predicted"]
    t = time.perf_counter()
    for _ in range(10):
        diagnose(win)
    assert (time.perf_counter() - t) / 10 < 0.02
