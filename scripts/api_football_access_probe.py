"""Private diagnostic: check API-Football access, never publish raw data or credentials."""
import json
import os
import urllib.request
from datetime import datetime, timezone
from urllib.error import HTTPError
from api_football_sample_quality import inspect_sample

BASE = "https://v3.football.api-sports.io/"
def request(key, path):
    req = urllib.request.Request(BASE + path, headers={"x-apisports-key": key})
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.loads(response.read(2_000_000))

def probe(key, reader=request):
    out = {"provider": "API-Football", "status": "unverified",
           "oddsAccess": "not_checked", "oddsRequestsAttempted": 0}
    if not key:
        out["status"] = "missing_secret"
        return out
    try:
        doc = reader(key, "status")
        if doc.get("errors") not in ([], {}):
            out["status"] = "status_api_error"
            return out
        data = doc["response"]
        subscription, quota = data["subscription"], data["requests"]
        used, limit = quota["current"], quota["limit_day"]
        if type(used) is not int or type(limit) is not int or not 0 <= used <= limit:
            raise ValueError("quota")
        out.update(status="verified", active=subscription.get("active") is True,
                   freePlan=subscription.get("plan") == "Free", used=used, limit=limit,
                   remaining=limit-used)
        if not out["active"] or not out["freePlan"] or limit-used < 20:
            out["oddsAccess"] = "quota_or_plan_guard"
            return out
        day = datetime.now(timezone.utc).date().isoformat()
        out["oddsRequestsAttempted"] = 1
        doc = reader(key, "odds?date=" + day)
        if doc.get("errors") not in ([], {}):
            out["oddsAccess"] = "api_error"
            return out
        rows = doc["response"]
        if not isinstance(rows, list):
            raise ValueError("response")
        out["oddsAccess"] = "sample_available" if rows else "empty_sample"
        out.update(inspect_sample(doc, datetime.now(timezone.utc)))
    except HTTPError as exc:
        out["errorType"] = "HTTP_" + str(exc.code)
    except Exception as exc:
        out["errorType"] = type(exc).__name__
    return out

if __name__ == "__main__":
    # No raw provider body, account details, API key, odds or URLs are printed.
    result = probe(os.environ.get("API_FOOTBALL_KEY", "").strip())
    print(json.dumps(result, ensure_ascii=False))
    if result["status"] != "verified" or "errorType" in result:
        raise SystemExit(1)
