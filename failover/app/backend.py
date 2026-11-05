"""Glue between the app and the core. Uses failover.core when it is importable, else the stub."""
from __future__ import annotations

import copy
import dataclasses
import json
import os
from typing import Any

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CONFIG_PATH = os.path.join(ROOT, "config", "loco.json")
WINDOW_S = 60
LEAK_MULTIPLIER = 2.0  # status: assumed. Air leak rate factor when the optional ML leak flag fires.
LEAK_P = 0.5
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
    from failover.core.types import FAULT_IDS
except Exception:  # core not landed yet
    FAULT_IDS = ["U1_TRIP", "U2_TRIP", "STANDBY_STUCK", "MCB_TRIP", "UNIT_DERATE", "BLOWER_FAIL",
                 "COMPRESSOR_FAIL", "TEMP_SENSOR_STUCK"]
TRAIN_LOADS = ("loaded", "empty")

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
    rows.append({"key": "app.LEAK_MULTIPLIER", "value": LEAK_MULTIPLIER, "status": "assumed",
                 "source": "team guess: leak rate factor used by the advisor when the optional MetroPT-3 leak flag "
                           f"has p > {LEAK_P} (failover/app/backend.py)"})
    return rows


class BadRequest(ValueError):
    """A request field is missing, has the wrong type or is out of range. The server answers 400."""


def _num(req: dict, key: str, default: float, lo: float, hi: float) -> float:
    """req[key] as a finite float in [lo, hi], else BadRequest."""
    raw = req.get(key, default)
    if isinstance(raw, bool):
        raise BadRequest(f"{key} must be a number")
    try:
        x = float(raw)
    except (TypeError, ValueError):
        raise BadRequest(f"{key} must be a number") from None
    if not (lo <= x <= hi):  # also rejects NaN
        raise BadRequest(f"{key} must be between {lo:g} and {hi:g}")
    return x


def make_scenario(req: dict) -> Any:
    """Build a Scenario from a request dict. Units: C, percent, km, km/h. Raises BadRequest on bad input."""
    if not isinstance(req, dict):
        raise BadRequest("request body must be a JSON object")
    faults = req.get("faults", [])
    if isinstance(faults, str):
        faults = [faults]
    if not isinstance(faults, (list, tuple)) or not all(isinstance(f, str) for f in faults):
        raise BadRequest("faults must be a list of fault ids")
    faults = list(dict.fromkeys(faults))
    unknown = [f for f in faults if f not in FAULT_IDS]
    if unknown:
        raise BadRequest(f"unknown fault ids {unknown}; valid ids are {FAULT_IDS}")
    if req.get("stick_temp") and "TEMP_SENSOR_STUCK" not in faults:
        faults.append("TEMP_SENSOR_STUCK")
    train_load = req.get("train_load", "loaded")
    if train_load not in TRAIN_LOADS:
        raise BadRequest(f"train_load must be one of {list(TRAIN_LOADS)}")
    units = _num(req, "units", 2, 1, 3)
    if units != int(units):
        raise BadRequest("units must be a whole number")
    seed = _num(req, "seed", 1, 0, 2**32 - 1)
    if seed != int(seed):
        raise BadRequest("seed must be a whole number")
    params = req.get("params", {})
    if not isinstance(params, dict):
        raise BadRequest("params must be a JSON object")
    params = {str(k): _num(params, k, 0, -1e6, 1e6) for k in params}
    sid = req.get("id") or ("__".join(faults) or "healthy")
    return Scenario(
        id=str(sid),
        faults=tuple(faults),
        ambient_c=_num(req, "ambient_c", 45, -50, 70),
        gradient_pct=_num(req, "gradient_pct", 2.7, -10, 10),
        train_load=train_load,
        units=int(units),
        dist_next_station_km=_num(req, "dist_next_station_km", 15, 0, 500),
        speed_kmph=_num(req, "speed_kmph", 40, 1, 200),
        noise=_num(req, "noise", 0.02, 0, 1),
        seed=int(seed),
        params=dict(params),
    )


