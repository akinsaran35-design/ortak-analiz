
import json
import math
from pathlib import Path
from datetime import datetime, timezone

SOURCE = Path("extra_markets.json")
ARCHIVE = Path("extra_market_archive.json")


def parse_time(value):
    return datetime.fromisoformat(
        value.replace("Z", "+00:00")
    )


def run():
    report = json.loads(
        SOURCE.read_text(encoding="utf-8")
    )

    if (
        report.get("source") != "The Odds API"
        or report.get("region") != "uk"
        or report.get("errors") != []
        or report.get("mode") != "research_only"
    ):
        print("PAS: invalid pilot report")
        return

    stamp = report["updatedAt"]
    captured = parse_time(stamp)

    age = (
        datetime.now(timezone.utc) - captured
    ).total_seconds()

    if not 0 <= age <= 1800:
        print("PAS: stale pilot report")
        return

    archive = (
        json.loads(ARCHIVE.read_text(encoding="utf-8"))
        if ARCHIVE.exists()
        else {"version": "4.10", "records": {}}
    )

    records = archive["records"]
    added = 0

    for event in report["events"]:
        kickoff = parse_time(event["kickoff"])

        if captured >= kickoff:
            continue

        for market, names in (
            ("over15", ("Over", "Under")),
            ("btts", ("Yes", "No"))
        ):
            for book in event.get(market, []):
                prices = book["prices"]

                if not all(
                    isinstance(prices.get(n), (int, float))
                    and math.isfinite(prices[n])
                    and prices[n] > 1
                    for n in names
                ):
                    continue

                updated = parse_time(book["lastUpdate"])

                if not 0 <= (
                    captured - updated
                ).total_seconds() <= 1800:
                    continue

                record_id = "|".join([
                    event["id"],
                    market,
                    book["bookmaker"]
                ])

                record = records.setdefault(
                    record_id, {
                        "eventId": event["id"],
                        "league": event["league"],
                        "home": event["home"],
                        "away": event["away"],
                        "kickoff": event["kickoff"],
                        "market": market,
                        "bookmaker": book["bookmaker"],
                        "history": []
                    }
                )

                history = record["history"]

                if any(
                    h["lastUpdate"] == book["lastUpdate"]
                    for h in history
                ):
                    continue

                probability = (
                    1 / prices[names[0]]
                ) / sum(1 / prices[n] for n in names)

                history.append({
                    "capturedAt": stamp,
                    "lastUpdate": book["lastUpdate"],
                    "prices": prices,
                    "marketProbability": round(
                        probability, 6
                    )
                })

                history.sort(
                    key=lambda h: parse_time(h["lastUpdate"])
                )

                first = history[0]
                latest = history[-1]

                record["firstObserved"] = first
                record["latestObserved"] = latest

                initial = first["prices"][names[0]]
                current = latest["prices"][names[0]]

                record["oddsChangePct"] = round(
                    (current / initial - 1) * 100, 4
                )

                record["probabilityChangePP"] = round(
                    (
                        latest["marketProbability"]
                        - first["marketProbability"]
                    ) * 100, 4
                )

                record["movementReady"] = len(history) >= 2
                added += 1

    archive["updatedAt"] = datetime.now(
        timezone.utc
    ).isoformat()

    archive["mode"] = "research_only"
    archive["decision"] = "PAS"
    archive["recordCount"] = len(records)

    temp = ARCHIVE.with_suffix(".tmp")
    temp.write_text(
        json.dumps(
            archive, ensure_ascii=False, indent=2
        ),
        encoding="utf-8"
    )
    temp.replace(ARCHIVE)

    print("Archive records:", len(records))
    print("New observations:", added)


if __name__ == "__main__":
    run()
