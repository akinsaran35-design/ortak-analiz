"""Read-only domestic H2H coverage, not a prediction model."""
from collections import defaultdict
from datetime import date, datetime
from concurrent.futures import ThreadPoolExecutor
import json
from h2h_history_research import collect, EXTRA_DIVISIONS
from league_average_research import summarize
from league_config import LEAGUES
from results_source_pilot import TR, read

def pairs(rows, cutoff):
    unique, conflicts = {}, set()
    for r in rows:
        if date.fromisoformat(r["date"]) >= cutoff:
            continue
        k=(r["date"],r["home"],r["away"])
        if k in unique and unique[k]!=r:
            conflicts.add(k)
        unique[k]=r
    groups=defaultdict(list)
    for k,r in sorted(unique.items()):
        if k not in conflicts:
            groups[tuple(sorted((r["home"],r["away"])))].append(r)
    return {"conflicts":len(conflicts),"pairs":[dict(teams=list(k),sample=len(rs),latest=rs[-1]["date"],ageDays=(cutoff-date.fromisoformat(rs[-1]["date"])).days,competitions=sorted({r["competition"] for r in rs}),metrics=summarize(rs[-12:],cutoff)["metrics"]) for k,rs in sorted(groups.items())]}

def build(now, reader=read):
    cutoff=now.astimezone(TR).date()
    def group(entry):
        _,code,sport=entry
        rows,sources,errors,invalid=collect(code,sport,cutoff,reader)
        extra=EXTRA_DIVISIONS.get(code)
        if extra:
            more,src,err,bad=collect(code,sport,cutoff,reader,extra)
            rows+=more; sources+=src; errors+=err; invalid+=bad
        return dict(league=code,sources=sources,errors=errors,invalid=invalid,**pairs(rows,cutoff))
    with ThreadPoolExecutor(max_workers=6) as pool:
        groups=list(pool.map(group,LEAGUES))
    return dict(version="5.55",cutoffExclusive=cutoff.isoformat(),predictionsEnabled=False,decision="PAS",groups=groups)

if __name__=="__main__":
    print(json.dumps(build(datetime.now(TR)),ensure_ascii=False))
