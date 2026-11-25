import json
import math
from pathlib import Path
from datetime import datetime, timezone, timedelta
from statistics import median

MAX_AGE = 1800
MIN_BOOKS = 3

MARKETS = {
    "over15": "1.5 Üst",
    "over25": "2.5 Üst",
    "btts": "KG Var"
}

def load(name):
    return json.loads(
        Path(name).read_text(encoding="utf-8")
    )

def parse_time(value):
    return datetime.fromisoformat(
        value.replace("Z", "+00:00")
    )

def fresh(value, now):
    try:
        age = (now - parse_time(value)).total_seconds()
        return 0 <= age <= MAX_AGE
    except (ValueError, TypeError, AttributeError):
        return False

def valid_price(value):
    return (
        isinstance(value, (int, float))
        and math.isfinite(value)
        and value > 1
    )

def compare_market(probability, quotes, now):
    books = {}

    for quote in quotes:
        try:
            key = quote["bookmaker"]
            a = quote["positive"]
            b = quote["negative"]

            if not key or not fresh(
                quote["lastUpdate"], now
            ):
                continue

            if not valid_price(a) or not valid_price(b):
                continue

            total = 1 / a + 1 / b
            margin = total - 1

            if not 0 <= margin <= 0.20:
                continue

            books[key] = {
                "price": a,
                "probability": (1 / a) / total
            }

        except (KeyError, TypeError, ValueError):
            continue

    if len(books) < MIN_BOOKS:
        return None

    if not math.isfinite(probability):
        return None

    if not 0 <= probability <= 1:
        return None

    market = median(
        b["probability"] for b in books.values()
    )

    best = max(
        books, key=lambda k: books[k]["price"]
    )

    price = books[best]["price"]

    return {
        "bookCount": len(books),
        "modelProbabilityUncalibrated": round(probability, 6),
        "marketProbability": round(market, 6),
        "differencePP": round(
            (probability - market) * 100, 4
        ),
        "bestBookmaker": best,
        "bestOdds": price,
        "estimatedEV": round(
            probability * price - 1, 6
        ),
        "decision": "PAS"
    }

def main():
    now = datetime.now(timezone.utc)
    report = {
        "version": "4.12",
        "updatedAt": now.isoformat(),
        "mode": "research_only",
        "modelCalibrated": False,
        "decision": "PAS",
        "realBettingEnabled": False,
        "rows": [],
        "rejected": {},
        "errors": []
    }

    def reject(reason):
        counts = report["rejected"]
        counts[reason] = counts.get(reason, 0) + 1

    try:
        daily = load("daily.json")
        matching = load("matching.json")
        odds = load("odds.json")
        try:
            extra = load("extra_markets.json")
        except (OSError, ValueError):
            extra = {}
            reject("extra_report_unavailable")
        movement = load("market_movement.json")

        candidates = {}

        for c in daily["candidates"]:
            candidates.setdefault(
                c["match"], []
            ).append(c)

        base_events = {}
        extra_events = {}

        if (
            odds.get("source") == "The Odds API"
            and odds.get("region") == "uk"
            and odds.get("errors") == []
            and fresh(odds.get("updatedAt"), now)
        ):
            base_events = {
                e["id"]: e for e in odds["events"]
            }

        if (
            extra.get("source") == "The Odds API"
            and extra.get("region") == "uk"
            and extra.get("errors") == []
            and fresh(extra.get("updatedAt"), now)
        ):
            extra_events = {
                e["id"]: e for e in extra["events"]
            }

        moves = {}

        if (
            movement.get("errors") == []
            and fresh(movement.get("updatedAt"), now)
        ):
            moves = {
                (m["eventId"], m["market"]): m
                for m in movement["markets"]
            }

        for match in matching["matched"]:
            event_id = match["eventId"]
            cs = candidates.get(match["match"], [])

            if len(cs) != 1:
                reject("ambiguous_model_match")
                continue

            candidate = cs[0]
            kickoff = parse_time(match["kickoff"])

            if kickoff <= now:
                reject("already_started")
                continue

            local_date = (
                kickoff + timedelta(hours=3)
            ).date()

            today = (
                now + timedelta(hours=3)
            ).date()

            if local_date != today:
                reject("not_today")
                continue

            if candidate.get("date") != str(local_date):
                reject("date_mismatch")
                continue

            for market, label in MARKETS.items():
                quotes = []

                if market == "over25":
                    event = base_events.get(event_id, {})

                    if event.get("kickoff") != match["kickoff"]:
                        reject("missing_or_mismatched_base_event")
                        continue

                    for book in event.get("bookmakers", []):
                        for line in book.get("lines", []):
                            if line.get("point") == 2.5:
                                quotes.append({
                                    "bookmaker": book.get("key"),
                                    "positive": line.get("over"),
                                    "negative": line.get("under"),
                                    "lastUpdate": line.get("lastUpdate")
                                })
                else:
                    event = extra_events.get(event_id, {})

                    if event.get("kickoff") != match["kickoff"]:
                        reject("missing_or_mismatched_extra_event")
                        continue

                    names = (
                        ("Over", "Under")
                        if market == "over15"
                        else ("Yes", "No")
                    )

                    for book in event.get(market, []):
                        prices = book.get("prices", {})

                        quotes.append({
                            "bookmaker": book.get("bookmaker"),
                            "positive": prices.get(names[0]),
                            "negative": prices.get(names[1]),
                            "lastUpdate": book.get("lastUpdate")
                        })

                probability = candidate.get(
                    "markets", {}
                ).get(label)

                if not isinstance(probability, (int, float)):
                    reject("missing_model_probability")
                    continue

                result = compare_market(
                    probability / 100, quotes, now
                )

                if result is None:
                    reject("insufficient_valid_market_data")
                    continue

                move = moves.get((event_id, market), {})

                report["rows"].append({
                    "eventId": event_id,
                    "match": match["match"],
                    "kickoff": match["kickoff"],
                    "market": market,
                    "marketLabel": label,
                    **result,
                    "movementDirection": move.get("direction"),
                    "movementPP": move.get("medianChangePP"),
                    "movementBookmakers": move.get(
                        "movementBookmakers", 0
                    )
                })

    except Exception as exc:
        report["errors"].append(type(exc).__name__)
        report["rows"] = []

    report["rows"].sort(
        key=lambda r: r["estimatedEV"],
        reverse=True
    )

    report["comparedCount"] = len(report["rows"])

    Path("model_market.json").write_text(
        json.dumps(
            report, ensure_ascii=False, indent=2
        ),
        encoding="utf-8"
    )

    print("V4.12 comparisons:", report["comparedCount"])
    print("Errors:", report["errors"])
    print("Decision: PAS")

if __name__ == "__main__":
    main()
