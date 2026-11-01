"""App tests: every endpoint returns valid JSON, and the app works with the network blocked."""
import socket

import pytest

from failover.app.server import create_app


@pytest.fixture()
def client(monkeypatch):
    def no_net(*args, **kwargs):
        raise RuntimeError("network access attempted")

    monkeypatch.setattr(socket.socket, "connect", no_net)
    monkeypatch.setattr(socket, "create_connection", no_net)
    return create_app().test_client()


def test_index_has_no_external_assets(client):
    html = client.get("/").get_data(as_text=True)
    assert "http://" not in html and "https://" not in html
    js = client.get("/static/app.js").get_data(as_text=True)
    assert "https://" not in js


@pytest.mark.parametrize("path", ["/api/status", "/api/config", "/api/coverage", "/api/anomaly-demo", "/api/metrics"])
def test_get_endpoints_json(client, path):
    r = client.get(path)
    assert r.status_code == 200
    assert r.get_json() is not None


def test_config_has_badges(client):
    rows = client.get("/api/config").get_json()["assumptions"]
    assert rows and all(r["status"] in ("assumed", "confirmed") for r in rows)


def test_coverage_shape(client):
    cov = client.get("/api/coverage").get_json()
    assert len(cov["cases"]) == 36 * 4
    assert {"baseline_unsafe", "advisor_unsafe", "runs_per_policy"} <= set(cov["summary"])


def test_advise_hard_case(client):
    r = client.post("/api/advise", json={"faults": ["U1_TRIP", "STANDBY_STUCK"], "ambient_c": 45, "gradient_pct": 2.7})
    body = r.get_json()
    assert r.status_code == 200
    a = body["advice"]
    assert a["decision"] in ("CONTINUE", "STOP_AT_NEXT", "STOP_NOW")
    assert a["minutes_left_p5"] >= 0
    assert len(body["chart"]["t_s"]) == len(body["chart"]["motor_temp_baseline"])


def test_advise_with_diagnose_and_stuck_sensor(client):
    r = client.post("/api/advise", json={"faults": ["BLOWER_FAIL"], "stick_temp": True, "diagnose": True})
    body = r.get_json()
    assert "TEMP_SENSOR_STUCK" in body["scenario"]["faults"]
    assert body["diagnosis"] is not None


def test_diagnose_endpoint_json(client):
    r = client.post("/api/diagnose", json={"observed": {"motor_temp_c": [100.0] * 60}})
    assert r.status_code == 200 and r.get_json() is not None


def test_report_missing_is_json(client):
    r = client.get("/api/report")
    assert r.status_code in (200, 404)
    if r.status_code == 404:
        assert r.get_json()["available"] is False
