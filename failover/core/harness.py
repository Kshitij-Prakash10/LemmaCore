"""Fault-injection harness: every single and double fault, four conditions, baseline and advisor.

CLI: python -m failover.core.harness --out outputs
The advisor policy receives the true fault set (an oracle) so this measures the advisor, not the classifier.
"""

from __future__ import annotations

import argparse
import csv
import html
import itertools
import json
import os
import time
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone

from .config import ROOT, assumed_blocks, load_config
from .model import CAP_MIN, allocate, plant_from_faults
from .simulate import simulate
from .types import FAULT_IDS, Scenario
from .version import CORE_VERSION

SEED = 1


def fault_sets() -> list:
    """8 single faults and 28 pairs: 36 combinations."""
    return [(f,) for f in FAULT_IDS] + list(itertools.combinations(FAULT_IDS, 2))


def case_id(faults, cond_id: str) -> str:
    return "+".join(faults) + "__" + cond_id


def enumerate_cases(cfg: dict) -> list:
    return [(f, c) for f in fault_sets() for c in cfg["conditions"]]


def _check_properties(cfg: dict, sc: Scenario, adv_run, advice_events: list) -> list:
    """Return the names of failed properties for one advisor run (empty list means all hold)."""
    failed = []
    names = {l["name"] for l in cfg["loads"]}
    essential = {l["name"] for l in cfg["loads"] if l["priority"] == "essential"}
    plant = plant_from_faults(sc.faults, sc.units)
    if adv_run.limit_hit == "brake_air":
        failed.append("P1_brake_air_below_minimum")
    for e in advice_events:
        if essential & set(e["shed"]):
            failed.append("P2_essential_load_shed")
        alloc = allocate(cfg, sc.ambient_c, plant["states"], plant["failover_ok"], shed=names - set(e["keep"]))
        if alloc["powered"] != set(e["keep"]):
            failed.append("P3_more_load_than_power")
    if advice_events and adv_run.minutes_left_true is not None:
        if advice_events[0]["minutes_left_p5"] > min(adv_run.minutes_left_true, CAP_MIN) + 0.1:
            failed.append("P4_optimistic_minutes_left")
    return sorted(set(failed))


def _run_case(args: tuple) -> dict:
    faults, cond, cfg = args
    d = cfg["defaults"]
    sc = Scenario(id=case_id(faults, cond["id"]), faults=tuple(faults), ambient_c=cond["ambient_c"],
                  gradient_pct=cond["gradient_pct"], train_load=cond["train_load"], units=cfg["converters"]["count"],
                  dist_next_station_km=d["dist_next_station_km"], speed_kmph=d["speed_kmph"], seed=SEED)
    base = simulate(sc, "baseline", cfg)
    adv = simulate(sc, "advisor", cfg)
    events = [e for e in adv.events if e["type"] == "advice"]
    first = events[0] if events else None
    failed = _check_properties(cfg, sc, adv, events)
    return {
        "case_id": sc.id, "faults": list(faults), "condition": cond["id"],
        "baseline": {"outcome": base.outcome, "limit_hit": base.limit_hit, "t_limit_s": base.t_limit_s,
                     "reached_station": base.reached_station, "minutes_left_true": base.minutes_left_true},
        "advisor": {"outcome": adv.outcome, "limit_hit": adv.limit_hit, "t_limit_s": adv.t_limit_s,
                    "reached_station": adv.reached_station,
                    "decision": first["decision"] if first else "NONE",
                    "shed": first["shed"] if first else [],
                    "limiting_factor": first["limiting_factor"] if first else "none",
                    "minutes_left_p5": first["minutes_left_p5"] if first else None,
                    "minutes_left_true": adv.minutes_left_true},
        "properties_ok": not failed, "properties_failed": failed,
    }


def _summary(cases: list) -> dict:
    b_unsafe = sum(c["baseline"]["outcome"] == "UNSAFE" for c in cases)
    a_unsafe = sum(c["advisor"]["outcome"] == "UNSAFE" for c in cases)
    return {
        "runs_per_policy": len(cases),
        "baseline_unsafe": b_unsafe, "advisor_unsafe": a_unsafe,
        "baseline_safe": sum(c["baseline"]["outcome"] == "SAFE" for c in cases),
        "advisor_safe": sum(c["advisor"]["outcome"] == "SAFE" for c in cases),
        "advisor_controlled_stops": sum(c["advisor"]["outcome"] == "CONTROLLED_STOP" for c in cases),
        "saved_by_advisor": sum(c["baseline"]["outcome"] == "UNSAFE" and c["advisor"]["outcome"] != "UNSAFE"
                                for c in cases),
        "false_stops": sum(c["baseline"]["outcome"] == "SAFE" and c["advisor"]["outcome"] == "CONTROLLED_STOP"
                           for c in cases),
        "properties_failed": sum(not c["properties_ok"] for c in cases),
    }


_COLOUR = {"SAFE": "#2f7d4f", "CONTROLLED_STOP": "#b9770e", "UNSAFE": "#b03a2e"}


