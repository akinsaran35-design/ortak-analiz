import json
import math
import os
import urllib.request
import urllib.parse
from urllib.error import HTTPError
from datetime import datetime, timezone, timedelta
from pathlib import Path

from league_config import ODDS_CODES
from odds_snapshot_validation import normalize_event,finalize,instant
from extra_market_budget_plan import optional_refresh_gate
LEAGUES = list(ODDS_CODES.values())
key = os.environ.get("ODDS_API_KEY", "").strip()
now = datetime.now(timezone.utc)
# Reuse only a complete, recent snapshot; never change its original timestamp.
cache_path = Path("odds.json")
# Historical backup is deliberately separate from odds.json; never use it as live prices.
archive_path=Path("odds_last_good.json")
status_path=Path("odds_source_status.json")
def read_doc(path):
    try:
        doc=json.loads(path.read_text(encoding="utf-8"))
        return doc if isinstance(doc,dict) else {}
    except (OSError,ValueError,TypeError):return {}
def write_doc(path,doc):
    temp=path.with_suffix(".tmp")
    temp.write_text(json.dumps(doc,ensure_ascii=False,indent=2),encoding="utf-8")
    temp.replace(path)
def complete_snapshot(doc,at):
    try:
        stamp=instant(doc["updatedAt"])
        queried=doc["queriedLeagues"];inactive=doc["inactiveLeagues"]
        events=doc["events"]
        if not (stamp<=at and doc["source"]=="The Odds API" and doc["region"]=="uk" and doc["market"]=="totals"
            and doc["configuredLeagues"]==LEAGUES and doc["errors"]==[] and isinstance(queried,list) and isinstance(inactive,list)
            and len(queried+inactive)==len(LEAGUES) and set(queried+inactive)==set(LEAGUES)
            and isinstance(events,list) and events and doc["eventCount"]==len(events)):return False
        ids=set()
        for e in events:
            if not all(isinstance(e[k],str) and e[k] for k in ("id","league","home","away")) or e["id"] in ids or e["league"] not in queried or e["home"]==e["away"] or instant(e["kickoff"])<=stamp:return False
            ids.add(e["id"])
            if not isinstance(e["bookmakers"],list) or not e["bookmakers"]:return False
            keys=set()
            for b in e["bookmakers"]:
                if not isinstance(b["key"],str) or not b["key"] or b["key"] in keys or not b["lines"]:return False
                keys.add(b["key"])
                points=set()
                for l in b["lines"]:
                    if l["point"] not in (1.5,2.5) or l["point"] in points or not all(type(l[k]) in (int,float) and math.isfinite(l[k]) and l[k]>1 for k in ("over","under")) or not timedelta(0)<=stamp-instant(l["lastUpdate"])<=timedelta(minutes=30):return False
                    points.add(l["point"])
        return True
    except (KeyError,ValueError,TypeError,AttributeError,OverflowError):return False
def preserve(doc,at):
    if not complete_snapshot(doc,at):return
    old=read_doc(archive_path)
    if not complete_snapshot(old,at) or instant(doc["updatedAt"])>instant(old["updatedAt"]):
        write_doc(archive_path,doc)
def publish_status(doc,reason,at,live_balance=None,errors=None):
    backup=read_doc(archive_path)
    valid=complete_snapshot(backup,at)
    current=complete_snapshot(doc,at) and timedelta(0)<=at-instant(doc["updatedAt"])<=timedelta(minutes=30)
    normal=reason in ("refresh_success","recent_cache") and current
    write_doc(status_path,dict(version="6.94",updatedAt=at.isoformat(),mode="normal" if normal else "fallback",
        reason=reason,oddsSnapshotAt=doc.get("updatedAt"),lastGoodSnapshotAt=backup["updatedAt"] if valid else None,
        historicalBackupEvents=backup["eventCount"] if valid else None,backupUsedAsCurrent=False,
        currentOddsAvailable=normal,liveBalance=live_balance,liveBalanceVerified=live_balance is not None,
        errors=errors or [],independentAnalysisMayContinue=True,productionEnabled=False))
