"""Separate multi-year core-league research, fixed baseline, non-overlapping test windows."""
import json,time
from datetime import date,timedelta
from pathlib import Path
from urllib.request import urlopen
from urllib.parse import quote
from openliga_pilot import normalize
from historical_baseline import evaluate
from historical_archive_merge import merge
def run(today):
    rows={}; conflicts=set(); errors=[]
    pairs={(league,year) for league in ("bl1","bl2","bl3") for year in range(today.year-4,today.year+1)}
    try:
        with urlopen("https://api.openligadb.de/getavailableleagues",timeout=20) as f:
            catalog=json.load(f)
        for item in catalog:
            sport=item.get("sport") or {}
            if str(sport.get("sportName","")).casefold() not in ("fußball","fussball","football","soccer"): continue
            shortcut=item.get("leagueShortcut")
            season=str(item.get("leagueSeason",""))
            if isinstance(shortcut,str) and shortcut and season in {str(y) for y in range(today.year-4,today.year+1)}:
                pairs.add((shortcut,int(season)))
    except Exception as e: errors.append(dict(stage="catalog",error=type(e).__name__))
    ordered=sorted(pairs,key=lambda x:(-x[1],x[0]))
    # Scan the full discovered catalog; report any failed requests.
    requested=ordered
    batch_index=0
    batches=1
    for league,year in requested:
        if True:
            try:
                with urlopen(f"https://api.openligadb.de/getmatchdata/{quote(league,safe='')}/{year}",timeout=20) as f:
                    for row in normalize(json.load(f),league,today,days=1460):
                        k=row["matchID"]
                        if k in rows and rows[k]!=row: conflicts.add(k)
                        rows[k]=row
            except Exception as e: errors.append(dict(league=league,year=year,error=type(e).__name__))
            time.sleep(2)
    data=[v for k,v in rows.items() if k not in conflicts]
    archive=Path("openliga_archive.json")
    previous=json.loads(archive.read_text()) if archive.exists() else {}
    data,blocked=merge(previous.get("matches",[]),data,[str(k) for k in conflicts]+previous.get("blocked",[]),(today-timedelta(days=1460)).isoformat(),today.isoformat())
    Path("openliga_archive.json").write_text(json.dumps(dict(asOf=today.isoformat(), attribution="Data from OpenLigaDB (www.openligadb.de)", license="ODbL-1.0", matches=data, blocked=blocked, errors=errors, conflicts=len(blocked))))
    windows=[]
    for offset in range(0,1096,61):
        end=today-timedelta(days=offset)
        report=evaluate(data,end)
        windows.append(dict(asOf=end.isoformat(),metrics=report["metrics"],skipped=report["skipped"]))
    result=dict(status="research_only",realBettingEnabled=False,independentHoldout=False,attribution="Data from OpenLigaDB (www.openligadb.de)",license="ODbL-1.0",matchCount=len(data),catalogPairs=len(pairs),requestedPairs=len(requested),batchIndex=batch_index,batches=batches,leagueCodeCount=len({r['league'] for r in data}),errors=errors,conflicts=len(conflicts),windows=windows)
    Path("openliga_multiyear.json").write_text(json.dumps(result,indent=2))
    print("Multiyear catalog:",len(pairs),"requested:",len(requested),"batch:",batch_index,"of",batches)
    print("Multiyear archive:",len(data),"errors:",errors,"test counts:",{k:sum(w["metrics"].get(k,{}).get("n",0) for w in windows) for k in ("over15","over25","btts")})
if __name__=="__main__": run(date.today())
