# Flight Price Agent --- BLR → ISK / SAG --- 7 Nov 2026

## 1. Goal

Build a **zero-cost (or as close to zero-cost as possible) personal
flight-price agent** that checks:

-   **BLR → ISK (Nashik)** --- 7 Nov 2026
-   **BLR → SAG (Shirdi)** --- 7 Nov 2026
-   One-way
-   1 adult
-   Economy
-   Show both direct and 1-stop options when available
-   Ignore bank/credit-card/coupon offers
-   Compare the **actual displayed fare** and important fare conditions
-   Run automatically **every 6 hours**
-   Notify me when the price is lower than the previous check, reaches a
    target, or a particularly good option appears
-   Send the result by **email**. Telegram can be added as a free
    instant notification channel.
-   Keep a price history so the agent can tell whether the fare is
    falling, rising, or stable.

### Important constraint

There is no official public Google Flights fare API. Google Flights
itself supports price tracking and email alerts, but programmatic access
normally requires either a third-party provider or web
automation/scraping. Therefore this project should use a **provider
abstraction** rather than hard-code one source.

For a free MVP:

1.  **Amadeus Self-Service API** = structured flight data
2.  **Google Flights / public search page via Playwright** = optional
    secondary source for broader fare discovery
3.  **GitHub Actions** = free scheduler/runner for a personal low-volume
    project
4.  **Git repository JSON/CSV** = free historical database
5.  **Gmail SMTP** = email notification
6.  **Telegram Bot API** = optional free push notification

Amadeus provides a monthly free request quota, including in production,
but its Self-Service data has limitations: it returns published GDS
rates and does not include every low-cost carrier. Therefore it should
**not** be treated as the only source when the goal is the absolute
cheapest fare.

------------------------------------------------------------------------

# 2. Recommended architecture

``` text
                         ┌──────────────────────────┐
                         │     GitHub Actions       │
                         │      every 6 hours       │
                         └────────────┬─────────────┘
                                      │
                                      ▼
                         ┌──────────────────────────┐
                         │       run_tracker.py     │
                         └────────────┬─────────────┘
                                      │
                  ┌───────────────────┼───────────────────┐
                  ▼                   ▼                   ▼
        ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
        │ Amadeus Provider│  │ Google Flights  │  │ Airline/OTA     │
        │   (structured)  │  │   Playwright    │  │ provider later  │
        └────────┬────────┘  └────────┬────────┘  └────────┬────────┘
                 │                    │                    │
                 └────────────────────┼────────────────────┘
                                      ▼
                           ┌─────────────────────┐
                           │ normalize_offers.py │
                           └──────────┬──────────┘
                                      ▼
                           ┌─────────────────────┐
                           │     price_store     │
                           │  prices.json / CSV  │
                           └──────────┬──────────┘
                                      ▼
                           ┌─────────────────────┐
                           │   decision_engine   │
                           │                     │
                           │ New low?            │
                           │ Target hit?         │
                           │ Good vs history?    │
                           │ Price rising?       │
                           └──────────┬──────────┘
                                      ▼
                         ┌─────────────────────────┐
                         │       notifier.py       │
                         ├─────────────┬───────────┤
                         ▼             ▼           │
                       Email        Telegram       │
                         │             │            │
                         └─────────────┴────────────┘
```

------------------------------------------------------------------------

# 3. Why this design

Do **not** make the project one giant scraper.

Instead, define a common internal flight-offer format:

``` python
FlightOffer(
    source="amadeus",
    origin="BLR",
    destination="ISK",
    date="2026-11-07",
    airline="6E",
    flight_numbers=["6E..."],
    departure="14:00",
    arrival="15:50",
    stops=0,
    duration_minutes=110,
    price=10068,
    currency="INR",
    baggage=None,
    booking_url=None,
)
```

Then every provider converts its own response into this structure.

This means that if one website changes its HTML, you only repair that
provider.

------------------------------------------------------------------------

# 4. Routes

``` yaml
routes:
  - origin: BLR
    destination: ISK
    date: 2026-11-07

  - origin: BLR
    destination: SAG
    date: 2026-11-07
```

Keep the destination airport codes explicit.

Do not silently substitute Mumbai/Pune/Aurangabad/etc. unless a future
configuration explicitly enables nearby-airport alternatives.

------------------------------------------------------------------------

# 5. What the agent should report

