
import json
import math
from collections import Counter
from pathlib import Path
from datetime import datetime, timezone

SOURCE = Path("extra_markets.json")
ARCHIVE = Path("extra_market_archive.json")


def parse_time(value):
    t=datetime.fromisoformat(value.replace("Z","+00:00"))
    if t.tzinfo is None:raise ValueError("timezone required")
    return t


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
    quarantine=archive.setdefault("quarantine",{})
    raw=report["events"]
    if not isinstance(raw,list) or not isinstance(records,dict) or not isinstance(quarantine,dict):
        raise ValueError("archive schema")
    counts=Counter(e.get("id") for e in raw if isinstance(e,dict) and isinstance(e.get("id"),str))
    for event in raw:
        if not isinstance(event,dict):continue
        if not all(isinstance(event.get(k),str) and event[k].strip() and "|" not in event[k] for k in ("id","league","home","away")) or event["home"]==event["away"]:continue
        if counts[event["id"]]!=1 or event["id"] in quarantine:continue
        try:kickoff=parse_time(event["kickoff"])
        except (KeyError,ValueError,TypeError,AttributeError):continue
        # One event ID cannot be reused across teams, leagues or kickoff times.
        try:
            conflict=any(r["eventId"]==event["id"] and (
                (r["league"],r["home"],r["away"])!=(event["league"],event["home"],event["away"])
                or parse_time(r["kickoff"])!=kickoff) for r in records.values())
        except (KeyError,ValueError,TypeError,AttributeError):raise ValueError("invalid existing archive identity")
        if conflict:
            quarantine[event["id"]]=dict(reason="event_identity_conflict",detectedAt=stamp)
            continue

        if captured >= kickoff:
            continue

        for market, names in (
            ("over15", ("Over", "Under")),
            ("btts", ("Yes", "No"))
        ):
            books=event.get(market,[])
            if not isinstance(books,list):continue
            counts_books=Counter(b.get("bookmaker") for b in books if isinstance(b,dict) and isinstance(b.get("bookmaker"),str))
            for book in books:
                if not isinstance(book,dict):continue
                key=book.get("bookmaker")
                if not isinstance(key,str) or not key or "|" in key or counts_books[key]!=1:continue
                prices=book.get("prices")
                if not isinstance(prices,dict) or set(prices)!=set(names):continue

                if not all(
                    type(prices.get(n)) in (int, float)
                    and math.isfinite(prices[n])
                    and prices[n] > 1
                    for n in names
                ):
                    continue

                try:updated=parse_time(book["lastUpdate"])
                except (KeyError,ValueError,TypeError,AttributeError):continue

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

                same=[h for h in history if parse_time(h["lastUpdate"])==updated]
                if same:
                    if len(same)!=1 or same[0]["prices"]!=prices:
                        quarantine[event["id"]]=dict(reason="same_timestamp_price_conflict",detectedAt=stamp)
                    continue
                if event["id"] in quarantine:continue

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
    archive["integrityVersion"]="6.85"
    archive["quarantinedEvents"]=len(quarantine)

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
