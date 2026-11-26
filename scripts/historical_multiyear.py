"""Separate multi-year core-league research, fixed baseline, non-overlapping test windows."""
import json,time
from datetime import date,timedelta
from pathlib import Path
from urllib.request import urlopen
from openliga_pilot import normalize
from historical_baseline import evaluate
def run(today):
    rows={}; conflicts=set(); errors=[]
    for league in ("bl1","bl2","bl3"):
        for year in range(today.year-4,today.year+1):
            try:
                with urlopen(f"https://api.openligadb.de/getmatchdata/{league}/{year}",timeout=20) as f:
                    for row in normalize(json.load(f),league,today,days=1460):
                        k=row["matchID"]
                        if k in rows and rows[k]!=row: conflicts.add(k)
                        rows[k]=row
            except Exception as e: errors.append(dict(league=league,year=year,error=type(e).__name__))
            time.sleep(2)
    data=[v for k,v in rows.items() if k not in conflicts]
    windows=[]
    for offset in range(0,1096,61):
        end=today-timedelta(days=offset)
        report=evaluate(data,end)
        windows.append(dict(asOf=end.isoformat(),metrics=report["metrics"],skipped=report["skipped"]))
    result=dict(status="research_only",realBettingEnabled=False,independentHoldout=False,attribution="Data from OpenLigaDB (www.openligadb.de)",license="ODbL-1.0",matchCount=len(data),errors=errors,conflicts=len(conflicts),windows=windows)
    Path("openliga_multiyear.json").write_text(json.dumps(result,indent=2))
    print("Multiyear archive:",len(data),"errors:",errors,"test counts:",{k:sum(w["metrics"].get(k,{}).get("n",0) for w in windows) for k in ("over15","over25","btts")})
if __name__=="__main__": run(date.today())
