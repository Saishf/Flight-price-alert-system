# Flight Price Agent

A lightweight personal flight-price tracker for BLR -> ISK and BLR -> SAG based on the project plan in this repository.

## What it does

- Checks configured routes every run
- Uses SerpApi Google Flights as the primary live source
- Keeps demo/sample results behind the explicit `--demo` flag
- Stores historical low prices in a local JSON history file
- Evaluates alerts for new all-time lows, target hits, big drops, spikes, and simple thresholds
- Sends optional email and Telegram notifications when alerts are triggered
- Works with GitHub Actions on an eight-hour schedule to stay inside the free quota

## Quick start

1. Create and activate a virtual environment
2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Run the tracker:

   ```bash
   python src/main.py --demo
   ```

4. For live checks, set these environment variables:

   ```bash
   export SERPAPI_API_KEY="..."
   export SMTP_USERNAME="..."
   export SMTP_PASSWORD="..."
   export EMAIL_TO="..."
   export TELEGRAM_BOT_TOKEN="..."
   export TELEGRAM_CHAT_ID="..."
   ```

5. Then run:

   ```bash
   python src/main.py
   ```

## Config

Edit [config.yaml](config.yaml) to change routes, target prices, and route labels.

## Project structure

- [src/main.py](src/main.py) - entry point
- [src/config.py](src/config.py) - YAML config loader
- [src/models.py](src/models.py) - normalized flight offer model
- [src/decision_engine.py](src/decision_engine.py) - price alert logic
- [src/price_store.py](src/price_store.py) - keeps JSON history
- [src/providers/serpapi_google_flights.py](src/providers/serpapi_google_flights.py) - SerpApi Google Flights provider
- [src/providers/trip.py](src/providers/trip.py) - experimental Trip.com browser provider
- [src/providers/amadeus.py](src/providers/amadeus.py) - demo/sample provider
- [src/notifications/email.py](src/notifications/email.py) - email alert sender
- [src/notifications/telegram.py](src/notifications/telegram.py) - Telegram bot sender

## Notes

This is a practical MVP, not a substitute for official rate parity or airline booking checks. The tracker records observed fares and notifies on threshold conditions; it does not claim a fare is guaranteed bookable until rechecked.
