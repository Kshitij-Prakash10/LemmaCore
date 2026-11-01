"""External test of the v2 leak model on MetroPT-2 (Zenodo 7766691, CC BY 4.0). Never used in training.

Skips cleanly if the file is absent. Writes models/leak_v2_external.json. CLI: python -m failover.ml.external_test
"""
from __future__ import annotations

import json
import os

import joblib
import numpy as np
import pandas as pd

from failover.ml import leak_features as lf

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CANDIDATES = [os.path.join(ROOT, "data", "MetroPT2.csv"), os.path.join(ROOT, "data", "raw", "MetroPT2.csv")]
OUT = os.path.join(ROOT, "models", "leak_v2_external.json")
MODEL = os.path.join(ROOT, "models", "leak_model_v2.joblib")
AIR = (pd.Timestamp("2022-06-04 10:19:24"), pd.Timestamp("2022-06-04 14:22:39"))
OIL = (pd.Timestamp("2022-07-11 10:10:18"), pd.Timestamp("2022-07-14 10:22:08"))


def _minutes(path: str, chunksize: int = 500_000) -> pd.DataFrame:
    """Read in chunks and resample each chunk to 1 min, then average minutes split across chunks by row count."""
    parts = []
    for chunk in pd.read_csv(path, chunksize=chunksize):
        chunk = lf.normalise(chunk)
        tcol = next(c for c in chunk.columns if c.lower() == "timestamp")
        chunk.index = pd.to_datetime(chunk[tcol])
        parts.append(lf.to_minutes(chunk.sort_index()))
    m = pd.concat(parts)
    weighted = m.drop(columns="n_rows").multiply(m["n_rows"].fillna(0), axis=0)
    g = weighted.groupby(level=0).sum()
    n = m["n_rows"].fillna(0).groupby(level=0).sum()
    out = g.divide(n.replace(0, np.nan), axis=0)
    out["n_rows"] = n
    return out.sort_index().asfreq("1min").assign(n_rows=lambda d: d["n_rows"].fillna(0))


def main(path: str | None = None) -> dict:
    """Apply the saved model unchanged and report detection and false alarms."""
    path = path or next((c for c in CANDIDATES if os.path.exists(c)), None)
    if path is None or not os.path.exists(path):
        out = {"available": False, "reason": "data/MetroPT2.csv is not on this machine; external test not run"}
    else:
        b = joblib.load(MODEL)
        m = b["model"]
        F = lf.features(_minutes(path))
        X, valid, ti = F[b["features"]].to_numpy(float), F["valid"].to_numpy(), F.index
        p = m.predict_p(X) if hasattr(m, "predict_p") else m.predict_proba(X)[:, 1]
        a = lf.alarm(p, valid, b["theta"])
        air, oil = (ti >= AIR[0]) & (ti <= AIR[1]), (ti >= OIL[0]) & (ti <= OIL[1])
        first = ti[a & air]
        rest = a & ~air & ~oil
        starts = rest & ~np.concatenate([[False], rest[:-1]])
        days = (valid & ~air & ~oil).sum() / 1440
        out = {"available": True, "data": "MetroPT-2, external, not used in training", "theta": b["theta"],
               "air_leak_detected": bool(len(first)),
               "air_leak_minutes_to_first_alert": round((first[0] - AIR[0]).total_seconds() / 60, 1) if len(first) else None,
               "oil_leak_alert_fraction": round(float(a[oil].mean()), 3) if oil.any() else None,
               "false_alarms_per_day": round(float(starts.sum() / days), 3) if days else None,
               "valid_fraction": round(float(valid.mean()), 3)}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    print(json.dumps(out, indent=1))
    return out


if __name__ == "__main__":
    main()