def _report_html(cov: dict, cfg: dict) -> str:
    s = cov["summary"]
    conds = [c["id"] for c in cov["conditions"]]
    by = {(tuple(c["faults"]), c["condition"]): c for c in cov["cases"]}
    rows = []
    seen = []
    for c in cov["cases"]:
        key = tuple(c["faults"])
        if key not in seen:
            seen.append(key)
    for key in seen:
        cells = []
        for cid in conds:
            c = by.get((key, cid))
            if c is None:
                cells.append("<td></td>")
                continue
            b, a = c["baseline"]["outcome"], c["advisor"]["outcome"]
            cells.append(
                f'<td><span class="b" style="background:{_COLOUR[b]}" title="baseline {b}">B</span>'
                f'<span class="b" style="background:{_COLOUR[a]}" title="advisor {a} ({c["advisor"]["decision"]})">A</span></td>')
        rows.append(f"<tr><th>{html.escape(' + '.join(key))}</th>{''.join(cells)}</tr>")
    assumed = "".join(f"<li>{html.escape(x)}</li>" for x in cov["assumptions"])
    head = "".join(f"<th>{html.escape(c)}</th>" for c in conds)
    return f"""<!doctype html><meta charset="utf-8"><title>Failover Guardian test report</title>
<style>body{{font:15px system-ui,sans-serif;max-width:980px;margin:24px auto;padding:0 16px;color:#131e27}}
table{{border-collapse:collapse}}th,td{{border:1px solid #d5dde2;padding:4px 8px;text-align:left}}
.b{{display:inline-block;color:#fff;font-weight:600;border-radius:3px;padding:1px 7px;margin-right:4px}}
.tiles span{{display:inline-block;margin:0 16px 8px 0}}</style>
<h1>Failover Guardian: fault-injection report</h1>
<p>Core version {html.escape(cov['core_version'])}, generated {html.escape(cov['generated_utc'])}, seed {cov['seed']}.
Each cell shows B (baseline) and A (advisor): green safe, amber controlled stop, red unsafe.
The advisor receives the true fault set.</p>
<p class="tiles"><span><b>{s['runs_per_policy']}</b> runs per policy</span>
<span><b>{s['baseline_unsafe']}</b> baseline unsafe</span><span><b>{s['advisor_unsafe']}</b> advisor unsafe</span>
<span><b>{s['saved_by_advisor']}</b> saved by the advisor</span><span><b>{s['false_stops']}</b> stops the baseline did not need</span>
<span><b>{s['properties_failed']}</b> cases with a failed property</span></p>
<table><tr><th>Faults</th>{head}</tr>{''.join(rows)}</table>
<h2>Assumptions</h2><p>These parameter blocks are still marked assumed in config/loco.json:</p><ul>{assumed}</ul>
<h2>Limits</h2><p>Every loco parameter is an assumption until a mentor confirms it. The baseline is a modelling assumption:
no load shedding, with the loco's own protection derating and tripping. A stopped train does not count as unsafe.
The advisor stops when the cautious (5th percentile) minutes left do not cover the trip, so some stops are
not needed; that count is shown above. This is a simulation of our model, not of a real loco.</p>"""


def run_harness(config: dict | None = None, out_dir: str = "outputs", n_mc: int | None = None,
                workers: int | None = None, max_cases: int | None = None) -> dict:
    cfg = json.loads(json.dumps(config or load_config()))
    if n_mc is not None:
        cfg["advisor"]["mc_runs"] = int(n_mc)
    cases_in = enumerate_cases(cfg)
    if max_cases:
        cases_in = cases_in[:max_cases]
    args = [(f, c, cfg) for f, c in cases_in]
    t0 = time.time()
    workers = workers if workers is not None else (os.cpu_count() or 1)
    if workers > 1 and len(args) > 4:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            cases = list(pool.map(_run_case, args, chunksize=4))
    else:
        cases = [_run_case(a) for a in args]
    cov = {
        "core_version": CORE_VERSION,
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "seed": SEED,
        "conditions": [{"id": c["id"], "ambient_c": c["ambient_c"], "gradient_pct": c["gradient_pct"],
                        "train_load": c["train_load"]} for c in cfg["conditions"]],
        "faults": FAULT_IDS,
        "advisor_policy_note": "advisor receives the true fault set (oracle)",
        "assumptions": assumed_blocks(cfg),
        "cases": cases,
        "summary": _summary(cases),
        "elapsed_s": round(time.time() - t0, 1),
    }
    out = out_dir if os.path.isabs(out_dir) else os.path.join(ROOT, out_dir)
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "coverage.json"), "w", encoding="utf-8") as f:
        json.dump(cov, f, indent=1)
    with open(os.path.join(out, "runs.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["case_id", "faults", "condition", "policy", "outcome", "limit_hit", "t_limit_s",
                    "reached_station", "decision", "minutes_left_p5", "properties_ok"])
        for c in cases:
            for pol in ("baseline", "advisor"):
                r = c[pol]
                w.writerow([c["case_id"], "+".join(c["faults"]), c["condition"], pol, r["outcome"], r["limit_hit"],
                            r["t_limit_s"], r["reached_station"], r.get("decision", ""),
                            r.get("minutes_left_p5", ""), c["properties_ok"]])
    with open(os.path.join(out, "report.html"), "w", encoding="utf-8") as f:
        f.write(_report_html(cov, cfg))
    return cov


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="outputs")
    ap.add_argument("--mc", type=int, default=None, help="Monte Carlo runs per advice (default from config)")
    ap.add_argument("--workers", type=int, default=None)
    ap.add_argument("--max-cases", type=int, default=None)
    a = ap.parse_args()
    cov = run_harness(None, a.out, a.mc, a.workers, a.max_cases)
    print(json.dumps(cov["summary"], indent=1))
    print(f"wrote {a.out}/coverage.json, runs.csv, report.html in {cov['elapsed_s']} s")


if __name__ == "__main__":
    main()
