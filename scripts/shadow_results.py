import json
import urllib.request
from datetime import datetime, timezone, timedelta
from shadow_performance import load, save, stamp

from fixture_schema import matches_in
from league_config import RESULT_CODES as LEAGUES
def norm(s):
    if isinstance(s, dict):
        s = s.get("name") or s.get("code") or ""
    return " ".join(s.casefold().split()) if isinstance(s, str) else ""

def fetch(season, league):
    if league == "tr.1":
        from turkey_source import fetch as turkey_fetch
        return turkey_fetch(season,include_fixtures=False)
    url = f"https://raw.githubusercontent.com/openfootball/football.json/master/{season}/{league}.json"
    with urllib.request.urlopen(url,timeout=20) as response:
        return matches_in(json.load(response))

def resolve(records, results, now, fetcher=fetch):
    errors = []
    cache = {}
    for record in records.values():
        if record.get("status") != "pending":
            continue
        for p in record["selections"]:
            eid = p["eventId"]
            if eid in results:
                continue
            try:
                day = stamp(p["kickoff"]).astimezone(timezone(timedelta(hours=3))).date()
                if day >= now.astimezone(timezone(timedelta(hours=3))).date():
                    continue
                league = p.get("league")
                if league not in LEAGUES:
                    errors.append({"eventId":eid,"error":"missing_supported_league"})
                    continue
                names = p["match"].split(" – ")
                if len(names)!=2:
                    continue
                year = day.year if day.month>=7 else day.year-1
                key = (f"{year}-{str(year+1)[-2:]}",LEAGUES[league])
                if key not in cache:
                    cache[key] = fetcher(*key)
                name_key = norm
                if league == "soccer_turkey_super_league":
                    from turkey_source import team_key
                    name_key = team_key
                matches = [m for m in cache[key] if str(m.get("date",""))[:10]==day.isoformat()
                           and norm(m.get("team1")) and norm(m.get("team2"))
                           and [name_key(m["team1"]),name_key(m["team2"])]==[name_key(n) for n in names]]
                if len(matches)!=1:
                    errors.append({"eventId":eid,"error":"ambiguous_fixture" if matches else "fixture_not_found"})
                    continue
                ft = (matches[0].get("score") or {}).get("ft")
                if isinstance(ft,list) and len(ft)==2 and all(type(x) is int and x>=0 for x in ft):
                    results[eid] = {"status":"final","score":ft,"source":"Football-Data.co.uk" if league=="soccer_turkey_super_league" else "OpenFootball","verifiedAt":now.isoformat()}
                else:
                    errors.append({"eventId":eid,"error":"final_score_unavailable"})
            except (OSError,ValueError,KeyError,TypeError,AttributeError) as exc:
                errors.append({"eventId":eid,"error":type(exc).__name__})
    return errors

if __name__ == "__main__":
    now = datetime.now(timezone.utc)
    results = load("shadow_verified_results.json",{})
    errors = resolve(load("shadow_archive.json",{}),results,now)
    save("shadow_verified_results.json",results)
    save("shadow_results_status.json",{"updatedAt":now.isoformat(),"errors":errors,"verified":len(results)})
