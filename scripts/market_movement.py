import json,math
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict,Counter
from statistics import median

SOURCE = Path("extra_market_archive.json")
OUTPUT = Path("market_movement.json")

MIN_BOOKMAKERS = 3
MIN_CHANGE_PP = 1.0


def parse_time(value):
    t=datetime.fromisoformat(value.replace("Z","+00:00"))
    if t.tzinfo is None:raise ValueError("timezone required")
    return t

NAMES={"over15":("Over","Under"),"btts":("Yes","No")}

def checked_history(record,now):
    """Recompute no-vig probabilities from timestamped raw prices."""
    try:
        history=record["history"]
        if not isinstance(history,list) or len(history)<2:return None
        kickoff=parse_time(record["kickoff"])
        names=NAMES[record["market"]]
        seen=set()
        values=[]
        for h in history:
            updated=parse_time(h["lastUpdate"])
            captured=parse_time(h["capturedAt"])
            if updated in seen or not updated<=captured<kickoff or captured>now or (captured-updated).total_seconds()>1800:return None
            seen.add(updated)
            prices=h["prices"]
            if not isinstance(prices,dict) or set(prices)!=set(names) or not all(type(v) in (int,float) and math.isfinite(v) and v>1 for v in prices.values()):return None
            p=round((1/prices[names[0]])/sum(1/prices[k] for k in names),6)
            if type(h.get("marketProbability")) not in (int,float) or not math.isfinite(h["marketProbability"]) or abs(h["marketProbability"]-p)>0.000001:return None
            values.append((updated,p))
        values.sort()
        if not 0<=(now-values[-1][0]).total_seconds()<=1800:return None
        return (values[-1][1]-values[0][1])*100
    except (KeyError,ValueError,TypeError,AttributeError,OverflowError):return None


def run():
    now = datetime.now(timezone.utc)

    report = {
        "version": "4.11",
        "evidenceVersion":"6.91",
        "firstObservedIsOpening":False,
        "excluded":{},
        "updatedAt": now.isoformat(),
        "mode": "research_only",
        "decision": "PAS",
        "eventCount": 0,
        "markets": [],
        "errors": []
    }

    groups = defaultdict(list)
    excluded=Counter()

    if not SOURCE.exists():
        report["errors"].append("missing_archive")
    else:
        archive = json.loads(
            SOURCE.read_text(encoding="utf-8")
        )

        quarantine=archive.get("quarantine",{})
        if not isinstance(quarantine,dict):raise ValueError("invalid quarantine")
        identities=defaultdict(set)
        eligible=[]
        for key,record in archive["records"].items():
            try:
                if record["eventId"] in quarantine:
                    excluded["quarantined_record"]+=1;continue
                if not all(isinstance(record[k],str) and record[k].strip() and "|" not in record[k] for k in ("eventId","league","home","away","market","bookmaker")) or record["home"]==record["away"] or record["market"] not in NAMES:
                    raise ValueError("identity")
                if key!="|".join(record[k] for k in ("eventId","market","bookmaker")):
                    raise ValueError("key")
                kickoff=parse_time(record["kickoff"])
                identities[record["eventId"]].add((record["league"],record["home"],record["away"],kickoff))
                if kickoff<=now:continue
                eligible.append(record)
            except (KeyError,ValueError,TypeError,AttributeError,OverflowError):
                excluded["invalid_record_identity"]+=1
        for record in eligible:
            if len(identities[record["eventId"]])!=1:
                excluded["conflicting_event_identity"]+=1;continue
            groups[(record["eventId"],record["market"])].append(record)

    for (event_id, market), records in groups.items():
        ready={}
        counts=Counter(r["bookmaker"] for r in records)
        for record in records:
            if counts[record["bookmaker"]]!=1:
                excluded["duplicate_bookmaker"]+=1;continue
            change=checked_history(record,now)
            if change is None:
                excluded["unusable_history"]+=1;continue
            ready[record["bookmaker"]]=change

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
    report["excluded"]=dict(excluded)

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
