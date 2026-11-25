import json
import urllib.request
from datetime import datetime, timezone, timedelta
from shadow_performance import load, save, stamp

LEAGUES = {"soccer_epl":"en.1","soccer_efl_champ":"en.2","soccer_germany_bundesliga":"de.1","soccer_spain_la_liga":"es.1","soccer_italy_serie_a":"it.1","soccer_france_ligue_one":"fr.1"}
def norm(s):
    return " ".join(s.casefold().split())

def fetch(season, league):
    url = f"https://raw.githubusercontent.com/openfootball/football.json/master/{season}/{league}.json"
    with urllib.request.urlopen(url,timeout=20) as response:
        return json.load(response)["matches"]

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
                matches = [m for m in cache[key] if str(m.get("date",""))[:10]==day.isoformat()
                           and isinstance(m.get("team1"),str) and isinstance(m.get("team2"),str)
                           and [norm(m["team1"]),norm(m["team2"])]==[norm(n) for n in names]]
                if len(matches)!=1:
                    continue
                ft = (matches[0].get("score") or {}).get("ft")
                if isinstance(ft,list) and len(ft)==2 and all(type(x) is int and x>=0 for x in ft):
                    results[eid] = {"status":"final","score":ft,"source":"OpenFootball","verifiedAt":now.isoformat()}
            except (OSError,ValueError,KeyError,TypeError) as exc:
                errors.append({"eventId":eid,"error":type(exc).__name__})
    return errors

if __name__ == "__main__":
    now = datetime.now(timezone.utc)
    results = load("shadow_verified_results.json",{})
    errors = resolve(load("shadow_archive.json",{}),results,now)
    save("shadow_verified_results.json",results)
    save("shadow_results_status.json",{"updatedAt":now.isoformat(),"errors":errors,"verified":len(results)})
