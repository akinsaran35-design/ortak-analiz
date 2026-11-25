from datetime import date
from historical_data import normalize, collect
today=date(2026,11,25)
m={"date":"2026-11-24","team1":"A","team2":"B","score":{"ft":[0,0],"ht":[0,0]}}
rows=list(normalize({"matches":[m,dict(m,date="2026-11-25"),dict(m,date="2025-01-01")]},"en.1","test",today))
assert len(rows)==1 and rows[0]["ft"]==[0,0] and rows[0]["ht"]==[0,0]
assert list(normalize([dict(m,score={"ft":[0,0],"ht":[1,0]})],"en.1","test",today))[0]["ht"] is None
def fake(url):
    if "contents" in url:
        return [{"name":"en.1.json","type":"file"}]
    return {"matches":[m]}
r=collect(today,fake)
assert r["matchCount"]==1 and r["leagueCount"]==1 and r["halfTimeCount"]==1
assert not r["realBettingEnabled"]
print("Historical archive tests passed")
