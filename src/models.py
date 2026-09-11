from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class FlightOffer:
    source: str
    origin: str
    destination: str
    date: str
    airline: str
    flight_numbers: list[str] = field(default_factory=list)
    departure: str = ""
    arrival: str = ""
    stops: int = 0
    duration_minutes: int = 0
    price: int = 0
    currency: str = "INR"
    baggage: str | None = None
    booking_url: str | None = None
    fare_type: str = "observed"
    checked_at: str = ""
    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "origin": self.origin,
            "destination": self.destination,
            "date": self.date,
            "airline": self.airline,
            "flight_numbers": self.flight_numbers,
            "departure": self.departure,
            "arrival": self.arrival,
            "stops": self.stops,
            "duration_minutes": self.duration_minutes,
            "price": self.price,
            "currency": self.currency,
            "baggage": self.baggage,
            "booking_url": self.booking_url,
            "fare_type": self.fare_type,
            "checked_at": self.checked_at,
        }


@dataclass
class RouteConfig:
    origin: str
    destination: str
    date: str
    target_price: int | None = None
    label: str | None = None

    @property
    def key(self) -> str:
        return f"{self.origin}-{self.destination}-{self.date}"

    @property
    def route_label(self) -> str:
        return self.label or f"{self.origin} -> {self.destination}"
