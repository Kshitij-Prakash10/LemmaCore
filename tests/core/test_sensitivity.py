import json

from failover.core.sensitivity import PARAMS, run_sensitivity


def test_sensitivity_file(tmp_path):
    data = run_sensitivity(None, str(tmp_path))
    assert (tmp_path / "sensitivity.json").exists()
    assert len(data["cases"]) == 3
    for c in data["cases"]:
        assert len(c["parameters"]) == len(PARAMS)
        swings = [p["swing_minutes"] for p in c["parameters"]]
        assert swings == sorted(swings, reverse=True)
        assert c["nominal_minutes"] >= 0
    json.loads((tmp_path / "sensitivity.json").read_text())