def _window(observed: dict[str, list[float]], t_s: list[float], end_s: float) -> dict[str, list[float]]:
    idx = [i for i, t in enumerate(t_s) if end_s - WINDOW_S < t <= end_s]
    return {k: [v[i] for i in idx] for k, v in observed.items()}


def _context(sc: Any) -> dict:
    return {k: getattr(sc, k) for k in
            ("ambient_c", "gradient_pct", "train_load", "units", "dist_next_station_km", "speed_kmph")}


def _thin(series: list[float], step: int) -> list[float]:
    return [round(x, 3) for x in series[::step]]


def _leak_hook(req: dict, cfg: dict, window: dict, sc: Any) -> tuple[dict, dict]:
    """The single ML hook on the air clock. Returns (config for the advisor, card info).
    It can only raise the leak rate the advisor sees, so it never makes the air clock more optimistic.
    No model, no data or any error: the config is returned untouched and the advice is as before."""
    empty = {"p": None, "line": None, "source": None, "valid": None, "flag": False, "rate": None, "explain": []}
    try:
        from failover.ml.leak_detector import assess
        res = assess(req)
        if res is None or (res["valid"] and not res["flag"]):
            return cfg, {**empty, **(res or {}), "line": None}
        out = copy.deepcopy(cfg)
        spec = out["air"]["leak_bar_per_min"]
        keys = [k for k in ("min", "nominal", "max") if k in spec]
        out["air"]["use_fitted"] = False
        if not res["valid"]:
            worst = max(spec[k] for k in keys)
            for k in keys:
                spec[k] = worst
            return out, {**empty, **res, "line": "compressor data invalid - using cautious air estimate"}
        if res["rate"] is not None and res["rate"] > 0:
            for k in keys:
                spec[k] = max(spec[k], res["rate"])
            z = _air_minutes(cfg, window, sc, spec["nominal"])
            zs = "no limit while the compressor keeps up" if z == float("inf") else f"{z:.1f} min"
            y = res["normal_rate"] if res["normal_rate"] is not None else cfg["air"]["leak_bar_per_min"]["nominal"]
            line = f"Air leak suspected - reservoir falling {res['rate']:.2f} bar/min (normal {y:.2f}) - air limit now {zs}"
            return out, {**empty, **res, "line": line}
        for k in keys:
            spec[k] = spec[k] * LEAK_MULTIPLIER
        line = f"Air leak suspected (model p={res['p']:.2f}) - air limit shortened"
        return out, {**empty, **res, "line": line}
    except Exception:
        return cfg, empty


def _air_minutes(cfg: dict, window: dict, sc: Any, leak: float) -> float:
    """Minutes to the brake-air limit at this leak rate, from the core's own air model."""
    from failover.core.model import air_time_to_limit_min, resolve_params
    p = resolve_params(cfg, None, "nominal")
    obs = window.get("air_pressure_bar") or [p["normal_bar"]]
    return air_time_to_limit_min(float(obs[-1]), cfg["limits"]["brake_air_min_bar"]["value"], leak,
                                 "COMPRESSOR_FAIL" not in sc.faults, p["fill"])


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
        # trust the classifier only when it is confident AND names a fault; an empty or unsure
        # prediction must not reach the advisor as "no faults", so it infers from signals instead
        ok = diagnosis.get("available") and diagnosis["confidence"] >= 0.6 and diagnosis["predicted"]
        hypothesis = list(diagnosis["predicted"]) if ok else None
        if diagnosis.get("available"):
            diagnosis["used_by_advisor"] = bool(ok)
    adv_cfg, leak = _leak_hook(req, cfg, window, sc)
    advice = _advise({"observed": window, "context": _context(sc)}, adv_cfg, hypothesis)

    step = max(1, len(base.t_s) // 360)
    limits = cfg.get("limits", {})
    return {
        "core_version": CORE_VERSION, "stub": USING_STUB,
        "scenario": dataclasses.asdict(sc),
        "advice": dataclasses.asdict(advice),
        "diagnosis": diagnosis,
        "leak": leak,
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
    if not any(len(v) for v in window.values()):
        return {"available": False, "reason": "no observed signal data in the window"}
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
