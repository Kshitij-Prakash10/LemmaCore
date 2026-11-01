"""Config loading. Every loco number lives in config/loco.json with a status of assumed or confirmed."""

from __future__ import annotations

import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def load_config(path: str | None = None) -> dict:
    """Read config/loco.json (or the given path) and return it as a dict."""
    path = path or os.path.join(ROOT, "config", "loco.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def assumed_blocks(cfg: dict) -> list:
    """Names of config blocks whose status is 'assumed' (shown as badges in the app)."""
    out = []
    for key, block in cfg.items():
        if isinstance(block, dict) and block.get("status") == "assumed":
            out.append(key)
        elif isinstance(block, list):
            if any(isinstance(x, dict) and x.get("status") == "assumed" for x in block):
                out.append(key)
    return out
