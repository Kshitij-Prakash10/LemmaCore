"""Bad input to the API answers 400 with a JSON error, never a 500 or a silently wrong scenario."""
import pytest

from failover.app.server import create_app


@pytest.fixture()
def client():
    return create_app().test_client()


@pytest.mark.parametrize("body", [
    {"units": 0}, {"units": 2.5}, {"units": "x"}, {"ambient_c": "abc"}, {"ambient_c": True},
    {"speed_kmph": 0}, {"dist_next_station_km": -1}, {"train_load": "heavy"}, {"seed": "x"},
    {"faults": ["NOT_A_FAULT"]}, {"faults": [None]}, {"faults": 3}, {"params": "x"}, {"params": {"leak": "x"}},
    [1, 2], "text",
])
def test_advise_rejects_bad_input(client, body):
    r = client.post("/api/advise", json=body)
    assert r.status_code == 400
    assert r.get_json()["error"]


def test_advise_rejects_invalid_json(client):
    r = client.post("/api/advise", data="{not json", content_type="application/json")
    assert r.status_code == 400 and "error" in r.get_json()


def test_single_fault_string_is_one_fault(client):
    body = client.post("/api/advise", json={"faults": "STANDBY_STUCK"}).get_json()
    assert body["scenario"]["faults"] == ["STANDBY_STUCK"]


def test_empty_body_uses_defaults(client):
    assert client.post("/api/advise").status_code == 200


@pytest.mark.parametrize("units", [1, 2, 3])
def test_every_unit_count_runs(client, units):
    r = client.post("/api/advise", json={"units": units, "faults": ["U1_TRIP", "STANDBY_STUCK"]})
    assert r.status_code == 200


@pytest.mark.parametrize("body", [[1], {"observed": {"motor_temp_c": ["a"]}}, {"observed": "x"}])
def test_diagnose_rejects_bad_input(client, body):
    r = client.post("/api/diagnose", json=body)
    assert r.status_code == 400 and r.get_json()["error"]


def test_diagnose_empty_window_is_not_a_diagnosis(client):
    out = client.post("/api/diagnose", json={"observed": {}}).get_json()
    assert out["available"] is False


def test_api_404_and_405_are_json(client):
    assert client.get("/api/nope").get_json()["error"]
    r = client.get("/api/advise")
    assert r.status_code == 405 and r.get_json()["error"]


def test_wsgi_entry_point():
    from failover.app import server
    assert server.app.name and callable(server.app.wsgi_app)


def test_vercel_entry_point_serves_pages():
    import importlib.util
    import json
    import os

    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    spec = importlib.util.spec_from_file_location("vercel_index", os.path.join(root, "api", "index.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    c = mod.app.test_client()
    assert c.get("/").status_code == 200 and c.get("/api/status").status_code == 200
    with open(os.path.join(root, "vercel.json"), encoding="utf-8") as f:
        assert json.load(f)["rewrites"][0]["destination"] == "/api/index"