Every check should collect as much of this as the source provides:

  Field          Example
  -------------- --------------------------
  Route          BLR → ISK
  Date           7 Nov 2026
  Airline        IndiGo
  Flight         6E...
  Departure      14:00
  Arrival        15:50
  Duration       1h 50m
  Stops          Nonstop
  Price          ₹10,068
  Currency       INR
  Baggage        15 kg / unknown
  Fare type      Saver / published fare
  Source         Trip/Google/Amadeus/etc.
  Booking URL    source booking link
  Checked at     timestamp
  Price change   -₹500
  Lowest seen    ₹9,200

### Important

Do not call a price "bookable" merely because an aggregator showed it.

Before the user books, the agent should label it:

-   `observed`
-   `price_requires_recheck`
-   `confirmed_by_price_endpoint`
-   `unknown`

Prices can change between search and checkout.

------------------------------------------------------------------------

# 6. Notification rules

Do not send a notification every six hours just because the job ran.

Send an alert only when one of these happens:

### Rule A --- New all-time low

``` text
Current price < historical minimum
```

### Rule B --- Target price hit

Initial example:

``` text
ISK target = ₹7,500
SAG target = ₹7,500
```

Make these configurable.

### Rule C --- Significant drop

``` text
Current price <= previous_price * 0.90
```

Example:

``` text
₹10,068 → ₹8,900
```

= 11.6% drop → alert.

### Rule D --- New good option

Example:

``` text
A nonstop flight appears that wasn't available previously.
```

### Rule E --- Price spike

Useful because it tells you that waiting may be dangerous.

``` text
current_price >= previous_price * 1.15
```

Send:

> ⚠️ BLR → ISK jumped from ₹7,200 to ₹8,400.

------------------------------------------------------------------------

# 7. Example notification

``` text
✈️ FLIGHT PRICE ALERT

BLR → ISK
7 Nov 2026
1 adult · Economy · One-way

🔥 NEW LOW

IndiGo
14:00 → 15:50
Nonstop
₹8,420

Previous: ₹9,100
Drop: ₹680 (-7.5%)

Lowest ever seen: ₹8,420

Source: Google Flights / Amadeus
Checked: 11 Sep 2026 18:00 IST

Book/check price:
<booking URL>
```

For multiple options:

``` text
✈️ BLR → ISK / SAG
7 Nov 2026

NASHIK
1. IndiGo — Nonstop — ₹8,420
2. IndiGo — 1 stop — ₹7,950

SHIRDI
1. Air India Express — 1 stop — ₹7,820
2. IndiGo — 1 stop — ₹8,100

🔥 Cheapest overall: BLR → SAG ₹7,820

No bank/credit-card offers included.
```

------------------------------------------------------------------------

# 8. Six-hour schedule

Run:

``` text
00:00
06:00
12:00
18:00
```

IST.

However, GitHub Actions cron uses UTC.

India is UTC+5:30.

So an approximate UTC schedule is:

``` yaml
schedule:
  - cron: "30 0,6,12,18 * * *"
```

That gives approximately:

``` text
06:00 IST
12:00 IST
18:00 IST
00:00 IST
```

GitHub Actions scheduled workflows can be delayed occasionally, so treat
this as "roughly every six hours", not a guaranteed exact clock.

------------------------------------------------------------------------

# 9. GitHub Actions

Repository:

``` text
flight-price-agent/
```

Structure:

``` text
flight-price-agent/
│
├── .github/
│   └── workflows/
│       └── flight-check.yml
│
├── src/
│   ├── main.py
│   ├── config.py
│   ├── models.py
│   ├── decision_engine.py
│   ├── price_store.py
│   │
│   ├── providers/
│   │   ├── __init__.py
│   │   ├── amadeus.py
│   │   └── google_flights.py
│   │
│   └── notifications/
│       ├── email.py
│       └── telegram.py
│
├── data/
│   └── prices.json
│
├── config.yaml
├── requirements.txt
├── README.md
└── plan.md
```

------------------------------------------------------------------------

# 10. GitHub Actions workflow

``` yaml
name: Flight Price Check

on:
  schedule:
    - cron: "30 0,6,12,18 * * *"
  workflow_dispatch:

jobs:
  check:
    runs-on: ubuntu-latest

    permissions:
      contents: write

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          playwright install chromium

      - name: Run tracker
        env:
          AMADEUS_CLIENT_ID: ${{ secrets.AMADEUS_CLIENT_ID }}
          AMADEUS_CLIENT_SECRET: ${{ secrets.AMADEUS_CLIENT_SECRET }}

          SMTP_USERNAME: ${{ secrets.SMTP_USERNAME }}
          SMTP_PASSWORD: ${{ secrets.SMTP_PASSWORD }}

          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
        run: python src/main.py

      - name: Commit price history
        run: |
          git config user.name "flight-price-agent"
          git config user.email "actions@users.noreply.github.com"
          git add data/prices.json
          git diff --cached --quiet || git commit -m "Update flight prices"
          git push
```

