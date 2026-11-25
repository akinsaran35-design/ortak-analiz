from datetime import date
from historical_data import collect

def fetch(url):
    if "api.github.com" in url:
        return [{"type":"file","name":"en.1.json"}]
    return {"matches":[{"date":"2026-11-01","team1":"A","team2":"B","score":{"ft":[1,0]}},{"date":"2026-11-01","team1":"A","team2":"B","score":{"ft":[2,0]}}]}
r=collect(date(2026,11,26),fetch)
assert r["matchCount"]==0
assert r["conflictAudit"]
assert r["conflictAudit"][0]["records"][0]["ft"]==[1,0]
