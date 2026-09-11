from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

import requests

from src.models import FlightOffer, RouteConfig


class AmadeusProvider:
    def __init__(self, client_id: str | None = None, client_secret: str | None = None, enable_live: bool = False):
        self.client_id = client_id or os.getenv("AMADEUS_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("AMADEUS_CLIENT_SECRET")
        self.enable_live = enable_live and bool(self.client_id and self.client_secret)

    def _demo_offer(self, route: RouteConfig) -> list[FlightOffer]:
        base_price = 8420 if route.destination == "ISK" else 7820
        return [
            FlightOffer(
                source="demo",
                origin=route.origin,
                destination=route.destination,
                date=route.date,
                airline="IndiGo" if route.destination == "ISK" else "Air India Express",
                flight_numbers=["6E 2032"] if route.destination == "ISK" else ["IX 819"],
                departure="14:00",
                arrival="15:50",
                stops=0,
                duration_minutes=110,
                price=base_price,
                currency="INR",
                baggage="15 kg",
                booking_url="https://example.com/demo-flight",
                fare_type="observed",
                checked_at=datetime.now(timezone.utc).isoformat(),
            )
        ]

    def _live_offer_payload(self, route: RouteConfig) -> dict[str, Any]:
        return {
            "originLocationCode": route.origin,
            "destinationLocationCode": route.destination,
            "departureDate": route.date,
            "adults": 1,
            "max": 5,
            "travelClass": "ECONOMY",
            "nonStop": False,
        }

    def _fetch_token(self) -> str:
        response = requests.post(
            "https://test.api.amadeus.com/v1/security/oauth2/token",
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
            timeout=20,
        )
        response.raise_for_status()
        return response.json()["access_token"]

    def _search_live(self, route: RouteConfig) -> list[FlightOffer]:
        token = self._fetch_token()
        response = requests.get(
            "https://test.api.amadeus.com/v2/shopping/flight-offers",
            params=self._live_offer_payload(route),
            headers={"Authorization": f"Bearer {token}"},
            timeout=25,
        )
        response.raise_for_status()

        offers: list[FlightOffer] = []
        for item in response.json().get("data", [])[:5]:
            itinerary = item["itineraries"][0]
            segments = itinerary["segments"]
            first_segment = segments[0]
            last_segment = segments[-1]
            offers.append(
                FlightOffer(
                    source="amadeus",
                    origin=route.origin,
                    destination=route.destination,
                    date=route.date,
                    airline=first_segment.get("carrierCode", "Unknown"),
                    flight_numbers=[segment.get("carrierCode", "") + " " + segment.get("number", "") for segment in segments],
                    departure=first_segment["departure"]["at"],
                    arrival=last_segment["arrival"]["at"],
                    stops=max(len(segments) - 1, 0),
                    duration_minutes=int(itinerary["duration"].replace("PT", "").replace("H", "*").replace("M", "")) if "PT" in itinerary["duration"] else 0,
                    price=int(float(item["price"]["grandTotal"])),
                    currency=item["price"].get("currency", "INR"),
                    baggage=None,
                    booking_url=item.get("deepLink") or None,
                    fare_type="published fare",
                    checked_at=datetime.now(timezone.utc).isoformat(),
                    raw=item,
                )
            )
        return offers

    def search(self, route: RouteConfig) -> list[FlightOffer]:
        if not self.enable_live:
            return self._demo_offer(route)

        try:
            return self._search_live(route)
        except Exception:
            return self._demo_offer(route)
