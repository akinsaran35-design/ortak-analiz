"""V6.51 xT event-data readiness audit; no inferred coordinates or xT values."""
import json, math
from datetime import datetime,timedelta
from pathlib import Path
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from extra_league_score_audit import COMPETITIONS
from extra_xg_source_audit import BASE,LOOKBACK,PER_LEAGUE,completed_events
from results_source_pilot import read,TR

def coordinate_pair(value):
    if not isinstance(value,dict):
        return None
    x,y=value.get("x"),value.get("y")
    if any(type(v) not in (float,int) or not math.isfinite(v) for v in (x,y)):
        return None
    return (x,y)

def inspect_events(payload,fixture):
    try:
        header=payload["header"]
        if str(header["id"])!=fixture["eventId"]:
            return dict(status="event_mismatch")
        comp,=header["competitions"]
        status=comp["status"]["type"]
        if status.get("completed") is not True or status.get("name")!="STATUS_FULL_TIME":
            return dict(status="not_final")
        teams={v["homeAway"]:str(v["team"]["id"]) for v in comp["competitors"]}
        if len(comp["competitors"])!=2 or teams!=fixture["teams"]:
            return dict(status="team_mismatch")
    except (KeyError,ValueError,TypeError,AttributeError):
        return dict(status="summary_schema")
    groups={}
    # Inspect explicit structured event collections. Text commentary is not location data.
    for name in ("plays","keyEvents","commentary","playByPlay"):
        events=payload.get(name)
        if not isinstance(events,list):
            continue
        rows=[r for r in events if isinstance(r,dict)]
        types=Counter()
        keys=set()
        movements=paired=typed_outcomes=identified=0
        for r in rows:
            keys.update(r.keys())
            kind=r.get("type")
            if isinstance(kind,dict):
                kind=kind.get("text",kind.get("name",""))
            kind=str(kind or "").strip().casefold()
            types[kind or "unspecified"]+=1
            if kind not in ("pass","carry","dribble","ball carry"):
                continue
            movements+=1
            start=coordinate_pair(r.get("start"))
            end=coordinate_pair(r.get("end"))
            if start is None or end is None:
                continue
            paired+=1
            if isinstance(r.get("outcome"),(str,bool)) and r.get("outcome")!="":
                typed_outcomes+=1
            team=r.get("team")
            if isinstance(team,dict) and str(team.get("id")) in fixture["teams"].values():
                identified+=1
        groups[name]=dict(records=len(rows),observedKeys=sorted(keys),eventTypes=dict(types),
            explicitMovementEvents=movements,movementsWithStartEnd=paired,
            pairedWithOutcome=typed_outcomes,pairedWithTeam=identified)
    has_pairs=any(g["movementsWithStartEnd"] for g in groups.values())
    return dict(status="coordinate_candidates_unverified" if has_pairs else "movement_coordinates_not_found",
        topLevelKeys=sorted(payload.keys()),collections=groups,
        coordinateScaleVerified=False,attackingDirectionVerified=False,coverageVerified=False,xtComputed=False)

def audit(league,now,reader):
    events=[]
    errors=[]
    for i in range(1,LOOKBACK+1):
        day=(now.date()-timedelta(days=i)).isoformat()
        url=BASE+league+"/scoreboard?dates="+day.replace("-","")
        try:
            events.extend(completed_events(json.loads(reader(url)),league,day))
        except (OSError,ValueError,TypeError,KeyError,AttributeError) as exc:
            errors.append(dict(url=url,error=type(exc).__name__))
    counts=Counter(r["eventId"] for r in events)
    selected=sorted((r for r in events if counts[r["eventId"]]==1),key=lambda r:(r["date"],r["eventId"]),reverse=True)[:PER_LEAGUE]
    rows=[]
    for r in selected:
        url=BASE+league+"/summary?event="+r["eventId"]
        try:
            rows.append(dict(r,source=url,**inspect_events(json.loads(reader(url)),r)))
        except (OSError,ValueError,TypeError,KeyError,AttributeError) as exc:
            rows.append(dict(r,source=url,status="source_error",error=type(exc).__name__))
    return dict(league=league,sampled=len(selected),rows=rows,errors=errors)

def build(now,reader=read):
    now=now.astimezone(TR)
    with ThreadPoolExecutor(max_workers=3) as pool:
        groups=list(pool.map(lambda c:audit(c[0],now,reader),COMPETITIONS))
    rows=[r for g in groups for r in g["rows"]]
    return dict(version="6.51",mode="xt_source_readiness_only",updatedAt=now.isoformat(),
        leagues=groups,sampled=len(rows),statuses=dict(Counter(r["status"] for r in rows)),
        matchesWithCoordinateCandidates=sum(r["status"]=="coordinate_candidates_unverified" for r in rows),
        verifiedXtMatches=0,xtComputed=False,usedForTraining=False,existingArchivesModified=False,
        productionModelValidated=False)

if __name__=="__main__":
    report=build(datetime.now(TR))
    Path("extra_xt_source_audit.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("XT_SOURCE_651",json.dumps(report))
