"""V5.41: historical referee-label coverage by league and season; no future assignments."""
import json
from datetime import datetime,date
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from football_context_research import referee_summary
from football_statistics_pilot import parse
from nine_league_results_pilot import SOURCES
from league_config import LEAGUES
from results_source_pilot import read,TR

def season_report(raw,code,sport,year,cutoff):
    rows,_,invalid=parse(raw,code,sport,cutoff)
    rows=[r for r in rows if date(year,7,1)<=date.fromisoformat(r["date"])<date(year+1,7,1)]
    evidence=referee_summary(raw,rows,code,sport)
    return dict(season=year,completedMatches=len(rows),invalid=invalid,assignedFixtures=evidence["assignedFixtures"],ambiguousFixtures=evidence["ambiguousFixtures"],coverage=evidence["assignedFixtures"]/len(rows) if rows else None,labels=evidence["labels"])

def build(now,reader=read):
    cutoff=now.astimezone(TR).date();year=cutoff.year-(cutoff.month<7)
    def group(entry):
        label,code,sport=entry
        records=[];errors=[]
        for y in range(year,year-6,-1):
            url=f"https://football-data.co.uk/mmz4281/{y%100:02d}{(y+1)%100:02d}/{SOURCES[code][0]}.csv"
            try:records.append(dict(source=url,**season_report(reader(url),code,sport,y,cutoff)))
            except (OSError,ValueError,TypeError,KeyError,AttributeError) as exc:errors.append(dict(season=y,source=url,error=type(exc).__name__))
        n=sum(r["completedMatches"] for r in records);a=sum(r["assignedFixtures"] for r in records)
        return dict(league=code,leagueName=label,completedMatches=n,assignedFixtures=a,coverage=a/n if n else None,seasons=records,errors=errors)
    with ThreadPoolExecutor(max_workers=6) as pool:groups=list(pool.map(group,LEAGUES))
    return dict(version="5.41",mode="historical_referee_label_coverage_only",updatedAt=now.isoformat(),cutoffExclusive=cutoff.isoformat(),identityVerified=False,upcomingAssignmentsVerified=False,predictionsEnabled=False,decision="PAS",groups=groups)

if __name__=="__main__":
    r=build(datetime.now(TR))
    Path("historical_referee_coverage.json").write_text(json.dumps(r,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    for g in r["groups"]:
        print(json.dumps({k:v for k,v in g.items() if k!="seasons"}|{"seasons":[dict(season=s["season"],matches=s["completedMatches"],assigned=s["assignedFixtures"],labels=len(s["labels"])) for s in g["seasons"]]},ensure_ascii=False))
    if not any(g["completedMatches"] for g in r["groups"]):raise SystemExit("No historical matches")