------------------------------------------------------------------------

# 11. Free data-source strategy

## Provider 1 --- Amadeus

Use:

``` text
Flight Offers Search
```

This gives structured flight offers and is much easier to work with than
HTML scraping.

Amadeus provides a free monthly request quota. Production keeps the free
quota, but calls above the quota can become billable, so configure a
hard safety limit in your own code.

Example:

``` python
MAX_API_CALLS_PER_DAY = 8
```

For two routes checked every six hours:

``` text
2 routes × 4 checks/day = 8 searches/day
≈ 240 searches/month
```

That is a relatively small workload, but verify your actual Amadeus
quota before enabling production.

### Important limitation

Amadeus does not represent every airline/low-cost fare. Its
documentation specifically says its Self-Service catalog returns
published GDS rates and excludes some low-cost carriers.

Therefore:

**Amadeus alone is not enough if your objective is "absolute cheapest
fare".**

------------------------------------------------------------------------

# 12. Provider 2 --- Google Flights web automation

Use Playwright only as a **secondary discovery provider**.

Conceptually:

``` python
browser = await chromium.launch()
page = await browser.new_page()

await page.goto(google_flights_url)

# wait for results
# extract visible flight cards
# parse airline / times / stops / price / link

await browser.close()
```

Do not try to bypass CAPTCHA or anti-bot protection.

If Google changes the page or blocks automated requests:

``` text
Google provider = unavailable
```

The agent should continue using Amadeus instead of crashing.

Also obey the website's applicable terms and access rules.

------------------------------------------------------------------------

# 13. Optional Provider 3 --- direct airline websites

For this particular route, add airline-specific providers only if
necessary.

Example:

``` text
providers/
    indigo.py
    air_india_express.py
```

Use these to verify the cheapest candidate.

The workflow becomes:

``` text
Find cheap candidate
        ↓
Check direct airline price
        ↓
If direct price is valid
        ↓
notify user
```

This is better than trusting a single aggregator.

------------------------------------------------------------------------

# 14. Do NOT use this approach

Avoid:

``` text
Scrape 10 websites every 6 hours
```

That sounds attractive but creates:

-   CAPTCHA problems
-   blocked IPs
-   changing HTML
-   duplicate fares
-   stale prices
-   terms-of-service issues
-   unnecessary requests

Instead:

``` text
2–3 providers
+
normalization
+
deduplication
+
price history
+
decision engine
```

------------------------------------------------------------------------

# 15. Deduplication

The same flight may appear on multiple sources.

Create a stable key:

``` python
key = (
    origin,
    destination,
    date,
    airline,
    flight_numbers,
    departure_time,
    arrival_time,
)
```

Then compare:

``` text
Google Flights      ₹10,068
Amadeus             ₹10,068
OTA                 ₹10,250
```

Store the itinerary once:

``` text
₹10,068
```

and keep the source list:

``` json
{
  "sources": [
    "google_flights",
    "amadeus"
  ]
}
```

------------------------------------------------------------------------

# 16. Price-history database

For the MVP, don't use PostgreSQL.

Use:

``` text
data/prices.json
```

Example:

``` json
{
  "BLR-ISK-2026-11-07": [
    {
      "checked_at": "2026-09-11T18:00:00+05:30",
      "price": 10068,
      "currency": "INR",
      "airline": "IndiGo",
      "stops": 0,
      "source": "google_flights"
    }
  ]
}
```

Later, if the project grows:

``` text
SQLite
```

is the best next step.

------------------------------------------------------------------------

# 17. Agent logic

The "AI" part does not need an LLM initially.

Use deterministic logic first.

``` python
def classify(current, previous, lowest_seen):

    if current < lowest_seen:
        return "NEW_LOW"

    if current <= previous * 0.90:
        return "BIG_DROP"

    if current >= previous * 1.15:
        return "PRICE_SPIKE"

    return "NO_ALERT"
```

This is cheaper, faster and more reliable than using an LLM for every
six-hour check.

------------------------------------------------------------------------

# 18. Add AI later

Once enough history exists, an LLM can analyze:

