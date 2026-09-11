from src.models import RouteConfig
from src.providers.serpapi_google_flights import SerpApiGoogleFlightsProvider


def test_serpapi_google_flights_parser_normalizes_offer():
    provider = SerpApiGoogleFlightsProvider(api_key="test")
    route = RouteConfig(
        origin="BLR",
        destination="ISK",
        date="2026-11-07",
        target_price=7500,
        label="BLR -> ISK",
    )

    data = {
        "best_flights": [
            {
                "flights": [
                    {
                        "departure_airport": {"id": "BLR", "time": "2026-11-07 14:15"},
                        "arrival_airport": {"id": "ISK", "time": "2026-11-07 16:05"},
                        "airline": "IndiGo",
                        "flight_number": "6E 6547",
                        "extensions": ["Checked baggage for a fee"],
                    }
                ],
                "total_duration": 110,
                "price": 10068,
                "type": "One way",
                "booking_token": "hidden",
            }
        ],
        "other_flights": [],
    }

    offers = provider._parse(data, route)

    assert len(offers) == 1
    assert offers[0].source == "serpapi_google_flights"
    assert offers[0].airline == "IndiGo"
    assert offers[0].flight_numbers == ["6E 6547"]
    assert offers[0].price == 10068
    assert offers[0].stops == 0
