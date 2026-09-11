from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


class PriceStore:
    def __init__(self, file_path: str | Path = "data/prices.json"):
        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.file_path.exists():
            self.file_path.write_text(
                json.dumps({"routes": {}}, indent=2), encoding="utf-8"
            )

    def _load(self) -> dict:
        try:
            with open(self.file_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (json.JSONDecodeError, FileNotFoundError):
            data = {"routes": {}}
        if "routes" not in data:
            data["routes"] = {}
        return data

    def _save(self, data: dict) -> None:
        with open(self.file_path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)

    @staticmethod
    def route_key(origin: str, destination: str, date: str) -> str:
        return f"{origin}-{destination}-{date}"

    def get_route(self, origin: str, destination: str, date: str) -> dict:
        data = self._load()
        return data["routes"].get(
            self.route_key(origin, destination, date),
            {
                "history": [],
                "lowest_price": None,
                "latest_price": None,
            },
        )

    def append_offer(self, route: dict, offer: dict) -> dict:
        data = self._load()
        key = self.route_key(route["origin"], route["destination"], route["date"])
        route_data = data["routes"].setdefault(
            key, {"history": [], "lowest_price": None, "latest_price": None}
        )

        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "price": offer["price"],
            "airline": offer["airline"],
            "source": offer["source"],
            "stops": offer["stops"],
            "route": f"{route['origin']} -> {route['destination']}",
        }
        route_data["history"].append(entry)
        route_data["latest_price"] = offer["price"]

        historical_prices = [item["price"] for item in route_data["history"]]
        route_data["lowest_price"] = (
            min(historical_prices) if historical_prices else None
        )

        data["routes"][key] = route_data
        self._save(data)
        return route_data
