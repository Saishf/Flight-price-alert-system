from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from src.models import FlightOffer, RouteConfig


class TripProvider:
    """Trip.com browser provider for observed public fares."""

    def __init__(self, debug_dir: str | Path = "data/debug", headless: bool = True):
        self.debug_dir = Path(debug_dir)
        self.headless = headless

    @staticmethod
    def _search_url(route: RouteConfig) -> str:
        origin = route.origin.lower()
        destination = route.destination.lower()
        return (
            "https://www.trip.com/flights/showfarefirst"
            f"?dcity={origin}&acity={destination}"
            f"&ddate={route.date}"
            "&triptype=ow"
            "&class=y"
            "&quantity=1"
            "&locale=en-IN"
            "&curr=INR"
        )

    @staticmethod
    def _duration_minutes(value: Any) -> int:
        if isinstance(value, (int, float)):
            return int(value)
        text = str(value or "")
        hours = re.search(r"(\d+)\s*h", text, re.IGNORECASE)
        minutes = re.search(r"(\d+)\s*m", text, re.IGNORECASE)
        return (int(hours.group(1)) * 60 if hours else 0) + (int(minutes.group(1)) if minutes else 0)

    @staticmethod
    def _parse_price(value: Any) -> int | None:
        if isinstance(value, (int, float)):
            return int(value)
        text = str(value or "")
        match = re.search(r"(?:INR|₹|Rs\.?)\s*([0-9][0-9,]*)", text, re.IGNORECASE)
        if not match:
            match = re.search(r"\b([1-9][0-9]{3,6})\b", text.replace(",", ""))
        if not match:
            return None
        return int(match.group(1).replace(",", ""))

    @staticmethod
    def _walk_json(value: Any) -> list[dict[str, Any]]:
        found: list[dict[str, Any]] = []
        if isinstance(value, dict):
            found.append(value)
            for child in value.values():
                found.extend(TripProvider._walk_json(child))
        elif isinstance(value, list):
            for child in value:
                found.extend(TripProvider._walk_json(child))
        return found

    @staticmethod
    def _load_json_candidates(payload: str) -> list[Any]:
        candidates: list[Any] = []
        for line in payload.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("data:"):
                line = line[5:].strip()
            if not line or line == "[DONE]":
                continue
            try:
                candidates.append(json.loads(line))
            except json.JSONDecodeError:
                continue

        if not candidates:
            try:
                candidates.append(json.loads(payload))
            except json.JSONDecodeError:
                pass
        return candidates

    @staticmethod
    def _value_from_keys(data: dict[str, Any], keys: tuple[str, ...]) -> Any:
        lowered = {str(key).lower(): value for key, value in data.items()}
        for key in keys:
            if key.lower() in lowered:
                return lowered[key.lower()]
        return None

    def _offer_from_record(self, record: dict[str, Any], route: RouteConfig, url: str) -> FlightOffer | None:
        record_text = json.dumps(record, ensure_ascii=False, default=str)
        if route.origin not in record_text or route.destination not in record_text:
            return None

        price = self._parse_price(
            self._value_from_keys(
                record,
                (
                    "price",
                    "amount",
                    "adultPrice",
                    "displayPrice",
                    "displayPriceText",
                    "lowestPrice",
                    "totalPrice",
                    "salePrice",
                ),
            )
            or record_text
        )
        if price is None:
            return None

        airline = self._value_from_keys(record, ("airlineName", "airline", "carrierName", "marketingCarrierName")) or "Unknown"
        flight_number = self._value_from_keys(record, ("flightNo", "flightNumber", "flightNumbers", "flightNoList"))
        departure = self._value_from_keys(record, ("departureTime", "departTime", "dTime", "departDateTime")) or ""
        arrival = self._value_from_keys(record, ("arrivalTime", "arriveTime", "aTime", "arriveDateTime")) or ""
        stops = self._value_from_keys(record, ("stopCount", "stops", "transferCount"))
        duration = self._value_from_keys(record, ("duration", "durationMinutes", "durationTime"))
        baggage = self._value_from_keys(record, ("baggage", "baggageText", "baggageAllowance"))

        try:
            stop_count = int(stops or 0)
        except (TypeError, ValueError):
            stop_count = 0 if "nonstop" in record_text.lower() or "direct" in record_text.lower() else 1

        if isinstance(flight_number, list):
            flight_numbers = [str(item) for item in flight_number]
        elif flight_number:
            flight_numbers = [str(flight_number)]
        else:
            flight_numbers = []

        return FlightOffer(
            source="trip.com",
            origin=route.origin,
            destination=route.destination,
            date=route.date,
            airline=str(airline),
            flight_numbers=flight_numbers,
            departure=str(departure),
            arrival=str(arrival),
            stops=stop_count,
            duration_minutes=self._duration_minutes(duration),
            price=price,
            currency="INR",
            baggage=str(baggage) if baggage else None,
            booking_url=url,
            fare_type="observed",
            checked_at=datetime.now(timezone.utc).isoformat(),
            raw=record,
        )

    def _parse_network_payloads(self, payloads: list[str], route: RouteConfig, url: str) -> list[FlightOffer]:
        offers_by_key: dict[tuple[int, str, str], FlightOffer] = {}
        for payload in payloads:
            for candidate in self._load_json_candidates(payload):
                for record in self._walk_json(candidate):
                    offer = self._offer_from_record(record, route, url)
                    if offer:
                        key = (offer.price, offer.departure, offer.arrival)
                        offers_by_key[key] = offer
        return sorted(offers_by_key.values(), key=lambda item: (item.price, item.stops, item.duration_minutes))

    def _save_debug(self, page: Any, route: RouteConfig, reason: str) -> None:
        self.debug_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        base = self.debug_dir / f"trip-{route.origin}-{route.destination}-{route.date}-{stamp}"
        try:
            page.screenshot(path=str(base.with_suffix(".png")), full_page=True)
        except Exception:
            pass
        try:
            base.with_suffix(".html").write_text(page.content(), encoding="utf-8")
        except Exception:
            pass
        base.with_suffix(".txt").write_text(reason, encoding="utf-8")

    @staticmethod
    def _blocked_reason(page: Any) -> str | None:
        try:
            text = page.locator("body").inner_text(timeout=2000).lower()
        except Exception:
            return None

        if "whaleguard block" in text:
            return "Trip.com blocked this automated browser with WhaleGuard."
        if "captcha" in text or "robot" in text or "access denied" in text:
            return "Trip.com showed an anti-bot or access-control page."
        return None

    def search(self, route: RouteConfig) -> list[FlightOffer]:
        url = self._search_url(route)
        payloads: list[str] = []

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=self.headless)
            page = browser.new_page(locale="en-IN", timezone_id="Asia/Kolkata")

            def capture_response(response: Any) -> None:
                response_url = response.url.lower()
                if "flightlistsearch" not in response_url and "flightsearch" not in response_url:
                    return
                try:
                    payloads.append(response.text())
                except Exception:
                    return

            page.on("response", capture_response)

            try:
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(12000)
                try:
                    page.wait_for_load_state("networkidle", timeout=15000)
                except PlaywrightTimeoutError:
                    pass
                blocked_reason = self._blocked_reason(page)
                if blocked_reason:
                    self._save_debug(page, route, blocked_reason)
                    print(f"Trip.com provider unavailable for {route.route_label}: {blocked_reason}")
                    return []
                offers = self._parse_network_payloads(payloads, route, url)
                if not offers:
                    self._save_debug(page, route, "No Trip.com flight offers could be parsed.")
                return offers[:10]
            except Exception as exc:
                self._save_debug(page, route, f"Trip.com provider failed: {exc}")
                return []
            finally:
                browser.close()
