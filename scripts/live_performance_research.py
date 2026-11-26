"""Prospective live-scenario research metrics. No betting or result inference."""
import math
from collections import defaultdict,Counter
from datetime import datetime
from urllib.parse import urlparse
from results_source_pilot import TR
from live_rate_link import stamp

MARKETS=("homeWin","draw","awayWin","over15","over25","btts")
def probs(s):
    if not isinstance(s,dict) or s.get("mode")!="conditional_research_scenario" or s.get("modelCalibrated") is not False or s.get("predictionsEnabled") is not False:return None
    p={k:s.get(k) for k in MARKETS}
    if not all(type(v) in (int,float) and math.isfinite(v) and 0<=v<=1 for v in p.values()):return None
    if abs(sum(p[k] for k in MARKETS[:3])-1)>1e-8:return None
    return p

def archive(report,records,now):
    """Keep one first-observed scenario per event; no retroactive overwrite."""
    if report.get("mode")!="live_link_research_only" or report.get("predictionsEnabled") is not False:return records
    generated=stamp(report.get("updatedAt"))
    if not generated or not 0<=(now-generated).total_seconds()<=120:return records
    rows=report.get("rows",[])
    if not isinstance(rows,list) or len(rows)>12:return records
    counts=Counter((r.get("league"),r.get("eventId")) for r in rows)
    out=dict(records)
    for r in rows:
        ident=(r.get("league"),r.get("eventId"))
        if counts[ident]!=1 or r.get("status")!="conditional_scenario":continue
        if not all(isinstance(x,str) and x for x in ident):continue
        kickoff=stamp(r.get("kickoff"));received=stamp(r.get("receivedAt"));prematch=stamp(report.get("prematchUpdatedAt"))
        if not kickoff or not received or not prematch or not prematch<kickoff<=received<=generated:continue
        if (generated-received).total_seconds()>120:continue
        p=probs(r.get("scenario"))
        if not p:continue
        key=":".join(ident)
        if key in out:continue
        out[key]=dict(league=ident[0],eventId=ident[1],date=kickoff.astimezone(TR).date().isoformat(),home=r["home"],away=r["away"],kickoff=kickoff.isoformat(),recordedAt=now.isoformat(),minute=r["scenario"]["minute"],score=r["scenario"]["score"],probabilities=p)
    return out

def evaluate(records,verified,now):
    """Match exact league/date/ordered names to corroborated completed scores."""
    results=defaultdict(set)
    for r in verified:
        try:
            if r["date"]>=now.astimezone(TR).date().isoformat():continue
            h,a=r["result"]
            if any(type(v) is not int or v<0 for v in (h,a)):continue
            hosts={urlparse(u).hostname for u in r["sources"] if isinstance(u,str) and u.startswith("https://")}
            if len(hosts-{None})<2:continue
            results[(r["date"],r["league"],r["home"],r["away"])].add((h,a))
        except (ValueError,TypeError,KeyError,AttributeError):continue
    errors=defaultdict(list);counts=Counter()
    for r in records.values():
        ident=(r["date"],r["league"],r["home"],r["away"])
        found=results[ident]
        recorded=stamp(r.get("recordedAt"))
        if not recorded or recorded>now or recorded.astimezone(TR).date().isoformat()>r["date"]:
            counts["invalid_record"]+=1;continue
        if len(found)!=1:
            counts["conflict" if found else "pending"]+=1;continue
        h,a=next(iter(found))
        if h<r["score"][0] or a<r["score"][1]:
            counts["score_conflict"]+=1;continue
        outcomes=(h>a,h==a,h<a,h+a>=2,h+a>=3,h>0 and a>0)
        for k,y in zip(MARKETS,outcomes):errors[k].append((r["probabilities"][k]-int(y))**2)
        counts["evaluated"]+=1
    return dict(version="5.19",mode="research_only",modelCalibrated=False,predictionsEnabled=False,decision="PAS",recorded=len(records),counts=dict(counts),brier={k:sum(errors[k])/len(errors[k]) if errors[k] else None for k in MARKETS})
