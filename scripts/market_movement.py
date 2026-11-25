import json
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict
from statistics import median

SOURCE = Path("extra_market_archive.json")
OUTPUT = Path("market_movement.json")

MIN_BOOKMAKERS = 3
MIN_CHANGE_PP = 1.0


def parse_time(value):
    return datetime.fromisoformat(
        value.replace("Z", "+00:00")
    )


def run():
    now = datetime.now(timezone.utc)

    report = {
        "version": "4.11",
        "updatedAt": now.isoformat(),
        "mode": "research_only",
        "decision": "PAS",
        "eventCount": 0,
        "markets": [],
        "errors": []
    }

    groups = defaultdict(list)

    if not SOURCE.exists():
        report["errors"].append("missing_archive")
    else:
        archive = json.loads(
            SOURCE.read_text(encoding="utf-8")
        )

        for record in archive["records"].values():
            if parse_time(record["kickoff"]) <= now:
                continue

            key = (
                record["eventId"],
                record["market"]
            )

            groups[key].append(record)

    for (event_id, market), records in groups.items():
        ready = {}

        for record in records:
            history = record.get("history", [])

            if len(history) < 2:
                continue

            history = sorted(
                history,
                key=lambda h: parse_time(h["lastUpdate"])
            )

            first = history[0]
            latest = history[-1]

            first_time = parse_time(first["lastUpdate"])
            last_time = parse_time(latest["lastUpdate"])

            if last_time <= first_time:
                continue

            age = (now - last_time).total_seconds()

            if not 0 <= age <= 1800:
                continue

            change = (
                latest["marketProbability"]
                - first["marketProbability"]
            ) * 100

            ready[record["bookmaker"]] = change

        changes = list(ready.values())

        rising = sum(
            x >= MIN_CHANGE_PP for x in changes
        )

        falling = sum(
            x <= -MIN_CHANGE_PP for x in changes
        )

        direction = "INSUFFICIENT_DATA"

        if len(changes) >= MIN_BOOKMAKERS:
            direction = "MIXED_OR_STABLE"

            if rising / len(changes) >= 0.75:
                direction = "PROBABILITY_UP"

            elif falling / len(changes) >= 0.75:
                direction = "PROBABILITY_DOWN"

        report["markets"].append({
            "eventId": event_id,
            "home": records[0]["home"],
            "away": records[0]["away"],
            "kickoff": records[0]["kickoff"],
            "market": market,
            "bookmakers": len(records),
            "movementBookmakers": len(changes),
            "rising": rising,
            "falling": falling,
            "medianChangePP": (
                round(median(changes), 4)
                if changes else None
            ),
            "direction": direction,
            "bookmakerChangesPP": ready,
            "decision": "PAS"
        })

    report["eventCount"] = len({
        row["eventId"]
        for row in report["markets"]
    })

    report["marketCount"] = len(report["markets"])

    temp = OUTPUT.with_suffix(".tmp")

    temp.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    temp.replace(OUTPUT)

    print("V4.11 market movement")
    print("Events:", report["eventCount"])
    print("Markets:", report["marketCount"])
    print("Decision: PAS")


if __name__ == "__main__":
    run()
