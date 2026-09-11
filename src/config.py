from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from src.models import RouteConfig


ROOT_DIR = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT_DIR / "config.yaml"


def _as_config_string(value: Any) -> str:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def load_config(path: str | Path | None = None) -> dict:
    config_path = Path(path) if path else CONFIG_PATH
    with open(config_path, "r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle) or {}

    routes_raw = config.get("routes", [])
    config["routes"] = [
        RouteConfig(
            origin=route["origin"],
            destination=route["destination"],
            date=_as_config_string(route["date"]),
            target_price=route.get("target_price"),
            label=route.get("label"),
        )
        for route in routes_raw
    ]
    return config
