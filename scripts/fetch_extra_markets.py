
import json
import os
import urllib.request
import urllib.parse
from urllib.error import HTTPError
from datetime import datetime, timezone
from pathlib import Path

MAX_EVENTS = 3
RESERVE = 20
MAX_AGE = 1800

key = os.environ.get("ODDS_API_KEY", "").strip()
now = datetime.now(timezone.utc)

report = {
    "version": "4.9-pilot",
    "updatedAt": now.isoformat(),
    "source": "The Odds API",
    "region": "uk",
    "mode": "research_only",
    "decision": "PAS",
    "remainingCredits": None,
    "events": [],
    "errors": []
}

def parse_time(value):
    return datetime.fromisoformat(
        value.replace("Z", "+00:00")
    )

def request(path, params):
    query = urllib.parse.urlencode({
        "apiKey": key,
        **params
    })
    url = (
        "https://api.the-odds-api.com/v4/"
        + path + "?" + query
    )

    with urllib.request.urlopen(
        url, timeout=20
    ) as response:
        remaining = response.headers.get(
            "x-requests-remaining", ""
        )
        report["remainingCredits"] = (
            int(remaining)
            if remaining.isdigit()
            else None
        )
        return json.load(response)

def extract_market(event, market_key, names):
    results = {}

    for book in event.get("bookmakers", []):
        for market in book.get("markets", []):
            if market.get("key") != market_key:
                continue

            stamp = (
                market.get("last_update")
                or book.get("last_update")
            )

            try:
                age = (
                    datetime.now(timezone.utc)
                    - parse_time(stamp)
                ).total_seconds()

                if not 0 <= age <= MAX_AGE:
                    continue
            except (ValueError, TypeError, AttributeError):
                continue

            prices = {}

            for outcome in market.get("outcomes", []):
                if market_key == "alternate_totals":
                    if outcome.get("point") != 1.5:
                        continue

                name = outcome.get("name")
                price = outcome.get("price")

                if (
                    name in names
                    and isinstance(price, (int, float))
                    and price > 1
                ):
                    prices[name] = price

            if not all(n in prices for n in names):
                continue

            total = sum(1 / prices[n] for n in names)

            book_key = book.get("key")
            if not book_key:
                continue

            results[book_key] = {
                "bookmaker": book_key,
                "prices": prices,
                "lastUpdate": stamp,
                "marketProbability": round(
                    (1 / prices[names[0]]) / total, 6
                )
            }

    return list(results.values())

def run():
    if not key:
        report["errors"].append("missing_key")
        return

    snapshot = json.loads(
        Path("odds.json").read_text(encoding="utf-8")
    )

    age = (
        now - parse_time(snapshot["updatedAt"])
    ).total_seconds()

    if not 0 <= age <= MAX_AGE:
        report["errors"].append("stale_snapshot")
        return

    if (
        snapshot.get("source") != "The Odds API"
        or snapshot.get("region") != "uk"
        or snapshot.get("errors") != []
    ):
        report["errors"].append("invalid_snapshot")
        return

    request("sports/", {})

    candidates = sorted(
        snapshot.get("events", []),
        key=lambda e: parse_time(e["kickoff"])
    )

    checked = set()

    for event in candidates:
        if len(checked) >= MAX_EVENTS:
            break

        if parse_time(event["kickoff"]) <= datetime.now(timezone.utc):
            continue

        event_id = event["id"]
        league = event["league"]

        if event_id in checked:
            continue

        credits = report["remainingCredits"]

        if credits is None or credits < RESERVE + 2:
            report["errors"].append("quota_guard")
            break

        checked.add(event_id)

        try:
            data = request(
                f"sports/{league}/events/{event_id}/odds",
                {
                    "regions": "uk",
                    "markets": "alternate_totals,btts",
                    "oddsFormat": "decimal"
                }
            )

            over15 = extract_market(
                data, "alternate_totals",
                ("Over", "Under")
            )

            btts = extract_market(
                data, "btts", ("Yes", "No")
            )

            report["events"].append({
                "id": event_id,
                "league": league,
                "home": event["home"],
                "away": event["away"],
                "kickoff": event["kickoff"],
                "over15": over15,
                "btts": btts,
                "over15Bookmakers": len(over15),
                "bttsBookmakers": len(btts),
                "over15DataReady": len(over15) >= 3,
                "bttsDataReady": len(btts) >= 3,
                "decision": "PAS"
            })

        except HTTPError as exc:
            report["errors"].append(
                f"event_http_{exc.code}"
            )
            if exc.code in (401, 403, 429):
                break
        except Exception:
            report["errors"].append(
                "event_response_error"
            )
            break

try:
    run()
except HTTPError as exc:
    report["errors"].append(f"HTTP_{exc.code}")
except Exception:
    report["errors"].append("pilot_error")

report["eventCount"] = len(report["events"])

Path("extra_markets.json").write_text(
    json.dumps(
        report, ensure_ascii=False, indent=2
    ),
    encoding="utf-8"
)

print(
    "Extra market events:", report["eventCount"],
    "Credits:", report["remainingCredits"],
    "Errors:", report["errors"]
)
