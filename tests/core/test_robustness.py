import json

from failover.core.robustness import PARAMS, run_robustness


def test_robustness_small(tmp_path):
    d = run_robustness(None, str(tmp_path), workers=1, max_corners=2, max_cases=6, n_mc=20)
    assert d["n_corners"] == 2
    assert set(d["ranges_tested"]) == set(PARAMS)
    assert (tmp_path / "robustness.json").exists()
    row = d["corners"][0]
    assert {"baseline_unsafe", "advisor_unsafe", "false_stops", "advisor_optimistic_cases"} <= set(row)
    json.loads((tmp_path / "robustness.json").read_text())
