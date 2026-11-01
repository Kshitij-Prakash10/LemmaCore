"""Glue between the app and the core. Uses failover.core when it is importable, else the stub."""
from __future__ import annotations

import dataclasses
import json
import os
from typing import Any

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CONFIG_PATH = os.path.join(ROOT, "config", "loco.json")
WINDOW_S = 60
OBS_END_S = 120  # observation window ends this many seconds into the run

try:
    from failover.core.advisor import advise as _advise
    from failover.core.simulate import simulate as _simulate
    from failover.core.types import Scenario
    import failover.core as _core

    CORE_VERSION: str = getattr(_core, "CORE_VERSION", "unknown")
    USING_STUB = False
except Exception:  # core not landed yet
    from failover.stubs.stub_core import CORE_VERSION, Scenario  # type: ignore
    from failover.stubs.stub_core import advise as _advise  # type: ignore
    from failover.stubs.stub_core import simulate as _simulate  # type: ignore

    USING_STUB = True

try:
    from failover.ml import infer as _infer
except Exception:
    _infer = None


def load_config() -> dict:
    """The loco config as a dict."""
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def flatten_assumptions(cfg: dict) -> list[dict]:
    """Every config entry that carries a status, as rows {key, value, status, source}."""
    rows: list[dict] = []

    def walk(node: Any, path: str) -> None:
        if isinstance(node, dict):
            if "status" in node:
                value = {k: v for k, v in node.items() if k not in ("status", "source")}
                if list(value) == ["value"]:
                    value = value["value"]
                rows.append({"key": path, "value": value, "status": node["status"],
                             "source": node.get("source", "")})
                return
            for k, v in node.items():
                if k != "meta":
                    walk(v, f"{path}.{k}" if path else k)
        elif isinstance(node, list):
            for i, v in enumerate(node):
                name = v.get("name", str(i)) if isinstance(v, dict) else str(i)
                walk(v, f"{path}.{name}")

    walk(cfg, "")
    return rows


def make_scenario(req: dict) -> Any:
    """Build a Scenario from a request dict. Units: C, percent, km, km/h."""
    faults = list(req.get("faults", []))
    if req.get("stick_temp") and "TEMP_SENSOR_STUCK" not in faults:
        faults.append("TEMP_SENSOR_STUCK")
    return Scenario(
        id=req.get("id") or ("__".join(faults) or "healthy"),
        faults=tuple(faults),
        ambient_c=float(req.get("ambient_c", 45)),
        gradient_pct=float(req.get("gradient_pct", 2.7)),
        train_load=req.get("train_load", "loaded"),
        units=int(req.get("units", 2)),
        dist_next_station_km=float(req.get("dist_next_station_km", 15)),
        speed_kmph=float(req.get("speed_kmph", 40)),
        noise=float(req.get("noise", 0.02)),
        seed=int(req.get("seed", 1)),
        params=dict(req.get("params", {})),
    )


def _window(observed: dict[str, list[float]], t_s: list[float], end_s: float) -> dict[str, list[float]]:
    idx = [i for i, t in enumerate(t_s) if end_s - WINDOW_S < t <= end_s]
    return {k: [v[i] for i in idx] for k, v in observed.items()}


def _context(sc: Any) -> dict:
    return {k: getattr(sc, k) for k in
            ("ambient_c", "gradient_pct", "train_load", "units", "dist_next_station_km", "speed_kmph")}


def _thin(series: list[float], step: int) -> list[float]:
    return [round(x, 3) for x in series[::step]]


def run_case(req: dict) -> dict:
    """Simulate baseline and advisor, take the advice (optionally after diagnosis), return JSON-ready dict."""
    cfg = load_config()
    sc = make_scenario(req)
    base = _simulate(sc, "baseline", cfg)
    adv_run = _simulate(sc, "advisor", cfg)
    window = _window(base.observed, base.t_s, OBS_END_S)

    diagnosis = None
    hypothesis: list[str] | None = list(sc.faults)
    if req.get("diagnose"):
        diagnosis = diagnose(window)
        if diagnosis.get("available"):
            hypothesis = diagnosis["predicted"] if diagnosis["confidence"] >= 0.6 else None
        else:
            hypothesis = None
    advice = _advise({"observed": window, "context": _context(sc)}, cfg, hypothesis)

    step = max(1, len(base.t_s) // 360)
    limits = cfg.get("limits", {})
    return {
        "core_version": CORE_VERSION, "stub": USING_STUB,
        "scenario": dataclasses.asdict(sc),
        "advice": dataclasses.asdict(advice),
        "diagnosis": diagnosis,
        "runs": {
            p: {"outcome": r.outcome, "limit_hit": r.limit_hit, "t_limit_s": r.t_limit_s,
                "reached_station": r.reached_station, "minutes_left_true": r.minutes_left_true,
                "events": r.events}
            for p, r in (("baseline", base), ("advisor", adv_run))
        },
        "chart": {
            "t_s": _thin(base.t_s, step),
            "motor_temp_baseline": _thin(base.true["motor_temp_c"], step),
            "motor_temp_advisor": _thin(adv_run.true["motor_temp_c"], step),
            "motor_temp_observed": _thin(base.observed["motor_temp_c"], step),
            "air_baseline": _thin(base.true["air_pressure_bar"], step),
            "air_advisor": _thin(adv_run.true["air_pressure_bar"], step),
            "motor_temp_limit_c": limits.get("motor_temp_trip_c", {}).get("value"),
            "air_min_bar": limits.get("brake_air_min_bar", {}).get("value"),
        },
    }


def diagnose(window: dict[str, list[float]]) -> dict:
    """Classifier output, or {"available": False} if the model is not trained yet."""
    if _infer is None or not hasattr(_infer, "diagnose"):
        return {"available": False, "reason": "classifier not built yet"}
    try:
        out = dict(_infer.diagnose(window))
    except FileNotFoundError:
        return {"available": False, "reason": "model file missing, run make train"}
    out["available"] = True
    return out


def coverage() -> dict:
    """outputs/coverage.json, else demo_outputs/coverage.json, else stub coverage."""
    for rel in ("outputs/coverage.json", "demo_outputs/coverage.json"):
        p = os.path.join(ROOT, rel)
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                data = json.load(f)
            data["_source_file"] = rel
            return data
    from failover.stubs.stub_core import stub_coverage
    data = stub_coverage()
    data["_source_file"] = "STUB (no coverage.json yet)"
    return data


def read_json(rel: str) -> dict | None:
    """A JSON file under the repo root, or None."""
    p = os.path.join(ROOT, rel)
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)
