"""MetroPT-3 loader (real metro compressor data, used as a proxy). Reads the CSV in chunks and caches a pickle.

The file in data/raw has rows 10 s apart (see data/README.md), not 1 Hz as the PDF says.
"""
from __future__ import annotations

import json
import os

import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RAW_CSV = os.path.join(ROOT, "data", "raw", "metropt3.csv")
CACHE = os.path.join(ROOT, "data", "raw", "metropt3.pkl")
FAILURES = os.path.join(ROOT, "data", "processed", "failures.json")
ANALOG = ["TP2", "TP3", "H1", "DV_pressure", "Reservoirs", "Oil_temperature", "Motor_current"]
DIGITAL = ["COMP", "DV_eletric", "Towers", "MPG", "LPS", "Pressure_switch", "Oil_level", "Caudal_impulses"]


def load(chunksize: int = 250_000) -> pd.DataFrame:
    """All rows, indexed by timestamp, float32 signals. Units: bar, C, A; digital 0/1."""
    if os.path.exists(CACHE):
        return pd.read_pickle(CACHE)
    parts = []
    for chunk in pd.read_csv(RAW_CSV, usecols=["timestamp"] + ANALOG + DIGITAL, chunksize=chunksize):
        chunk["timestamp"] = pd.to_datetime(chunk["timestamp"])
        parts.append(chunk.set_index("timestamp").astype("float32"))
    df = pd.concat(parts).sort_index()
    df.to_pickle(CACHE)
    return df


def failures() -> list[dict]:
    """Labelled air-leak events with pandas timestamps."""
    with open(FAILURES, encoding="utf-8") as f:
        rows = json.load(f)["failures"]
    return [{**r, "start": pd.Timestamp(r["start"]), "end": pd.Timestamp(r["end"])} for r in rows]


if __name__ == "__main__":
    d = load()
    print(len(d), d.index.min(), d.index.max())
    print(d.index.to_series().diff().value_counts().head(3))
    print(d.describe().T[["mean", "min", "max"]])
