from src.decision_engine import DecisionEngine
from src.main import pick_best_offer
from src.models import FlightOffer


def test_pick_best_offer_prefers_nonstop_even_if_more_expensive():
    offers = [
        FlightOffer(source="x", origin="BLR", destination="ISK", date="2026-11-07", airline="Airline A", stops=1, price=5000, duration_minutes=180),
        FlightOffer(source="x", origin="BLR", destination="ISK", date="2026-11-07", airline="Airline B", stops=0, price=6200, duration_minutes=120),
    ]

    best = pick_best_offer(offers)

    assert best.stops == 0
    assert best.price == 6200


def test_new_all_time_low_detected():
    engine = DecisionEngine()

    # current price is a new historical minimum
    result = engine.evaluate(
        route="BLR -> ISK",
        current_price=8420,
        previous_price=9100,
        historical_min=9000,
    )

    assert result["alert"] is True
    assert result["reason"] == "new_all_time_low"


def test_significant_drop_detected():
    engine = DecisionEngine()

    result = engine.evaluate(
        route="BLR -> ISK",
        current_price=8900,
        previous_price=10068,
        historical_min=8900,
    )

    assert result["alert"] is True
    assert result["reason"] == "significant_drop"


def test_no_alert_when_price_is_stable():
    engine = DecisionEngine()

    result = engine.evaluate(
        route="BLR -> ISK",
        current_price=9500,
        previous_price=9600,
        historical_min=9000,
    )

    assert result["alert"] is False
    assert result["reason"] == "no_alert"
