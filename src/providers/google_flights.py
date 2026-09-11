from __future__ import annotations

from src.models import FlightOffer, RouteConfig


class GoogleFlightsProvider:
    """Optional secondary source. Kept lightweight and gracefully degrades to an empty result if unavailable."""

    def search(self, route: RouteConfig) -> list[FlightOffer]:
        return []
