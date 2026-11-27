"""V5.31: six-season historical metric coverage, consistency and seasonal summaries."""
import json,math
from datetime import datetime,date
from collections import Counter
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from h2h_history_research import collect
from football_statistics_pilot import METRICS
from football_context_research import half_history
from league_config import LEAGUES
from results_source_pilot import TR,read

def valid_pair(x):
    return isinstance(x,list) and len(x)==2 and all(type(v) is int and v>=0 for v in x)

def describe(values,n):
    sample=len(values)
    totals=sorted(sum(p) for p in values)
    def quantile(p):
        return totals[max(0,math.ceil(p*sample)-1)] if sample else None
    return dict(sample=sample,missing=n-sample,coverage=sample/n if n else None,homeAverage=sum(p[0] for p in values)/sample if sample else None,awayAverage=sum(p[1] for p in values)/sample if sample else None,totalAverage=sum(totals)/sample if sample else None,median=quantile(.5),p10=quantile(.1),p90=quantile(.9))

def summarize(rows):
    paired={k:[] for k in ("goals",*METRICS,"secondHalfGoals")}
    accepted=[];issues=Counter()
    for r in rows:
        score=r["score"]
        if not valid_pair(score):
            issues["invalidScore"]+=1;continue
        paired["goals"].append(score)
        stats=r["stats"]
        clean={k:v for k,v in stats.items() if k in METRICS and valid_pair(v)}
        if "halfTimeGoals" in clean and any(h>f for h,f in zip(clean["halfTimeGoals"],score)):
            clean.pop("halfTimeGoals");issues["halfTimeExceedsFinal"]+=1
        if "shotsOnTarget" in clean and "shots" in clean and any(a>b for a,b in zip(clean["shotsOnTarget"],clean["shots"])):
            clean.pop("shotsOnTarget");issues["shotsOnTargetExceedsShots"]+=1
        for k,v in clean.items():paired[k].append(v)
        if "halfTimeGoals" in clean:paired["secondHalfGoals"].append([f-h for f,h in zip(score,clean["halfTimeGoals"])])
        accepted.append(dict(r,stats=clean))
    n=len(accepted)
    half=half_history(accepted)
    if sum(v for k,v in half["counts"].items() if k.startswith("halfFull:"))!=half["sample"]:raise ValueError("half/full count mismatch")
    return dict(matches=n,issues=dict(issues),metrics={k:describe(v,n) for k,v in paired.items()},halves=half)

def build(now,reader=read):
    cutoff=now.astimezone(TR).date()
    def group(entry):
        label,code,sport=entry
        rows,sources,errors,invalid=collect(code,sport,cutoff,reader)
        def season(r):
            d=date.fromisoformat(r["date"])
            return d.year-(d.month<7)
        return dict(league=code,leagueName=label,sources=sources,sourceErrors=errors,sourceInvalid=invalid,aggregate=summarize(rows),seasons=[dict(season=s["season"],**summarize([r for r in rows if season(r)==s["season"]])) for s in sources])
    with ThreadPoolExecutor(max_workers=6) as pool:groups=list(pool.map(group,LEAGUES))
    return dict(version="5.31",mode="historical_metric_coverage_only",updatedAt=now.isoformat(),cutoffExclusive=cutoff.isoformat(),source="football-data.co.uk",predictionsEnabled=False,modelCalibrated=False,decision="PAS",groups=groups)
if __name__=="__main__":
    r=build(datetime.now(TR))
    Path("historical_metric_coverage.json").write_text(json.dumps(r,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    for g in r["groups"]:
        a=g["aggregate"]
        print(json.dumps(dict(league=g["league"],matches=a["matches"],seasons=len(g["seasons"]),samples={k:v["sample"] for k,v in a["metrics"].items()},issues=a["issues"],sourceErrors=g["sourceErrors"]),ensure_ascii=False))
    if not any(g["aggregate"]["matches"] for g in r["groups"]):raise SystemExit("No historical source data")
