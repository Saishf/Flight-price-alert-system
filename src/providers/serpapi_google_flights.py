from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

import requests

from src.models import FlightOffer, RouteConfig


class SerpApiGoogleFlightsProvider:
    """Google Flights results through SerpApi's free monthly search quota."""

    endpoint = "https://serpapi.com/search"

    def __init__(self, api_key: str | None = None, timeout: int = 45):
        self.api_key = api_key or os.getenv("SERPAPI_API_KEY")
        self.timeout = timeout

    @staticmethod
    def public_search_url(route: RouteConfig) -> str:
        return (
            "https://www.google.com/travel/flights"
            f"?q={route.origin}%20to%20{route.destination}%20{route.date}%20one-way"
        )

    def _params(self, route: RouteConfig) -> dict[str, Any]:
        return {
            "engine": "google_flights",
            "departure_id": route.origin,
            "arrival_id": route.destination,
            "outbound_date": route.date,
            "type": "2",
            "travel_class": "1",
            "adults": "1",
            "children": "0",
            "infants_in_seat": "0",
            "infants_on_lap": "0",
            "stops": "2",
            "sort_by": "2",
            "currency": "INR",
            "gl": "in",
            "hl": "en",
            "api_key": self.api_key,
        }

    @staticmethod
    def _time(value: dict[str, Any] | None) -> str:
        if not value:
            return ""
        return str(value.get("time") or "")

    @staticmethod
    def _baggage_text(itinerary: dict[str, Any]) -> str | None:
        texts: list[str] = []
        for extension in itinerary.get("extensions", []) or []:
            if "bag" in str(extension).lower():
                texts.append(str(extension))
        for flight in itinerary.get("flights", []) or []:
            for extension in flight.get("extensions", []) or []:
                if "bag" in str(extension).lower():
                    texts.append(str(extension))
        return "; ".join(texts) if texts else None

    def _offer_from_itinerary(self, itinerary: dict[str, Any], route: RouteConfig) -> FlightOffer | None:
        price = itinerary.get("price")
        flights = itinerary.get("flights") or []
        if not isinstance(price, (int, float)) or not flights:
            return None

        first_flight = flights[0]
        last_flight = flights[-1]
        airlines = []
        flight_numbers = []
        for flight in flights:
            airline = flight.get("airline")
            flight_number = flight.get("flight_number")
            if airline and airline not in airlines:
                airlines.append(str(airline))
            if flight_number:
                flight_numbers.append(str(flight_number))

        return FlightOffer(
            source="serpapi_google_flights",
            origin=route.origin,
            destination=route.destination,
            date=route.date,
            airline=" / ".join(airlines) if airlines else "Unknown",
            flight_numbers=flight_numbers,
            departure=self._time(first_flight.get("departure_airport")),
            arrival=self._time(last_flight.get("arrival_airport")),
            stops=max(len(flights) - 1, 0),
            duration_minutes=int(itinerary.get("total_duration") or 0),
            price=int(price),
            currency="INR",
            baggage=self._baggage_text(itinerary),
            booking_url=self.public_search_url(route),
            fare_type="observed",
            checked_at=datetime.now(timezone.utc).isoformat(),
            raw={
                "type": itinerary.get("type"),
                "extensions": itinerary.get("extensions", []),
                "booking_token_present": bool(itinerary.get("booking_token")),
            },
        )

    def _parse(self, data: dict[str, Any], route: RouteConfig) -> list[FlightOffer]:
        itineraries = []
        itineraries.extend(data.get("best_flights") or [])
        itineraries.extend(data.get("other_flights") or [])

        offers: list[FlightOffer] = []
        for itinerary in itineraries:
            offer = self._offer_from_itinerary(itinerary, route)
            if offer:
                offers.append(offer)

        return sorted(offers, key=lambda item: (item.price, item.stops, item.duration_minutes))

    def search(self, route: RouteConfig) -> list[FlightOffer]:
        if not self.api_key:
            print("SerpApi provider unavailable: SERPAPI_API_KEY is not configured.")
            return []

        try:
            response = requests.get(self.endpoint, params=self._params(route), timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            print(f"SerpApi provider failed for {route.route_label}: {exc}")
            return []

        if data.get("error"):
            print(f"SerpApi provider failed for {route.route_label}: {data['error']}")
            return []

        return self._parse(data, route)[:10]
