import json
import math
from pathlib import Path
from datetime import datetime, timezone, timedelta
from statistics import median
from collections import Counter
from match_odds import canonical,LEAGUES

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

def unique_events(rows):
    if not isinstance(rows,list):return {}
    counts=Counter(e.get("id") for e in rows if isinstance(e,dict) and isinstance(e.get("id"),str))
    return {e["id"]:e for e in rows if isinstance(e,dict) and isinstance(e.get("id"),str) and e["id"] and counts[e["id"]]==1}

def same_fixture(a,b):
    try:
        return all(isinstance(a[k],str) and a[k] and a[k]==b[k] for k in ("id","league","home","away")) and parse_time(a["kickoff"])==parse_time(b["kickoff"])
    except (KeyError,ValueError,TypeError,AttributeError):return False

def bound_extra(odds,extra,archive,now):
    if (extra.get("source")!="The Odds API" or extra.get("region")!="uk" or extra.get("mode")!="research_only"
        or extra.get("quotaPolicyVersion")!="6.89" or extra.get("oddsSnapshotAt")!=odds.get("updatedAt")
        or extra.get("errors")!=[] or not fresh(extra.get("updatedAt"),now)
        or odds.get("source")!="The Odds API" or odds.get("region")!="uk" or odds.get("market")!="totals"
        or odds.get("errors")!=[] or not fresh(odds.get("updatedAt"),now)
        or archive.get("integrityVersion")!="6.85" or archive.get("mode")!="research_only"
        or not isinstance(archive.get("quarantine"),dict) or not fresh(archive.get("updatedAt"),now)):
        return {}
    base=unique_events(odds.get("events"))
    return {k:e for k,e in unique_events(extra.get("events")).items() if k not in archive["quarantine"] and same_fixture(e,base.get(k,{}))}

def candidate_matches(c,e):
    try:
        h,a=c["match"].split(" – ")
        league=LEAGUES[c["league"]]
        return (league==e["league"] and canonical(h,league)==canonical(e["home"],league)
            and canonical(a,league)==canonical(e["away"],league)
            and c["date"]==parse_time(e["kickoff"]).astimezone(timezone(timedelta(hours=3))).date().isoformat())
    except (KeyError,ValueError,TypeError,AttributeError):return False

def totals_quotes(event,point):
    return [dict(bookmaker=b.get("key"),positive=l.get("over"),negative=l.get("under"),lastUpdate=l.get("lastUpdate"))
        for b in event.get("bookmakers",[]) for l in b.get("lines",[]) if l.get("point")==point]

def extra_quotes(event,market):
    names=("Over","Under") if market=="over15" else ("Yes","No")
    return [dict(bookmaker=b.get("bookmaker"),positive=b.get("prices",{}).get(names[0]),
        negative=b.get("prices",{}).get(names[1]),lastUpdate=b.get("lastUpdate")) for b in event.get(market,[])]

def main():
    now = datetime.now(timezone.utc)
    report = {
        "version": "4.12",
        "sourceBindingVersion":"6.92",
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
        try:archive=load("extra_market_archive.json")
        except (OSError,ValueError):archive={}
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
            and odds.get("market") == "totals"
            and odds.get("errors") == []
            and fresh(odds.get("updatedAt"), now)
        ):
            base_events=unique_events(odds.get("events"))
        extra_events=bound_extra(odds,extra,archive,now)

        moves = {}

        if (
            movement.get("evidenceVersion") == "6.91"
            and movement.get("errors") == []
            and fresh(movement.get("updatedAt"), now)
        ):
            moves = {
                (m["eventId"], m["market"]): m
                for m in movement["markets"]
            }

        for match in matching["matched"]:
            event_id = match["eventId"]
            base=base_events.get(event_id,{})
            cs = [c for c in candidates.get(match["match"], []) if candidate_matches(c,base)]

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
                if not base or parse_time(base["kickoff"])!=kickoff:
                    reject("missing_or_mismatched_base_event");continue
                probability=candidate.get("markets",{}).get(label)
                if type(probability) not in (int,float):
                    reject("missing_model_probability");continue
                result=None
                source=None
                if market in ("over15","over25"):
                    result=compare_market(probability/100,totals_quotes(base,1.5 if market=="over15" else 2.5),now)
                    if result is not None:source="totals"
                if result is None and market in ("over15","btts"):
                    result=compare_market(probability/100,extra_quotes(extra_events.get(event_id,{}),market),now)
                    if result is not None:source="bound_extra"
                if result is None:
                    reject("insufficient_valid_market_data");continue

                move = moves.get((event_id, market), {})

                report["rows"].append({
                    "eventId": event_id,
                    "match": match["match"],
                    "kickoff": match["kickoff"],
                    "market": market,
                    "marketLabel": label,
                    "quoteSource":source,
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
