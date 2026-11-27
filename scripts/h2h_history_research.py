"""V5.26: six-season league H2H enrichment, descriptive and schedule-bound."""
import json
from collections import Counter,defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import date,datetime
from pathlib import Path
from football_statistics_pilot import parse
from nine_league_results_pilot import SOURCES,result_key
from league_config import LEAGUES
from results_source_pilot import read,TR

SEASONS=6
LIMIT=12
def collect(code,sport,cutoff,reader=read):
    year=cutoff.year-(cutoff.month<7)
    csv_code,_=SOURCES[code]
    rows={};blocked=set();sources=[];errors=[];invalid=0
    for y in range(year,year-SEASONS,-1):
        url=f"https://football-data.co.uk/mmz4281/{y%100:02d}{(y+1)%100:02d}/{csv_code}.csv"
        try:
            records,_,bad=parse(reader(url),code,sport,cutoff)
            invalid+=bad
            valid=[r for r in records if date(y,7,1)<=date.fromisoformat(r["date"])<date(y+1,7,1)]
            if not valid:raise ValueError("no season rows")
            sources.append(dict(season=y,source=url,rows=len(valid)))
            for r in valid:
                k=(r["date"],r["home"],r["away"])
                if k in rows and rows[k]!=r:blocked.add(k)
                rows[k]=r
        except (OSError,ValueError,TypeError,KeyError,AttributeError) as exc:errors.append(dict(season=y,source=url,error=type(exc).__name__))
    return [r for k,r in rows.items() if k not in blocked],sources,errors,invalid+len(blocked)

def enrich_fixture(f,history,code,sport,cutoff,sources,errors):
    existing=f.get("formResearch")
    if not isinstance(existing,dict) or existing.get("version")!="5.06":return None
    if existing.get("asOfExclusive")!=cutoff.isoformat():return None
    names=f["match"].split(" – ")
    if len(names)!=2:return None
    home,away=names
    hk,ak=result_key(home,code,sport),result_key(away,code,sport)
    if not hk or not ak or hk==ak:return None
    rows={};conflicts=set()
    for r in history:
        if {r["home"],r["away"]}!={hk,ak} or r["date"]>=cutoff.isoformat():continue
        k=(r["date"],r["home"],r["away"])
        rows[k]=r
    for r in existing.get("h2h",[]):
        try:
            h,a=result_key(r["home"],code,sport),result_key(r["away"],code,sport)
            if {h,a}!={hk,ak} or date.fromisoformat(r["date"])>=cutoff:continue
            score=r["score"]
            if not isinstance(score,list) or len(score)!=2 or not all(type(v) is int and v>=0 for v in score):continue
            k=(r["date"],h,a)
            if k in rows and rows[k]["score"]!=score:conflicts.add(k)
            # CSV-backed records only in extended set. Preserve original when no CSV evidence.
        except (KeyError,TypeError,ValueError,AttributeError):continue
    matches=[]
    for k,r in sorted(rows.items(),reverse=True):
        if k in conflicts:continue
        m=dict(date=r["date"],home=home if r["home"]==hk else away,away=away if r["away"]==ak else home,score=r["score"],stats=r["stats"])
        matches.append(m)
    if matches:
        selected=matches[:LIMIT]
        existing["h2h"]=selected
        source="football-data.co.uk"
    elif conflicts:
        # Explicit contradiction: never display the contradictory original match.
        existing["h2h"]=[r for r in existing.get("h2h",[]) if (r["date"],result_key(r["home"],code,sport),result_key(r["away"],code,sport)) not in conflicts]
        selected=existing["h2h"];source="original_league_history_conflicts_filtered"
    else:
        selected=existing.get("h2h",[]);source="original_league_history"
    existing["h2hCoverage"]=dict(version="5.26",source=source,requestedSeasons=SEASONS,loadedSeasons=[s["season"] for s in sources],failedSeasons=[s["season"] for s in errors],limit=LIMIT,sample=len(selected),csvMatchesAvailable=len(matches),conflictsExcluded=len(conflicts),scope="same_league_only",predictionsEnabled=False)
    return dict(match=f["match"],date=f["date"],sample=len(selected),csvMatchesAvailable=len(matches),source=source)

def build(daily,now,reader=read):
    cutoff=now.astimezone(TR).date()
    # Do not enrich stale daily snapshots with a later information cutoff.
    stamp=datetime.fromisoformat(daily["updatedAt"])
    if stamp.tzinfo is None or stamp.astimezone(TR).date()!=cutoff:raise ValueError("stale daily snapshot")
    def group(entry):
        label,code,sport=entry
        history,sources,errors,invalid=collect(code,sport,cutoff,reader)
        records=[]
        for f in daily.get("upcoming",[]):
            if f.get("league")==label and f.get("date","")>=cutoff.isoformat():
                r=enrich_fixture(f,history,code,sport,cutoff,sources,errors)
                if r is not None:records.append(r)
        return dict(league=code,sources=sources,errors=errors,invalid=invalid,historicalRows=len(history),fixtures=len(records),sampleCounts=dict(Counter(r["sample"] for r in records)),rows=records)
    with ThreadPoolExecutor(max_workers=6) as pool:groups=list(pool.map(group,LEAGUES))
    report=dict(version="5.26",dailyUpdatedAt=daily["updatedAt"],cutoffExclusive=cutoff.isoformat(),mode="descriptive_research",decision="PAS",predictionsEnabled=False,groups=groups)
    return report

if __name__=="__main__":
    import sys
    path=Path("daily.json");daily=json.loads(path.read_text(encoding="utf-8"))
    # Research workflow replays only the existing snapshot date, never writes it back.
    apply="--apply" in sys.argv
    now=datetime.now(TR) if apply else datetime.fromisoformat(daily["updatedAt"])
    r=build(daily,now)
    Path("h2h_history_research.json").write_text(json.dumps(r,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    for g in r["groups"]:print(json.dumps({k:v for k,v in g.items() if k not in ("sources","rows")}|{"loadedSeasons":len(g["sources"])},ensure_ascii=False))
    if not any(g["sources"] for g in r["groups"]) and not apply:raise SystemExit("No history source")
    if apply:path.write_text(json.dumps(daily,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
