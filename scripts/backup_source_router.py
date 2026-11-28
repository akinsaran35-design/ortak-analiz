"""Route a verified primary outage to a bounded backup access check.
No raw odds are published or mixed into the primary snapshot.
"""
import json
import os
from pathlib import Path
from datetime import datetime,timezone,timedelta
from api_football_access_probe import probe
from odds_snapshot_validation import instant

def route(primary,continuity,now,key,check=probe):
    result={"version":"7.05","mode":"research_only","decision":"PAS",
            "primary":"The Odds API","backup":"API-Football",
            "backupAttempted":False,"reason":"unverified_primary_state"}
    try:
        if primary["source"]!="The Odds API" or continuity["version"]!="6.94":
            return result
        if continuity["currentOddsAt"]!=primary["updatedAt"]:
            return result
        if not timedelta(0)<=now-instant(continuity["updatedAt"])<=timedelta(minutes=10):
            return result
        if continuity["mode"]=="normal" and continuity["currentOddsUsable"] is True:
            result["reason"]="primary_healthy"
            return result
        if continuity["mode"]!="fallback" or continuity["currentOddsUsable"] is not False:
            return result
        if continuity["reason"] not in ("quota_guard","source_error","no_valid_events","optional_refresh_deferred"):
            return result
        if not key:
            result["reason"]="backup_secret_missing"
            return result
        result.update(backupAttempted=True,reason=continuity["reason"],access=check(key))
    except (ValueError,TypeError,KeyError,AttributeError):
        pass
    return result

def load(path):
    try:return json.loads(Path(path).read_text())
    except (OSError,ValueError):return {}

if __name__=="__main__":
    result=route(load("odds.json"),load("odds_continuity.json"),
        datetime.now(timezone.utc),os.environ.get("API_FOOTBALL_KEY","").strip())
    print(json.dumps(result,ensure_ascii=False))
