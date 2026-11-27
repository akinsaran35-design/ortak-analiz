"""V5.37: per-fixture history completeness and freshness diagnostics."""
import json
from collections import Counter
from datetime import date,datetime
from pathlib import Path
from league_config import LEAGUES
from results_source_pilot import TR

METRICS=("halfTimeGoals","corners","yellowCards","redCards","shots","shotsOnTarget")
MAX_FORM_AGE_DAYS=21
MIN_FORM=5
MIN_H2H=5
MIN_METRIC=5
def age(value,cutoff):
    try:
        n=(cutoff-date.fromisoformat(value)).days
        return n if n>0 else None
    except (TypeError,ValueError):return None

def form_status(side,cutoff):
    rows=side.get("rows",[])
    n=side.get("sample")
    if type(n) is not int or n!=len(rows) or not 0<=n<=5:return dict(status="invalid",sample=None,latestAgeDays=None)
    if not n:return dict(status="missing",sample=0,latestAgeDays=None)
    ages=[age(r.get("date"),cutoff) for r in rows]
    if any(v is None for v in ages):return dict(status="invalid",sample=n,latestAgeDays=None)
    latest=min(ages)
    status="stale" if latest>MAX_FORM_AGE_DAYS else "partial" if n<MIN_FORM else "available"
    return dict(status=status,sample=n,latestAgeDays=latest)

def metric_samples(side):
    return {k:side.get("metrics",{}).get(k,{}).get("sample",0) for k in METRICS}

def build(daily,context,statistics):
    stamp=datetime.fromisoformat(daily["updatedAt"])
    if stamp.tzinfo is None:raise ValueError("timezone")
    cutoff=stamp.astimezone(TR).date()
    if context.get("dailyUpdatedAt")!=daily["updatedAt"] or statistics.get("dailyUpdatedAt")!=daily["updatedAt"]:raise ValueError("snapshot mismatch")
    labels={code:label for label,code,_ in LEAGUES}
    cg={g["league"]:g for g in context["groups"]}
    sg={g["league"]:g for g in statistics["groups"]}
    if set(cg)!=set(labels) or set(sg)!=set(labels):raise ValueError("league coverage")
    groups=[]
    for code,label in labels.items():
        c,s=cg[code],sg[code]
        cr={(r["date"],r["match"]):r for r in c["rows"]}
        sr={(r["date"],r["match"]):r for r in s["rows"]}
        records=[];counts=Counter()
        source_age=age(c.get("latestCompletedDate"),cutoff)
        for f in daily["upcoming"]:
            if f["league"]!=label:continue
            key=(f["date"],f["match"]);form=f.get("formResearch",{})
            h2h=form.get("h2h",[])
            n=len(h2h)
            hs="missing" if n==0 else "partial" if n<MIN_H2H else "available"
            if form.get("asOfExclusive")!=cutoff.isoformat() or any(age(r.get("date"),cutoff) is None for r in h2h):hs="invalid"
            sides={k:form_status(form.get(k,{}),cutoff) for k in ("home","away")}
            if form.get("asOfExclusive")!=cutoff.isoformat():
                for v in sides.values():v["status"]="invalid"
            m={k:metric_samples(sr.get(key,{}).get(k,{})) for k in ("home","away")}
            venue={k:metric_samples(cr.get(key,{}).get(k+"Venue",{})) for k in ("home","away")}
            flags=[]
            for k,v in sides.items():
                if v["status"]!="available":flags.append(k+"Form:"+v["status"])
            if hs!="available":flags.append("h2h:"+hs)
            if key not in sr:flags.append("statistics:missing")
            if key not in cr:flags.append("context:missing")
            for field,samples in (("overall",m),("venue",venue)):
                for side,values in samples.items():
                    for metric,nm in values.items():
                        if type(nm) is not int or not 0<=nm<=10:flags.append(field+":"+side+":"+metric+":invalid")
                        elif nm<MIN_METRIC:flags.append(field+":"+side+":"+metric+(":missing" if nm==0 else ":partial"))
            if source_age is None:flags.append("leagueHistory:missing")
            elif source_age>MAX_FORM_AGE_DAYS:flags.append("leagueHistory:stale")
            counts.update(flags)
            records.append(dict(date=f["date"],match=f["match"],form=sides,h2h=dict(sample=n,status=hs),metricSamples=m,venueMetricSamples=venue,flags=flags))
        groups.append(dict(league=code,leagueName=label,latestLeagueResultAgeDays=source_age,fixtures=len(records),flags=dict(counts),rows=records))
    return dict(version="5.37",mode="fixture_data_quality_only",dailyUpdatedAt=daily["updatedAt"],cutoffExclusive=cutoff.isoformat(),predictionsEnabled=False,decision="PAS",thresholds=dict(formDays=MAX_FORM_AGE_DAYS,formSample=MIN_FORM,h2hSample=MIN_H2H,metricSample=MIN_METRIC),groups=groups)
def main():
    def load(name):return json.loads(Path(name).read_text(encoding="utf-8"))
    r=build(load("daily.json"),load("football_context_research.json"),load("football_statistics_pilot.json"))
    Path("fixture_data_quality.json").write_text(json.dumps(r,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    for g in r["groups"]:
        print(json.dumps({k:v for k,v in g.items() if k!="rows"},ensure_ascii=False))
if __name__=="__main__":main()
