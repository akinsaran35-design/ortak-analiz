"""V4.22 historical archive research; no betting selections."""
import json
import re
from datetime import date, timedelta
from pathlib import Path
from urllib.request import Request, urlopen

API = "https://api.github.com/repos/openfootball/football.json/contents"
RAW = "https://raw.githubusercontent.com/openfootball/football.json/master"

def get(url):
    with urlopen(Request(url, headers={"User-Agent":"OrtakAnaliz/4.22"}), timeout=20) as response:
        return json.load(response)

def score(value):
    if isinstance(value, dict):
        value = [value.get("home"), value.get("away")]
    if isinstance(value, list) and len(value)==2 and all(type(x) is int and x>=0 for x in value):
        return value
    return None

def team(value):
    if isinstance(value, dict):
        value = value.get("name")
    return value.strip() if isinstance(value,str) else ""

def normalize(data, league, source, today):
    rows = data if isinstance(data,list) else data.get("matches",[])
    if isinstance(data,dict) and not rows:
        rows = [m for r in data.get("rounds",[]) for m in r.get("matches",[])]
    for m in rows:
        if not isinstance(m,dict):
            continue
        try:
            d = date.fromisoformat(str(m.get("date") or m.get("datetime"))[:10])
        except ValueError:
            continue
        if not today-timedelta(days=365)<=d<today:
            continue
        h=team(m.get("team1") or m.get("home") or m.get("homeTeam"))
        a=team(m.get("team2") or m.get("away") or m.get("awayTeam"))
        s=m.get("score")
        if not isinstance(s,dict):
            continue
        ft=score(s.get("ft") or s.get("fulltime") or s.get("fullTime"))
        ht=score(s.get("ht") or s.get("halftime") or s.get("halfTime"))
        if not h or not a or h==a or ft is None:
            continue
        if ht is not None and any(x>y for x,y in zip(ht,ft)):
            ht=None
        yield dict(date=d.isoformat(),league=league,home=h,away=a,ft=ft,ht=ht,source=source)

def collect(today, fetch=get):
    report=dict(version="4.22",status="research_only",realBettingEnabled=False,asOf=today.isoformat(),matches=[],errors=[],filesLoaded=0)
    records={}
    conflicts=set()
    y=today.year
    seasons=sorted({str(n) for n in (y-1,y)} | {f"{n}-{str(n+1)[-2:]}" for n in (y-2,y-1,y)})
    for season in seasons:
        try:
            entries=fetch(f"{API}/{season}")
        except Exception as exc:
            report["errors"].append(dict(source=season,error=type(exc).__name__))
            continue
        for entry in entries:
            name=entry.get("name","")
            if entry.get("type")!="file" or not re.fullmatch(r"[a-z][a-z0-9._-]*\.json",name):
                continue
            url=f"{RAW}/{season}/{name}"
            try:
                rows=list(normalize(fetch(url),name[:-5],url,today))
                report["filesLoaded"]+=1
                for row in rows:
                    k=tuple(row[x] for x in ("league","date","home","away"))
                    old=records.get(k)
                    if old and (old["ft"]!=row["ft"] or (old["ht"] is not None and row["ht"] is not None and old["ht"]!=row["ht"])):
                        conflicts.add(k)
                    elif not old or old["ht"] is None:
                        records[k]=row
            except Exception as exc:
                report["errors"].append(dict(source=url,error=type(exc).__name__))
    report["matches"]=[records[k] for k in sorted(records) if k not in conflicts]
    report["conflictsExcluded"]=len(conflicts)
    report["matchCount"]=len(report["matches"])
    report["leagueCount"]=len({m["league"] for m in report["matches"]})
    report["halfTimeCount"]=sum(m["ht"] is not None for m in report["matches"])
    return report

if __name__=="__main__":
    Path("historical_data.json").write_text(json.dumps(collect(date.today()),ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
