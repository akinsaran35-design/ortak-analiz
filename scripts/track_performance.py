import json
import urllib.request
from datetime import datetime, timedelta, timezone, date
from pathlib import Path

root = Path(__file__).resolve().parent.parent
now = datetime.now(timezone(timedelta(hours=3)))
today = now.date()
daily = json.loads((root/"daily.json").read_text(encoding="utf-8"))
archive = root/"prediction_archive.json"
records = json.loads(archive.read_text(encoding="utf-8")) if archive.exists() else {}
leagues = {"İngiltere Premier Lig":"en.1","İngiltere Championship":"en.2","Almanya Bundesliga":"de.1","İspanya La Liga":"es.1","İtalya Serie A":"it.1","Fransa Ligue 1":"fr.1"}
markets = ["1.5 Üst","2.5 Üst","KG Var"]
def key(d,l,m):
    return json.dumps([d,l,m],ensure_ascii=False)
# Only future calendar dates; kickoff times are not verified.
for c in daily.get("candidates",[]):
    if c["date"] <= today.isoformat() or c["league"] not in leagues:
        continue
    k = key(c["date"],c["league"],c["match"])
    if k not in records and all(type(c["markets"].get(m)) in (int,float) and 0<=c["markets"][m]<=100 for m in markets):
        records[k] = {"date":c["date"],"league":c["league"],"match":c["match"],
                      "recordedAt":now.isoformat(),"modelVersion":daily.get("version"),
                      "markets":c["markets"],"result":None}
def team(x):
    return str(x.get("name") or x.get("code") or "").strip() if isinstance(x,dict) else str(x or "").strip()
errors = []
needed = set()
for r in records.values():
    if r["result"] is None and r["date"] < today.isoformat():
        d = date.fromisoformat(r["date"])
        y = d.year if d.month>=7 else d.year-1
        needed.add((r["league"],f"{y}-{str(y+1)[-2:]}"))
for league,season in sorted(needed):
    try:
        url = f"https://raw.githubusercontent.com/openfootball/football.json/master/{season}/{leagues[league]}.json"
        with urllib.request.urlopen(url,timeout=20) as response:
            matches = json.load(response).get("matches",[])
        for m in matches:
            d = str(m.get("date",""))[:10]
            if d>=today.isoformat():
                continue
            k = key(d,league,f"{team(m.get('team1'))} – {team(m.get('team2'))}")
            ft = (m.get("score") or {}).get("ft")
            if k in records and records[k]["result"] is None and isinstance(ft,list) and len(ft)==2 and all(type(x) is int and x>=0 for x in ft):
                records[k]["result"] = ft
                records[k]["settledAt"] = now.isoformat()
    except Exception as exc:
        errors.append(f"{league}/{season}: {exc}")
def metrics(rows):
    settled = [r for r in rows if r["result"] is not None]
    out = {"recorded":len(rows),"settled":len(settled),"pending":len(rows)-len(settled),"markets":{}}
    for i,m in enumerate(markets):
        pairs = []
        for r in settled:
            h,a = r["result"]
            y = [h+a>=2,h+a>=3,h>0 and a>0][i]
            pairs.append((r["markets"][m]/100,int(y)))
        n=len(pairs)
        out["markets"][m]={"tested":n,"brier":round(sum((p-y)**2 for p,y in pairs)/n,6) if n else None,"actualRate":round(100*sum(y for p,y in pairs)/n,2) if n else None}
    return out
rows=list(records.values())
report={"version":"2.4","updatedAt":now.isoformat(),"method":"First recorded future-date candidates only; kickoff unverified; no odds or profit measurement.","errors":errors,"overall":metrics(rows),"leagues":{l:metrics([r for r in rows if r["league"]==l]) for l in leagues},"periods":{str(n):metrics([r for r in rows if r["date"] >= (today-timedelta(days=n)).isoformat() and r["date"]<today.isoformat()]) for n in (30,90)}}
archive.write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding="utf-8")
(root/"performance.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps(report,ensure_ascii=False))
