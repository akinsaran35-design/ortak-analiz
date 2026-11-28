import json
import os
import urllib.request
import urllib.parse
from urllib.error import HTTPError
from datetime import datetime, timezone
from pathlib import Path

from league_config import ODDS_CODES
from odds_snapshot_validation import normalize_event,finalize
from extra_market_budget_plan import optional_refresh_gate
from odds_continuity import record
LEAGUES = list(ODDS_CODES.values())
key = os.environ.get("ODDS_API_KEY", "").strip()
now = datetime.now(timezone.utc)
# Reuse only a complete, recent snapshot; never change its original timestamp.
cache_path = Path("odds.json")
cached=None
optional_refresh=os.environ.get("ODDS_OPTIONAL_REFRESH")=="true"
try:
    cached = json.loads(cache_path.read_text(encoding="utf-8"))
    stamp = datetime.fromisoformat(cached["updatedAt"].replace("Z", "+00:00"))
    age = (now - stamp).total_seconds()
    if (0 <= age < 1200 and cached.get("source") == "The Odds API"
            and cached.get("region") == "uk" and cached.get("market") == "totals"
            and cached.get("configuredLeagues") == LEAGUES
            and cached.get("errors") == [] and isinstance(cached.get("events"), list)
            and cached["events"]):
        record(cached,cached,datetime.now(timezone.utc),"recent_cache")
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
                        record(cached,cached,datetime.now(timezone.utc),"optional_refresh_deferred",report["remainingCredits"],report["errors"])
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
Path("odds.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
reason="quota_guard" if "quota_guard" in report["errors"] else "source_error" if report["errors"] else "collected" if report["events"] else "no_valid_events"
record(report,cached,datetime.now(timezone.utc),reason,report["remainingCredits"],report["errors"])
print("Odds events:", report["eventCount"], "Remaining credits:", report["remainingCredits"], "Errors:", report["errors"])
