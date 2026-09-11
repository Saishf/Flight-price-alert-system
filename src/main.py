from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import webbrowser
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from dotenv import load_dotenv

from src.config import load_config
from src.decision_engine import DecisionEngine
from src.models import FlightOffer
from src.notifications.email import send_email
from src.notifications.telegram import send_telegram
from src.price_store import PriceStore
from src.providers.amadeus import AmadeusProvider
from src.providers.serpapi_google_flights import SerpApiGoogleFlightsProvider


def _route_summary(route: dict) -> str:
    return f"{route.origin} -> {route.destination} ({route.date})"


def _format_alert(route: dict, decision: dict, best_offer: FlightOffer) -> str:
    drop = ""
    if decision["previous_price"] is not None:
        delta = best_offer.price - decision["previous_price"]
        delta_text = f"{abs(delta):,}"
        direction = "drop" if delta < 0 else "rise"
        drop = f"Previous: ₹{decision['previous_price']:,}\n{direction.title()}: ₹{delta_text}"

    url_line = best_offer.booking_url or "No direct booking URL available from this source."
    return (
        "✈️ FLIGHT PRICE ALERT\n\n"
        f"{route.route_label}\n"
        f"{route.date}\n"
        f"{best_offer.airline} — {best_offer.departure} → {best_offer.arrival}\n"
        f"Stops: {best_offer.stops}\n"
        f"Price: ₹{best_offer.price:,}\n\n"
        f"Reason: {decision['reason']}\n"
        f"{drop}\n\n"
        f"Open route: {url_line}"
    )


def _json_default(value: Any) -> str:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def pick_best_offer(offers: list[FlightOffer]) -> FlightOffer:
    if not offers:
        raise ValueError("No offers available")

    nonstop = [offer for offer in offers if offer.stops == 0]
    if nonstop:
        return sorted(nonstop, key=lambda item: (item.price, item.duration_minutes))[0]
    return sorted(offers, key=lambda item: (item.stops, item.price, item.duration_minutes))[0]


def open_route_url(url: str) -> bool:
    try:
        if sys.platform.startswith("win"):
            os.startfile(url)  # type: ignore[attr-defined]
            return True
        if sys.platform == "darwin":
            subprocess.Popen(["open", url])
            return True
        subprocess.Popen(["xdg-open", url])
        return True
    except Exception:
        try:
            return webbrowser.open(url)
        except Exception:
            return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Flight Price Agent")
    parser.add_argument("--demo", action="store_true", help="Use sample/demo ticket data instead of live providers")
    parser.add_argument("--json", action="store_true", help="Print each route output as JSON")
    parser.add_argument("--open", action="store_true", help="Open the route search page in the browser after each live result")
    args = parser.parse_args()

    load_dotenv(ROOT_DIR / ".env")
    config = load_config()
    price_store = PriceStore(ROOT_DIR / "data" / "prices.json")
    engine = DecisionEngine()

    demo_provider = AmadeusProvider(enable_live=False)
    live_provider = SerpApiGoogleFlightsProvider()

    results = []
    missing_routes = 0
    alert_routes: list[tuple[dict, dict, FlightOffer]] = []

    for route in config.get("routes", []):
        if args.demo:
            available_offers = demo_provider.search(route)
        else:
            available_offers = live_provider.search(route)

        if not available_offers:
            missing_routes += 1
            print(f"No offers found for {_route_summary(route)}")
            continue

        best_offer = pick_best_offer(available_offers)
        route_state = price_store.get_route(route.origin, route.destination, route.date)
        previous_price = route_state.get("latest_price")
        historical_min = route_state.get("lowest_price")

        decision = engine.evaluate(
            route=route.route_label,
            current_price=best_offer.price,
            previous_price=previous_price,
            historical_min=historical_min,
            target_price=route.target_price,
        )

        route_record = {
            "route": route.route_label,
            "date": route.date,
            "best_offer": best_offer.to_dict(),
            "decision": decision,
        }
        results.append(route_record)

        if decision["alert"]:
            alert_routes.append((route, decision, best_offer))

        price_store.append_offer(
            {
                "origin": route.origin,
                "destination": route.destination,
                "date": route.date,
            },
            best_offer.to_dict(),
        )

        if args.open and best_offer.booking_url:
            try:
                opened = open_route_url(best_offer.booking_url)
                if opened:
                    print(f"Opened route page in browser: {best_offer.booking_url}")
                else:
                    print(f"Browser open request returned False for: {best_offer.booking_url}")
            except Exception as exc:
                print(f"Could not open route page automatically: {exc}")

        if args.json:
            print(json.dumps(route_record, indent=2, default=_json_default))
        else:
            print(f"Route: {route.route_label} | Lowest: ₹{best_offer.price:,} | Status: {decision['reason']}")

    if alert_routes:
        combined_lines = ["✈️ FLIGHT PRICE ALERT\n"]
        for route, decision, best_offer in alert_routes:
            combined_lines.append(_format_alert(route, decision, best_offer))
            combined_lines.append("")

        combined_body = "\n\n".join(combined_lines).strip()
        send_email(
            subject="Flight price alert: combined update",
            body=combined_body,
        )
        send_telegram(
            message=combined_body,
        )

    if not args.demo and missing_routes:
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
