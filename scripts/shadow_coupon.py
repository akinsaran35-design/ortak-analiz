"""Research-only coupon selector; never enables live betting."""
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path

def stamp(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))

def select(analysis, odds, now):
    result = {"version":"4.8","mode":"shadow","liveEnabled":False,
              "updatedAt":now.isoformat(),"decision":"PAS","selections":[]}
    diagnostics = {"rows":len(analysis.get("rows", [])), "rejected":{}, "eligible":0}
    result["diagnostics"] = diagnostics
    def reject(reason):
        counts = diagnostics["rejected"]
        counts[reason] = counts.get(reason, 0) + 1
    if analysis.get("snapshotFresh") is not True or odds.get("errors") != [] or analysis.get("market") != "2.5":
        reject("snapshot_or_market_invalid")
        return result
    try:
        if any(not timedelta(0) <= now-stamp(d["updatedAt"]) <= timedelta(minutes=30)
               for d in (analysis, odds)):
            reject("stale_snapshot")
            return result
    except (KeyError, ValueError, TypeError):
        reject("invalid_timestamp")
        return result
    events = {e["id"]:e for e in odds.get("events", [])}
    candidates = []
    for row in analysis.get("rows", []):
        try:
            event = events[row["eventId"]]
            kickoff = stamp(event["kickoff"])
            if kickoff <= now or kickoff.astimezone(timezone(timedelta(hours=3))).date() != now.astimezone(timezone(timedelta(hours=3))).date():
                reject("started_or_other_day")
                continue
            p = float(row["modelProbabilityUncalibrated"])
            if not .75 <= p <= 1:
                reject("probability_below_threshold_or_invalid")
                continue
            books = {}
            for book in event["bookmakers"]:
                for line in book["lines"]:
                    if line["point"] == 2.5 and 1 < line["over"] and timedelta(0) <= now-stamp(line["lastUpdate"]) <= timedelta(minutes=30):
                        books[book["key"]] = (line["over"],book["name"])
            if len(books) < 3:
                reject("insufficient_fresh_bookmakers")
                continue
            price, name = max(books.values())
            ev = p*price-1
            if ev >= .05:
                candidates.append({"eventId":event["id"],"league":event["league"],"match":row["match"],"kickoff":event["kickoff"],"market":"2.5 Over","rawProbability":p,"odds":price,"bookmaker":name,"estimatedEV":ev,"calibrated":False,"teams":[event["home"],event["away"]]})
            else:
                reject("estimated_ev_below_threshold")
        except (KeyError, ValueError, TypeError):
            reject("invalid_or_unmatched_event")
            continue
    diagnostics["eligible"] = len(candidates)
    used = set()
    for item in sorted(candidates,key=lambda x:(x["rawProbability"],x["estimatedEV"]),reverse=True):
        teams = {t.casefold() for t in item["teams"]}
        if teams & used:
            reject("shared_team")
            continue
        used.update(teams)
        result["selections"].append(item)
        if len(result["selections"]) == 3:
            break
    if result["selections"]:
        result["decision"] = "SHADOW_ONLY"
    return result

if __name__ == "__main__":
    now = datetime.now(timezone.utc)
    result = select(json.loads(Path("market_analysis.json").read_text()),json.loads(Path("odds.json").read_text()),now)
    Path("shadow_coupon.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
