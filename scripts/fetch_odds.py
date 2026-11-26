import json
import os
import urllib.request
import urllib.parse
from urllib.error import HTTPError
from datetime import datetime, timezone
from pathlib import Path

from league_config import ODDS_CODES
LEAGUES = list(ODDS_CODES.values())
key = os.environ.get("ODDS_API_KEY", "").strip()
now = datetime.now(timezone.utc)
# Reuse only a complete, recent snapshot; never change its original timestamp.
cache_path = Path("odds.json")
try:
    cached = json.loads(cache_path.read_text(encoding="utf-8"))
    stamp = datetime.fromisoformat(cached["updatedAt"].replace("Z", "+00:00"))
    age = (now - stamp).total_seconds()
    if (0 <= age < 1200 and cached.get("source") == "The Odds API"
            and cached.get("region") == "uk" and cached.get("market") == "totals"
            and cached.get("configuredLeagues") == LEAGUES
            and cached.get("errors") == [] and isinstance(cached.get("events"), list)
            and cached["events"]):
        print("Reusing recent odds snapshot; no API requests.")
        raise SystemExit(0)
except (OSError, ValueError, TypeError, KeyError, AttributeError):
    pass
report = {"version": "3.7", "updatedAt": now.isoformat(), "source": "The Odds API",
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
            for event in events:
                kickoff = datetime.fromisoformat(event["commence_time"].replace("Z", "+00:00"))
                if kickoff <= now:
                    continue
                books = []
                for book in event.get("bookmakers", []):
                    lines = []
                    for market in book.get("markets", []):
                        if market.get("key") != "totals":
                            continue
                        for point in (1.5, 2.5):
                            prices = {o["name"]: o["price"] for o in market.get("outcomes", []) if o.get("point") == point and o.get("name") in ("Over", "Under") and isinstance(o.get("price"), (int, float)) and o["price"] > 1}
                            if len(prices) == 2:
                                total = 1/prices["Over"] + 1/prices["Under"]
                                lines.append({"point": point, "over": prices["Over"], "under": prices["Under"], "marketOverProbability": round((1/prices["Over"])/total, 6), "lastUpdate": market.get("last_update") or book.get("last_update")})
                    if lines:
                        books.append({"key": book["key"], "name": book["title"], "lines": lines})
                if books:
                    report["events"].append({"id": event["id"], "league": league, "home": event["home_team"], "away": event["away_team"], "kickoff": kickoff.isoformat(), "bookmakers": books})
        except HTTPError as exc:
            report["errors"].append(f"{league}: HTTP {exc.code}")
            if exc.code in (401, 403, 429):
                break
        except Exception:
            report["errors"].append(f"{league}: response_error")
report["eventCount"] = len(report["events"])
Path("odds.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print("Odds events:", report["eventCount"], "Remaining credits:", report["remainingCredits"], "Errors:", report["errors"])
