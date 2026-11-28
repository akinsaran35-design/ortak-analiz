
import json
import math
from collections import Counter
from league_config import ODDS_CODES
from extra_market_budget_plan import extra_event_gate
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
    "startedAt": now.isoformat(),
    "integrityVersion": "6.84",
    "quotaPolicyVersion": "6.89",
    "oddsSnapshotAt": None,
    "quotaStatus": "not_checked",
    "paidRequestsAttempted": 0,
    "source": "The Odds API",
    "region": "uk",
    "mode": "research_only",
    "decision": "PAS",
    "remainingCredits": None,
    "events": [],
    "errors": []
}

def parse_time(value):
    stamp=datetime.fromisoformat(value.replace("Z","+00:00"))
    if stamp.tzinfo is None:raise ValueError("timezone required")
    return stamp

def valid_identity(event):
    try:
        return (isinstance(event,dict) and all(isinstance(event[k],str) and event[k].strip() and "|" not in event[k] for k in ("id","league","home","away"))
            and event["league"] in ODDS_CODES.values() and event["home"]!=event["away"]
            and parse_time(event["kickoff"])>datetime.now(timezone.utc))
    except (KeyError,TypeError,ValueError,AttributeError,OverflowError):return False

def response_matches(data,event,received):
    try:
        return (isinstance(data,dict) and data["id"]==event["id"] and data["sport_key"]==event["league"]
            and data["home_team"]==event["home"] and data["away_team"]==event["away"]
            and parse_time(data["commence_time"])==parse_time(event["kickoff"])>received)
    except (KeyError,TypeError,ValueError,AttributeError,OverflowError):return False

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

def extract_market(event,market_key,names,received=None):
    received=received or datetime.now(timezone.utc)
    if not isinstance(event,dict) or not isinstance(event.get("bookmakers"),list):return []
    books=[b for b in event["bookmakers"] if isinstance(b,dict)]
    counts=Counter(b.get("key") for b in books if isinstance(b.get("key"),str))
    rows=[]
    for book in books:
        k=book.get("key")
        if not isinstance(k,str) or not k or "|" in k or counts[k]!=1:continue
        if not isinstance(book.get("markets"),list):continue
        markets=[m for m in book["markets"] if isinstance(m,dict) and m.get("key")==market_key]
        if len(markets)!=1:continue
        market=markets[0]
        stamp=market.get("last_update") or book.get("last_update")
        try:
            if not 0<=(received-parse_time(stamp)).total_seconds()<=MAX_AGE:continue
        except (ValueError,TypeError,AttributeError,OverflowError):continue
        if not isinstance(market.get("outcomes"),list):continue
        outcomes=[o for o in market["outcomes"] if isinstance(o,dict) and o.get("name") in names
            and (market_key!="alternate_totals" or o.get("point")==1.5)]
        if len(outcomes)!=2 or {o["name"] for o in outcomes}!=set(names):continue
        prices={o["name"]:o.get("price") for o in outcomes}
        if not all(type(p) in (int,float) and math.isfinite(p) and p>1 for p in prices.values()):continue
        rows.append(dict(bookmaker=k,prices=prices,lastUpdate=stamp,
            marketProbability=round((1/prices[names[0]])/sum(1/prices[n] for n in names),6)))
    return rows

def run():
    if not key:
        report["errors"].append("missing_key")
        return

    snapshot = json.loads(
        Path("odds.json").read_text(encoding="utf-8")
    )

    report["oddsSnapshotAt"]=snapshot.get("updatedAt")
    age = (
        now - parse_time(snapshot["updatedAt"])
    ).total_seconds()

    if not 0 <= age <= MAX_AGE:
        report["errors"].append("stale_snapshot")
        return

    if (
        snapshot.get("source") != "The Odds API"
        or snapshot.get("region") != "uk"
        or snapshot.get("market") != "totals"
        or snapshot.get("configuredLeagues") != list(ODDS_CODES.values())
        or snapshot.get("errors") != []
    ):
        report["errors"].append("invalid_snapshot")
        return

    try:
        workflow=Path(".github/workflows/daily.yml").read_text()
    except OSError:
        report["errors"].append("budget_policy_unavailable");return
    raw=snapshot.get("events",[])
    if not isinstance(raw,list):
        report["errors"].append("invalid_events");return
    ids=Counter(e.get("id") for e in raw if isinstance(e,dict) and isinstance(e.get("id"),str))
    candidates=sorted((e for e in raw if valid_identity(e) and ids[e["id"]]==1),key=lambda e:parse_time(e["kickoff"]))

    if not candidates:
        report["quotaStatus"]="no_eligible_events";return
    # The metadata response supplies the current balance. Archive balance never authorizes spending.
    request("sports/", {})
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

        gate=extra_event_gate(credits,datetime.now(timezone.utc),workflow,len(ODDS_CODES))
        report["quotaGate"]=gate
        if not gate["allowed"]:
            report["quotaStatus"]="quota_guard"
            break
        report["quotaStatus"]="reserve_preserved"

        checked.add(event_id)

        try:
            report["paidRequestsAttempted"]+=1
            data = request(
                f"sports/{league}/events/{event_id}/odds",
                {
                    "regions": "uk",
                    "markets": "alternate_totals,btts",
                    "oddsFormat": "decimal"
                }
            )

            received=datetime.now(timezone.utc)
            if not response_matches(data,event,received):
                report["errors"].append("event_identity_mismatch");break
            over15 = extract_market(data,"alternate_totals",("Over","Under"),received)

            btts = extract_market(data,"btts",("Yes","No"),received)

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

finished=datetime.now(timezone.utc)
report["updatedAt"]=finished.isoformat()
report["events"]=[e for e in report["events"] if parse_time(e["kickoff"])>finished]
for e in report["events"]:
    for m in ("over15","btts"):
        e[m]=[b for b in e[m] if 0<=(finished-parse_time(b["lastUpdate"])).total_seconds()<=MAX_AGE]
        e[m+"Bookmakers"]=len(e[m])
        e[m+"DataReady"]=len(e[m])>=3
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