``` text
Current price
7-day history
30-day history
Lowest observed
Highest observed
Number of days until flight
Recent price direction
```

Then ask:

``` text
Should I buy now or wait?

Return:
- BUY
- WAIT
- WATCH
- confidence
- reason
```

But this is optional.

The flight price data collection should work without an AI API.

------------------------------------------------------------------------

# 19. Notifications

## Option A --- Email (recommended for completely free MVP)

Use Gmail SMTP.

Secrets:

``` text
SMTP_USERNAME
SMTP_PASSWORD
ALERT_EMAIL
```

Use a Gmail App Password rather than your normal Gmail password.

Send HTML email:

``` text
Subject:
🔥 Flight price dropped — BLR → ISK — ₹8,420

Body:
...
```

------------------------------------------------------------------------

## Option B --- Telegram (recommended push channel)

Create a Telegram bot using BotFather.

Then:

``` text
TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID
```

Call:

``` text
https://api.telegram.org/bot<TOKEN>/sendMessage
```

Telegram's Bot API is free to use for this type of personal bot.

This is much easier to keep free than WhatsApp automation.

------------------------------------------------------------------------

# 20. WhatsApp

Do **not** build this around unofficial WhatsApp Web automation.

It can break and can put the account at risk.

If WhatsApp is mandatory, use the official WhatsApp Business/Cloud API
and verify its current pricing and messaging rules before
implementation.

For the free MVP:

``` text
Email + Telegram
```

is the recommended combination.

------------------------------------------------------------------------

# 21. Web dashboard

You do not actually need a website for version 1.

GitHub Actions + email/Telegram is enough.

But if you want a dashboard later:

``` text
Frontend:
    Next.js / React

Hosting:
    GitHub Pages / Cloudflare Pages

Data:
    prices.json

Charts:
    Chart.js

Backend:
    GitHub Actions
```

Dashboard:

``` text
┌─────────────────────────────────────┐
│ Flight Price Agent                  │
├─────────────────────────────────────┤
│ BLR → ISK · 7 Nov 2026              │
│                                     │
│ Current lowest       ₹8,420         │
│ Lowest ever          ₹8,420         │
│ Target               ₹7,500         │
│ Trend                ↓ Falling      │
│                                     │
│ [ View all flights ]                │
└─────────────────────────────────────┘
```

------------------------------------------------------------------------

# 22. Config file

Create `config.yaml`:

``` yaml
settings:
  currency: INR
  passengers: 1
  cabin: ECONOMY
  trip_type: ONE_WAY
  check_interval_hours: 6

notifications:
  email: true
  telegram: true

alerts:
  percent_drop: 10
  price_spike_percent: 15

routes:
  - name: "Nashik"
    origin: BLR
    destination: ISK
    date: "2026-11-07"
    target_price: 7500

  - name: "Shirdi"
    origin: BLR
    destination: SAG
    date: "2026-11-07"
    target_price: 7500
```

------------------------------------------------------------------------

# 23. Environment secrets

Never put these in Git:

``` text
AMADEUS_CLIENT_ID
AMADEUS_CLIENT_SECRET

SMTP_USERNAME
SMTP_PASSWORD

TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID
```

Use GitHub repository secrets.

Do not commit `.env`.

------------------------------------------------------------------------

# 24. requirements.txt

Initial version:

``` text
requests
PyYAML
python-dateutil
playwright
beautifulsoup4
lxml
```

Optional:

``` text
amadeus
```

You can use raw HTTP requests instead of the Amadeus Python SDK if you
want fewer dependencies.

------------------------------------------------------------------------

# 25. Development phases

## Phase 1 --- MVP

Goal: get a notification working.

Build:

``` text
config.yaml
        ↓
Amadeus search
        ↓
find cheapest
        ↓
email
```

No AI.

No website.

No scraping.

------------------------------------------------------------------------

## Phase 2 --- Price history

Add:

``` text
prices.json
```

Store every result.

Then calculate:

``` text
previous price
lowest price
highest price
average
percentage change
```

------------------------------------------------------------------------

## Phase 3 --- Second data source

Add:

``` text
Google Flights Playwright provider
```

Only if needed and allowed.

Compare:

``` text
Amadeus
vs
Google Flights
```

------------------------------------------------------------------------

## Phase 4 --- Telegram

Add instant Telegram alerts.

------------------------------------------------------------------------

## Phase 5 --- Decision engine

Add:

