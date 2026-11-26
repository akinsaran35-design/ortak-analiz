"""Historical match statistics from existing football-data CSV source; no forecasts."""
import csv,io,json
from datetime import datetime,timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from results_source_pilot import read,TR
from nine_league_results_pilot import SOURCES,result_key
from league_config import LEAGUES

METRICS={"corners":("HC","AC"),"yellowCards":("HY","AY"),"redCards":("HR","AR"),"shots":("HS","AS"),"shotsOnTarget":("HST","AST"),"halfTimeGoals":("HTHG","HTAG")}
def integer(x):
    return int(x) if isinstance(x,str) and x.isascii() and x.isdigit() else None
def parse(raw,code,sport,cutoff):
    rows=csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    columns=set(rows.fieldnames or [])
    if not {"Date","HomeTeam","AwayTeam","FTHG","FTAG"}<=columns:raise ValueError("schema")
    available=[k for k,v in METRICS.items() if set(v)<=columns]
    unique={};blocked=set();invalid=0
    for row in rows:
        try:
            d=None
            for fmt in ("%d/%m/%Y","%d/%m/%y"):
                try:d=datetime.strptime(row["Date"],fmt).date();break
                except (ValueError,TypeError):pass
            if d is None:raise ValueError("date")
            if d>=cutoff:continue
            h,a=result_key(row["HomeTeam"],code,sport),result_key(row["AwayTeam"],code,sport)
            hg,ag=integer(row["FTHG"]),integer(row["FTAG"])
            if not h or not a or h==a or hg is None or ag is None:raise ValueError("identity or score")
            stats={}
            for name,(hc,ac) in METRICS.items():
                x,y=integer(row.get(hc)),integer(row.get(ac))
                if x is None or y is None:continue
                if name=="halfTimeGoals" and (x>hg or y>ag):continue
                stats[name]=[x,y]
            k=(d.isoformat(),h,a)
            item=dict(date=k[0],home=h,away=a,score=[hg,ag],stats=stats)
            if k in unique and unique[k]!=item:blocked.add(k)
            unique[k]=item
        except (ValueError,TypeError,KeyError,AttributeError):invalid+=1
    return [v for k,v in unique.items() if k not in blocked],available,invalid+len(blocked)

def describe(rows,team):
    selected=sorted((r for r in rows if team in (r["home"],r["away"])),key=lambda r:r["date"],reverse=True)[:10]
    out={}
    for metric in METRICS:
        values=[(r["stats"][metric][0],r["stats"][metric][1]) if r["home"]==team else tuple(reversed(r["stats"][metric])) for r in selected if metric in r["stats"]]
        n=len(values)
        out[metric]=dict(sample=n,forAverage=sum(x for x,y in values)/n if n else None,againstAverage=sum(y for x,y in values)/n if n else None)
    return dict(sample=len(selected),metrics=out)

def build(daily,now,reader=read):
    cutoff=now.astimezone(TR).date()
    year=cutoff.year if cutoff.month>=7 else cutoff.year-1
    def group(entry):
        label,code,sport=entry
        csv_code,_=SOURCES[code]
        url=f"https://football-data.co.uk/mmz4281/{year%100:02d}{(year+1)%100:02d}/{csv_code}.csv"
        g=dict(league=code,leagueName=label,source=url,availableMetrics=[],historicalRows=0,invalid=0,error=None,rows=[])
        try:
            rows,available,invalid=parse(reader(url),code,sport,cutoff)
            g.update(availableMetrics=available,historicalRows=len(rows),invalid=invalid)
            for f in daily.get("upcoming",[]):
                if f["league"]!=label:continue
                h,a=f["match"].split(" – ")
                hk,ak=result_key(h,code,sport),result_key(a,code,sport)
                if not hk or not ak or hk==ak:continue
                g["rows"].append(dict(date=f["date"],league=label,match=f["match"],home=describe(rows,hk),away=describe(rows,ak)))
        except (OSError,ValueError,TypeError,KeyError,AttributeError) as exc:g.update(error=type(exc).__name__,rows=[])
        return g
    with ThreadPoolExecutor(max_workers=4) as pool:groups=list(pool.map(group,LEAGUES))
    return dict(version="5.09",updatedAt=now.isoformat(),dailyUpdatedAt=daily.get("updatedAt"),cutoffExclusive=cutoff.isoformat(),source="football-data.co.uk",mode="descriptive_research",groups=groups,
        respondingLeagues=sum(g["error"] is None for g in groups),fixtureCount=sum(len(g["rows"]) for g in groups),predictionsEnabled=False,realBettingEnabled=False,decision="PAS")
def main():
    daily=json.loads(Path("daily.json").read_text(encoding="utf-8"))
    r=build(daily,datetime.now(TR))
    Path("football_statistics_pilot.json").write_text(json.dumps(r,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Historical statistics:",json.dumps([{k:v for k,v in g.items() if k not in ("rows","source")} for g in r["groups"]],ensure_ascii=False))
    print("Source leagues:",r["respondingLeagues"],"fixture rows:",r["fixtureCount"])
    if not r["respondingLeagues"]:raise SystemExit("No source response")
if __name__=="__main__":main()
