import json
import os

from failover.core.config import load_config
from failover.core.harness import enumerate_cases, fault_sets, run_harness

CFG = load_config()


def test_case_counts():
    assert len(fault_sets()) == 36
    assert len(enumerate_cases(CFG)) == 144


def test_small_harness_run(tmp_path):
    cov = run_harness(CFG, str(tmp_path), n_mc=20, workers=1, max_cases=8)
    for name in ("coverage.json", "runs.csv", "report.html"):
        assert os.path.exists(tmp_path / name)
    data = json.loads((tmp_path / "coverage.json").read_text())
    assert data["summary"]["runs_per_policy"] == 8
    case = data["cases"][0]
    assert {"case_id", "faults", "condition", "baseline", "advisor", "properties_ok"} <= set(case)
    assert {"outcome", "limit_hit", "t_limit_s", "reached_station"} <= set(case["baseline"])
    assert {"outcome", "decision", "shed", "limiting_factor", "minutes_left_p5"} <= set(case["advisor"])
    assert cov["core_version"]