cached=None
optional_refresh=os.environ.get("ODDS_OPTIONAL_REFRESH")=="true"
try:
    cached = json.loads(cache_path.read_text(encoding="utf-8"))
    preserve(cached,now)
    stamp = datetime.fromisoformat(cached["updatedAt"].replace("Z", "+00:00"))
    age = (now - stamp).total_seconds()
    if (0 <= age < 1200 and cached.get("source") == "The Odds API"
            and cached.get("region") == "uk" and cached.get("market") == "totals"
            and cached.get("configuredLeagues") == LEAGUES
            and cached.get("errors") == [] and isinstance(cached.get("events"), list)
            and cached["events"] and complete_snapshot(cached,now)):
        publish_status(cached,"recent_cache",now)
        print("Reusing recent odds snapshot; no API requests.")
        raise SystemExit(0)
except (OSError, ValueError, TypeError, KeyError, AttributeError):
    pass
report = {"version": "3.7", "updatedAt": now.isoformat(), "startedAt": now.isoformat(), "source": "The Odds API",
          "region": "uk", "market": "totals", "events": [], "errors": [],
          "remainingCredits": None, "decision": "PAS",
          "configuredLeagues": LEAGUES, "queriedLeagues": [], "inactiveLeagues": []}
def request(path, params):
    url = "https://api.the-odds-api.com/v4/" + path + "?" + urllib.parse.urlencode({"apiKey": key, **params})
    with urllib.request.urlopen(url, timeout=20) as response:
        remaining = response.headers.get("x-requests-remaining")
        report["remainingCredits"] = int(remaining) if remaining and remaining.isdigit() else None
        return json.load(response)
if not key:
    report["errors"].append("missing_key")
else:
    try:
        active = {s["key"] for s in request("sports/", {}) if s.get("active")}
    except HTTPError as exc:
        active = set()
        report["errors"].append(f"HTTP {exc.code}")
    except Exception:
        active = set()
        report["errors"].append("connection_error")
    if optional_refresh:
        try:
            workflow=Path(".github/workflows/daily.yml").read_text()
            gate=optional_refresh_gate(report["remainingCredits"] if not report["errors"] else None,datetime.now(timezone.utc),workflow,len(LEAGUES))
        except (OSError,ValueError,TypeError):
            gate=dict(allowed=False,reason="budget_policy_unavailable")
        print("OPTIONAL_ODDS_REFRESH_688",json.dumps(gate))
        if not gate["allowed"]:
            # Retain the actual older observation, never mark it as fresh.
            if (isinstance(cached,dict) and cached.get("source")=="The Odds API" and cached.get("region")=="uk"
                and cached.get("market")=="totals" and isinstance(cached.get("events"),list)
                and cached.get("eventCount")==len(cached["events"])):
                try:
                    stamp=datetime.fromisoformat(cached["updatedAt"].replace("Z","+00:00"))
                    if stamp.tzinfo is not None and stamp<=now:
                        publish_status(cached,"optional_refresh_deferred",datetime.now(timezone.utc),report["remainingCredits"],report["errors"])
                        print("Optional refresh deferred; existing observation timestamp retained.")
                        raise SystemExit(0)
                except (ValueError,TypeError,KeyError,AttributeError):
                    pass
            report["errors"].append("optional_refresh_deferred")
            active=set()
    for league in LEAGUES:
        if league not in active:
            report["inactiveLeagues"].append(league)
            continue
        if report["remainingCredits"] is None or report["remainingCredits"] <= 20:
            report["errors"].append("quota_guard")
            break
        try:
            events = request(f"sports/{league}/odds/", {"regions": "uk", "markets": "totals", "oddsFormat": "decimal"})
            report["queriedLeagues"].append(league)
            received=datetime.now(timezone.utc)
            if not isinstance(events,list):
                raise ValueError("invalid events schema")
            for event in events:
                normalized=normalize_event(event,league,received)
                if normalized is not None:
                    report["events"].append(normalized)
        except HTTPError as exc:
            report["errors"].append(f"{league}: HTTP {exc.code}")
            if exc.code in (401, 403, 429):
                break
        except Exception:
            report["errors"].append(f"{league}: response_error")
finalize(report,datetime.now(timezone.utc))
write_doc(cache_path,report)
finished=instant(report["updatedAt"])
preserve(report,finished)
reason="refresh_success" if complete_snapshot(report,finished) else "quota_guard" if "quota_guard" in report["errors"] else "source_error" if report["errors"] else "incomplete_snapshot"
publish_status(report,reason,finished,report["remainingCredits"],report["errors"])
print("Odds events:", report["eventCount"], "Remaining credits:", report["remainingCredits"], "Errors:", report["errors"])
