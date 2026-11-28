"""Historical referee observations, not future assignments or predictions."""
import csv,io,json
from collections import defaultdict
from datetime import datetime,date
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from football_statistics_pilot import parse
from nine_league_results_pilot import SOURCES,result_key
from league_config import LEAGUES
from extra_historical_metric_coverage import LEAGUES as EXTRA
from results_source_pilot import TR,read

def observations(raw,code,sport,cutoff,season):
    records,_,invalid=parse(raw,code,sport,cutoff)
    eligible={(r["date"],r["home"],r["away"]):r for r in records
              if date(season,7,1)<=date.fromisoformat(r["date"])<date(season+1,7,1)}
    reader=csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    has_field="Referee" in (reader.fieldnames or [])
    refs=defaultdict(set)
    if has_field:
        for row in reader:
            try:
                for fmt in ("%d/%m/%Y","%d/%m/%y"):
                    try:d=datetime.strptime(row["Date"],fmt).date();break
                    except ValueError:d=None
                if d is None:continue
                k=(d.isoformat(),result_key(row["HomeTeam"],code,sport),
                   result_key(row["AwayTeam"],code,sport))
                if k not in eligible:continue
                name=" ".join((row.get("Referee") or "").split())
                if name and name.casefold() not in ("n/a","na","unknown","-","nan"):
                    refs[k].add(name)
            except (KeyError,TypeError,ValueError,AttributeError):continue
    assigned=[dict(r,referee=next(iter(refs[k]))) for k,r in eligible.items() if len(refs[k])==1]
    return len(eligible),assigned,has_field,sum(len(v)>1 for v in refs.values()),invalid

def describe(rows):
    def metric(k):
        vals=[sum(r["stats"][k]) for r in rows if k in r["stats"]]
        return dict(sample=len(vals),mean=sum(vals)/len(vals) if vals else None)
    return dict(matches=len(rows),yellowCards=metric("yellowCards"),redCards=metric("redCards"))

def build(now,reader=read):
    cutoff=now.astimezone(TR).date()
    year=cutoff.year-(cutoff.month<7)
    entries=[(label,code,sport,SOURCES[code][0]) for label,code,sport in LEAGUES]+list(EXTRA)
    def group(entry):
        label,code,sport,csv_code=entry
        total=0;assigned=[];sources=[];errors=[];conflicts=0
        for y in (year,year-1):
            url=f"https://football-data.co.uk/mmz4281/{y%100:02d}{(y+1)%100:02d}/{csv_code}.csv"
            try:
                n,rows,field,bad,invalid=observations(reader(url),code,sport,cutoff,y)
                total+=n;assigned.extend(rows);conflicts+=bad
                sources.append(dict(season=y,source=url,completedMatches=n,refereeFieldPresent=field,assignedMatches=len(rows),invalid=invalid))
            except (OSError,ValueError,TypeError,KeyError,AttributeError) as exc:
                errors.append(dict(season=y,error=type(exc).__name__))
        by=defaultdict(list)
        for row in assigned:by[row["referee"]].append(row)
        return dict(league=code,leagueName=label,completedMatches=total,
            assignedMatches=len(assigned),missingAssignments=total-len(assigned),
            conflictingAssignments=conflicts,sourceErrors=errors,sources=sources,
            referees=[dict(name=name,**describe(rows)) for name,rows in sorted(by.items())])
    with ThreadPoolExecutor(max_workers=4) as pool:groups=list(pool.map(group,entries))
    return dict(version="7.14",updatedAt=now.isoformat(),cutoffExclusive=cutoff.isoformat(),
        mode="historical_referee_observations",source="football-data.co.uk",decision="PAS",
        predictionsEnabled=False,futureAssignmentsVerified=False,groups=groups,
        completedMatches=sum(g["completedMatches"] for g in groups),
        assignedMatches=sum(g["assignedMatches"] for g in groups),
        leaguesWithAssignments=sum(g["assignedMatches"]>0 for g in groups))

if __name__=="__main__":
    report=build(datetime.now(TR))
    Path("referee_coverage.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    for g in report["groups"]:
        print(json.dumps({k:v for k,v in g.items() if k not in ("referees","sources")},ensure_ascii=False))
    print(json.dumps({k:v for k,v in report.items() if k!="groups"},ensure_ascii=False))
    if not report["completedMatches"]:raise SystemExit("No completed source matches")
