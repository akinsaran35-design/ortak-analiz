"""Research only: prior-day seasonal and rolling form summaries."""
from collections import defaultdict
from datetime import date, datetime
import json
from league_average_research import summarize
from h2h_history_research import collect
from league_config import LEAGUES
from results_source_pilot import TR, read

def profile(rows, cutoff):
    unique = {}
    conflicts = set()
    for r in rows:
        if date.fromisoformat(r["date"]) >= cutoff:
            continue
        k = (r["date"],r["home"],r["away"])
        if k in unique and unique[k] != r:
            conflicts.add(k)
        unique[k] = r
    seasons, teams = defaultdict(list), defaultdict(list)
    for k,r in sorted(unique.items()):
        if k in conflicts:
            continue
        d = date.fromisoformat(r["date"])
        seasons[d.year-(d.month<7)].append(r)
        for venue in ("home","away"):
            teams[r[venue],venue].append(r)
    return {"conflicts":len(conflicts),"seasons":{str(y):summarize(v,cutoff) for y,v in seasons.items()},"teams":[{"team":t,"venue":v,"latest":rs[-1]["date"],"windows":{str(n):summarize(rs[-n:],cutoff) for n in (5,10,20)}} for (t,v),rs in sorted(teams.items())]}

def build(now, reader=read):
    cutoff=now.astimezone(TR).date()
    groups=[]
    for label,code,sport in LEAGUES:
        rows,sources,errors,invalid=collect(code,sport,cutoff,reader)
        groups.append(dict(league=code,sources=sources,sourceErrors=errors,invalid=invalid,**profile(rows,cutoff)))
    return dict(version="5.53",cutoffExclusive=cutoff.isoformat(),predictionsEnabled=False,decision="PAS",groups=groups)

if __name__=="__main__":
    print(json.dumps(build(datetime.now(TR)),ensure_ascii=False,default=str))
