import json
import math
from pathlib import Path
from datetime import datetime, timezone, timedelta
from statistics import median
from collections import Counter
from match_odds import canonical
from league_config import ODDS_CODES

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
    t=datetime.fromisoformat(value.replace("Z","+00:00"))
    if t.tzinfo is None:raise ValueError("timezone required")
    return t

def fresh(value, now):
    try:
        age = (now - parse_time(value)).total_seconds()
        return 0 <= age <= MAX_AGE
    except (ValueError, TypeError, AttributeError):
        return False

def valid_price(value):
    return (
        type(value) in (int, float)
        and math.isfinite(value)
        and value > 1
    )

def compare_market(probability, quotes, now):
    books = {}
    counts=Counter(q.get('bookmaker') for q in quotes if isinstance(q,dict) and isinstance(q.get('bookmaker'),str))

    for quote in quotes:
        try:
            key = quote["bookmaker"]
            a = quote["positive"]
            b = quote["negative"]

            if not isinstance(key,str) or not key or counts[key]!=1 or not fresh(
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

    if type(probability) not in (int,float) or not math.isfinite(probability):
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

def objects(rows):
    return [r for r in rows if isinstance(r,dict)] if isinstance(rows,list) else []

def unique_events(rows):
    rows=objects(rows)
    counts=Counter(e.get("id") for e in rows if isinstance(e.get("id"),str))
    return {e["id"]:e for e in rows if isinstance(e.get("id"),str) and e["id"] and counts[e["id"]]==1}

def identity_matches(a,b):
    try:
        return all(isinstance(a[k],str) and a[k] and a[k]==b[k] for k in ("id","league","home","away")) and parse_time(a["kickoff"])==parse_time(b["kickoff"])
    except (KeyError,ValueError,TypeError,AttributeError):return False

def extra_bound(extra,odds,archive,now):
    return (isinstance(archive,dict) and archive.get("integrityVersion")=="6.85" and archive.get("mode")=="research_only"
        and isinstance(archive.get("quarantine"),dict)
        and fresh(archive.get("updatedAt"),now)
        and extra.get("quotaPolicyVersion")=="6.89" and extra.get("integrityVersion")=="6.84"
        and extra.get("source")=="The Odds API" and extra.get("region")=="uk"
        and extra.get("mode")=="research_only" and extra.get("decision")=="PAS"
        and extra.get("errors")==[] and fresh(extra.get("updatedAt"),now)
        and extra.get("oddsSnapshotAt")==odds.get("updatedAt")
        and fresh(odds.get("updatedAt"),now))

def quotes_for(event,market,stamp,extra=False):
    out=[]
    if extra:
        names=("Over","Under") if market=="over15" else ("Yes","No")
        for b in objects(event.get(market)):
            p=b.get("prices")
            if not isinstance(p,dict) or set(p)!=set(names):continue
            out.append(dict(bookmaker=b.get("bookmaker"),positive=p[names[0]],negative=p[names[1]],lastUpdate=b.get("lastUpdate")))
    else:
        point=1.5 if market=="over15" else 2.5
        books=objects(event.get("bookmakers"))
        counts=Counter(b.get("key") for b in books if isinstance(b.get("key"),str))
        for b in books:
            k=b.get("key")
            if not isinstance(k,str) or counts[k]!=1:continue
            lines=[l for l in objects(b.get("lines")) if l.get("point")==point]
            if len(lines)!=1:continue
            l=lines[0]
            out.append(dict(bookmaker=k,positive=l.get("over"),negative=l.get("under"),lastUpdate=l.get("lastUpdate")))
    return [q for q in out if fresh(q["lastUpdate"],parse_time(stamp))]

def main():
    now = datetime.now(timezone.utc)
    report = {
        "version": "4.12",
        "evidenceVersion":"6.92",
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
        try:archive=load("extra_market_archive.json")
        except (OSError,ValueError):archive={}

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
            and odds.get("market") == "totals"
            and odds.get("errors") == []
            and fresh(odds.get("updatedAt"), now)
        ):
            base_events=unique_events(odds.get("events"))

        if base_events and extra_bound(extra,odds,archive,now):
            extra_events={k:e for k,e in unique_events(extra.get("events")).items()
                if k in base_events and identity_matches(e,base_events[k]) and k not in archive["quarantine"]}

        moves = {}

        if (
            movement.get("evidenceVersion")=="6.91"
            and movement.get("errors") == []
            and fresh(movement.get("updatedAt"), now)
        ):
            moves = {
                (m["eventId"], m["market"]): m
                for m in movement["markets"]
            }

        matched=objects(matching.get("matched"))
        matched_counts=Counter(m.get("eventId") for m in matched if isinstance(m.get("eventId"),str))
        for match in matched:
            event_id = match["eventId"]
            if matched_counts[event_id]!=1:
                reject("ambiguous_matched_event");continue
            base=base_events.get(event_id)
            if not base:
                reject("missing_base_event");continue
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

            league=ODDS_CODES.get(candidate.get("league"))
            teams=candidate["match"].split(" – ")
            if (not league or len(teams)!=2 or base.get("league")!=league
                or parse_time(base["kickoff"])!=kickoff
                or canonical(base["home"],league)!=canonical(teams[0],league)
                or canonical(base["away"],league)!=canonical(teams[1],league)):
                reject("identity_mismatch");continue
            if candidate.get("date") != str(local_date):
                reject("date_mismatch")
                continue

            for market, label in MARKETS.items():
                sources=[]
                if market in ("over15","over25"):
                    sources.append(("base_totals",quotes_for(base,market,odds["updatedAt"])))
                if market in ("over15","btts") and event_id in extra_events:
                    sources.append(("extra_markets",quotes_for(extra_events[event_id],market,extra["updatedAt"],extra=True)))

                probability = candidate.get(
                    "markets", {}
                ).get(label)

                if type(probability) not in (int,float):
                    reject("missing_model_probability")
                    continue

                # Never mix separately captured snapshots or double-count the same bookmaker.
                comparisons=[(source,compare_market(probability/100,quotes,now)) for source,quotes in sources]
                valid=[(source,r) for source,r in comparisons if r is not None]
                result_source,result=max(valid,key=lambda item:item[1]["bookCount"]) if valid else (None,None)

                if result is None:
                    reject("insufficient_valid_market_data")
                    continue

                move = moves.get((event_id, market), {})
                if (move.get("league")!=league or move.get("home")!=base.get("home") or move.get("away")!=base.get("away") or move.get("kickoff")!=base.get("kickoff") or event_id in archive.get("quarantine",{})):
                    move={}
                if move.get("movementBookmakers",0)<3:move={}

                report["rows"].append({
                    "eventId": event_id,
                    "match": match["match"],
                    "kickoff": match["kickoff"],
                    "market": market,
                    "marketLabel": label,
                    "oddsEvidenceSource":result_source,
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