``` text
NEW LOW
TARGET HIT
BIG DROP
PRICE SPIKE
```

------------------------------------------------------------------------

## Phase 6 --- Dashboard

Only after the backend works.

------------------------------------------------------------------------

# 26. Suggested alert strategy for your actual trip

Because your date is fixed:

``` text
BLR → ISK
BLR → SAG

7 Nov 2026
```

I would use:

``` text
Target:
₹7,500

Strong buy:
≤ ₹7,000

Very strong buy:
≤ ₹6,500

Current observed benchmark:
~₹10,000
```

These thresholds are configuration values, not predictions.

The agent should ultimately decide based on the historical data it
collects.

------------------------------------------------------------------------

# 27. Extra useful feature: "all options"

Every notification should have two sections:

### Cheapest overall

``` text
₹7,850 — BLR → SAG
1 stop
```

### Cheapest direct

``` text
₹9,200 — BLR → ISK
Nonstop
```

Then the user can decide whether saving ₹1,350 is worth taking a
connection.

Sort options by:

``` text
1. price
2. stops
3. duration
4. departure time
```

------------------------------------------------------------------------

# 28. Extra useful feature: nearby airport alternative

Keep this OFF initially.

Later add:

``` text
BLR → BOM
BLR → PNQ
BLR → IXU
```

and compare:

``` text
flight + ground travel cost
```

For example:

``` text
BLR → BOM flight
+
Mumbai → Nashik transport
```

The agent can then report:

``` text
ISK airport: ₹10,068

Alternative:
BLR → BOM: ₹4,800
Ground transport: ₹1,000
Total: ₹5,800

Potential saving: ₹4,268
```

This would make the agent substantially more useful.

------------------------------------------------------------------------

# 29. Important reliability rules

The agent must:

-   Never invent a flight.
-   Never treat a generic "from ₹X" price as the exact fare for 7 Nov.
-   Always attach the source.
-   Store the timestamp.
-   Clearly distinguish direct vs connecting.
-   Clearly distinguish base/displayed fare vs offer/coupon price.
-   Recheck the price before recommending booking.
-   Continue if one provider fails.
-   Never expose API secrets in logs.
-   Never bypass CAPTCHA or access controls.

------------------------------------------------------------------------

# 30. Definition of done

The MVP is complete when:

``` text
[✓] BLR → ISK configured
[✓] BLR → SAG configured
[✓] 7 Nov 2026 configured
[✓] One-way configured
[✓] 1 adult configured
[✓] Economy configured
[✓] Flight prices fetched
[✓] Price history stored
[✓] Lowest fare calculated
[✓] Previous fare compared
[✓] Every-6-hour GitHub Action configured
[✓] Email notification works
[✓] Optional Telegram notification works
[✓] No bank/CC offers used
[✓] Booking/source link included
[✓] Provider failures handled
```

------------------------------------------------------------------------

# 31. Recommended final stack

  -----------------------------------------------------------------------
  Component               Tool                    Cost
  ----------------------- ----------------------- -----------------------
  Code                    Python                  Free

  Repository              GitHub                  Free

  Scheduler               GitHub Actions          Free for a small
                                                  personal project

  Structured flight API   Amadeus Self-Service    Free monthly quota;
                                                  verify quota

  Secondary discovery     Playwright              Free

  Database                JSON → SQLite later     Free

  Email                   Gmail SMTP              Free

  Push                    Telegram Bot API        Free

  Dashboard               GitHub Pages /          Free
                          Cloudflare Pages        

  AI                      None initially          ₹0

  Hosting                 GitHub Actions          ₹0 for this scale
  -----------------------------------------------------------------------

**Target: ₹0/month**, provided you stay within the free quotas and do
not use paid API calls.

------------------------------------------------------------------------

# 32. Build order I recommend

Do this in exactly this order:

``` text
1. Create GitHub repo
2. Create Amadeus developer account
3. Test BLR → ISK API call
4. Test BLR → SAG API call
5. Create models.py
6. Create price_store.py
7. Create decision_engine.py
8. Create Gmail notifier
9. Run locally
10. Add GitHub Secrets
11. Add GitHub Actions cron
12. Confirm 6-hour execution
13. Add Telegram
14. Add second flight-data provider
15. Add dashboard
16. Add AI analysis only if useful
```

The most important principle:

> **Build the price collector first. Build the "agent" second.**

You don't need an expensive AI model to monitor flight prices. The hard
part is obtaining reliable, current fare data; once that works, the
alerting and decision layer is straightforward.
