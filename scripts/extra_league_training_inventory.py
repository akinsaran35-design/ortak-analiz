"""V6.49 historical training-source inventory, not a verified result archive."""
import csv,io,json
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import date,datetime
from pathlib import Path
from extra_league_score_audit import COMPETITIONS
from results_source_pilot import read,score,TR
from match_odds import normalize

START=date(2023,7,1)
END=date(2026,8,30)  # Exclusive: before the original 90-day pilot.
SEASONS=range(2023,2027)

def parse_season(raw,league,year,url):
    reader=csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    if not {"Date","HomeTeam","AwayTeam","FTHG","FTAG"}.issubset(reader.fieldnames or []):
        raise ValueError("CSV schema")
    counts=Counter()
    rows=[]
    for r in reader:
        counts["read"]+=1
        d=None
        for fmt in ("%d/%m/%Y","%d/%m/%y"):
            try:
                d=datetime.strptime(r["Date"],fmt).date()
                break
            except (ValueError,TypeError):
                pass
        if d is None:
            counts["invalidDate"]+=1
            continue
        if not date(year,7,1)<=d<date(year+1,7,1) or not START<=d<END:
            counts["outsideWindow"]+=1
            continue
        try:
            h,a=normalize(r["HomeTeam"]),normalize(r["AwayTeam"])
            if not h or not a or h==a:
                raise ValueError("identity")
            s=score(r["FTHG"],r["FTAG"])
        except (ValueError,TypeError,KeyError,AttributeError):
            counts["invalidScoreOrIdentity"]+=1
            continue
        stats={}
        for name,columns in {"shots":("HS","AS"),"shotsOnTarget":("HST","AST"),"corners":("HC","AC")}.items():
            try:
                stats[name]=score(*(r.get(c) for c in columns))
            except (ValueError,TypeError,KeyError):
                continue
        if "shots" in stats and "shotsOnTarget" in stats and any(t>v for t,v in zip(stats["shotsOnTarget"],stats["shots"])):
            del stats["shotsOnTarget"]
        rows.append(dict(league=league,date=d.isoformat(),home=h,away=a,score=s,stats=stats,source=url,
            season=year,verification="single_source_only"))
        counts["eligibleRows"]+=1
    return rows,dict(counts)

def deduplicate(rows):
    grouped={}
    for r in rows:
        k=(r["league"],r["date"],r["home"],r["away"])
        grouped.setdefault(k,[]).append(r)
    kept=[]
    duplicates=0
    conflicts=0
    for k,items in sorted(grouped.items()):
        if len(items)!=1:
            if len({tuple(r["score"]) for r in items})>1:
                conflicts+=1
            else:
                duplicates+=1
            continue
        kept.append(items[0])
    return kept,duplicates,conflicts

def fetch_season(job,reader):
    league,code,year=job
    url=f"https://football-data.co.uk/mmz4281/{year%100:02d}{(year+1)%100:02d}/{code}.csv"
    try:
        rows,counts=parse_season(reader(url),league,year,url)
        return rows,dict(league=league,season=year,source=url,counts=counts,error=None)
    except (OSError,ValueError,TypeError,KeyError,AttributeError) as exc:
        return [],dict(league=league,season=year,source=url,counts={},error=type(exc).__name__)

def build(reader=read):
    jobs=[(l,c,y) for l,c in COMPETITIONS for y in SEASONS]
    with ThreadPoolExecutor(max_workers=4) as pool:
        results=list(pool.map(lambda job:fetch_season(job,reader),jobs))
    rows,duplicates,conflicts=deduplicate([r for rs,_ in results for r in rs])
    sources=[s for _,s in results]
    report=dict(version="6.49",mode="single_source_training_inventory",start=START.isoformat(),
        endExclusive=END.isoformat(),requestedSources=len(jobs),successfulSources=sum(s["error"] is None for s in sources),
        nonemptySources=sum(bool(rs) for rs,_ in results),uniqueTrainingCandidates=len(rows),
        duplicateIdentitiesExcluded=duplicates,conflictingIdentitiesExcluded=conflicts,
        independentlyVerified=0,leagueCounts=dict(Counter(r["league"] for r in rows)),
        seasonCounts=dict(Counter(str(r["season"]) for r in rows)),sources=sources,
        overlapsPilotDateWindow=False,existingArchivesModified=False,usedForTraining=False,productionModelValidated=False)
    return report,rows

if __name__=="__main__":
    report,rows=build()
    report["updatedAt"]=datetime.now(TR).isoformat()
    Path("extra_training_inventory.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    Path("extra_training_candidates.json").write_text(json.dumps(rows,ensure_ascii=False)+"\n",encoding="utf-8")
    print("TRAINING_INVENTORY_649",json.dumps(report))
