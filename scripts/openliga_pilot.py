"""Separate ODbL research dataset; Data from OpenLigaDB (www.openligadb.de)."""
import json,time
from datetime import date,timedelta
from pathlib import Path
from urllib.request import urlopen
from historical_baseline import evaluate

def normalize(rows,league,today):
    out={}
    conflicts=set()
    for m in rows:
        try:
            if m["matchIsFinished"] is not True: continue
            d=date.fromisoformat(m["matchDateTime"][:10])
            if not today-timedelta(days=365)<=d<today: continue
            scores={}
            for s in m["matchResults"]:
                k=s["resultTypeID"]
                if k not in (1,2): continue
                v=[s["pointsTeam1"],s["pointsTeam2"]]
                if not all(type(x) is int and x>=0 for x in v): raise ValueError()
                if k in scores and scores[k]!=v: raise ValueError()
                scores[k]=v
            ft=scores[2]; ht=scores.get(1)
            if ht and any(a>b for a,b in zip(ht,ft)): ht=None
            h=str(m["team1"]["teamId"]); a=str(m["team2"]["teamId"])
            if h==a: continue
            row=dict(date=d.isoformat(),league=league,home=h,away=a,ft=ft,ht=ht,source="https://www.openligadb.de",matchID=m["matchID"])
            k=m["matchID"]
            if k in out and out[k]!=row: conflicts.add(k)
            out[k]=row
        except (KeyError,TypeError,ValueError): continue
    return [v for k,v in out.items() if k not in conflicts]

def discover_leagues(today):
    with urlopen("https://api.openligadb.de/getavailableleagues",timeout=20) as f:
        catalog=json.load(f)
    pairs=set()
    for item in catalog:
        sport=item.get("sport") or {}
        if str(sport.get("sportName","")).casefold() not in ("fußball","fussball","football","soccer"): continue
        shortcut=item.get("leagueShortcut")
        season=str(item.get("leagueSeason",""))
        if isinstance(shortcut,str) and shortcut and season in (str(today.year-1),str(today.year)):
            pairs.add((shortcut,int(season)))
    return sorted(pairs)

def run(today):
    rows=[];errors=[]
    pairs={(league,year) for league in ("bl1","bl2","bl3") for year in (today.year-1,today.year)}
    try: pairs.update(discover_leagues(today))
    except Exception as e: errors.append(dict(stage="discovery",error=type(e).__name__))
    ordered=sorted(pairs,key=lambda x:(x[0] not in ("bl1","bl2","bl3"),x))
    for league,year in ordered[:60]:
        if True:
            try:
                with urlopen(f"https://api.openligadb.de/getmatchdata/{league}/{year}",timeout=20) as f:
                    rows.extend(normalize(json.load(f),league,today))
            except Exception as e: errors.append(dict(league=league,year=year,error=type(e).__name__))
            time.sleep(2)
    unique={}; conflicts=set()
    for row in rows:
        k=row["matchID"]
        if k in unique and unique[k]!=row: conflicts.add(k)
        unique[k]=row
    rows=[v for k,v in unique.items() if k not in conflicts]
    print("Football catalog:",len(pairs),"requested:",min(60,len(pairs)),"conflicts:",len(conflicts),"league codes:",len({r["league"] for r in rows}))
    result=dict(status="research_only",realBettingEnabled=False,license="ODbL-1.0",attribution="Data from OpenLigaDB (www.openligadb.de)",asOf=today.isoformat(),matches=rows,errors=errors)
    Path("openliga_pilot.json").write_text(json.dumps(result,indent=2))
    report=evaluate(rows,today)
    weighted=evaluate(rows,today,weighted=True)
    strength=evaluate(rows,today,strength=True)
    print("League strength comparison:",strength)
    Path("openliga_strength.json").write_text(json.dumps(strength,indent=2))
    from historical_tuning import tune
    tuning=tune(rows,today)
    Path("openliga_tuning.json").write_text(json.dumps(tuning,indent=2))
    print("Validation tuning:",tuning)
    comparison=dict(status="research_only",realBettingEnabled=False,baseline=report,weighted=weighted,holdoutPreviouslyInspected=True)
    print("Weighted comparison:",comparison)
    Path("openliga_comparison.json").write_text(json.dumps(comparison,indent=2))
    print("OpenLigaDB pilot:",len(rows),"errors:",errors,"baseline:",report)
    Path("openliga_baseline.json").write_text(json.dumps(report,indent=2))
if __name__=="__main__": run(date.today())
