"""V6.50 source availability audit: never substitute goals or shots for xG."""
import json,math
from datetime import datetime,timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
from extra_league_score_audit import COMPETITIONS,team_key
from results_source_pilot import TR,read

BASE="https://site.api.espn.com/apis/site/v2/sports/soccer/"
LOOKBACK=7
PER_LEAGUE=3
XG_NAMES={"expectedgoals","xg"}

def field_name(s):
    return "".join(c for c in str(s).casefold() if c.isalnum())

def completed_events(payload,league,day):
    if not isinstance(payload.get("events"),list):
        raise ValueError("scoreboard schema")
    out=[]
    for event in payload["events"]:
        try:
            comp,=event["competitions"]
            status=comp.get("status",event.get("status",{}))["type"]
            if status.get("completed") is not True or status.get("name")!="STATUS_FULL_TIME":
                continue
            stamp=datetime.fromisoformat(comp.get("date",event["date"]).replace("Z","+00:00"))
            if stamp.tzinfo is None or stamp.astimezone(TR).date().isoformat()!=day:
                continue
            teams={v["homeAway"]:str(v["team"]["id"]) for v in comp["competitors"]}
            event_id=str(event["id"])
            if len(comp["competitors"])!=2 or set(teams)!={"home","away"} or len(set(teams.values()))!=2 or not event_id.isdigit() or not all(v.isdigit() for v in teams.values()):
                continue
            out.append(dict(league=league,date=day,eventId=event_id,teams=teams))
        except (ValueError,KeyError,TypeError,AttributeError):
            continue
    counts=Counter(r["eventId"] for r in out)
    return [r for r in out if counts[r["eventId"]]==1]

def extract_xg(payload,fixture):
    """Accept explicit provider xG names only, with event and team ID matching."""
    try:
        header=payload["header"]
        if str(header["id"])!=fixture["eventId"]:
            return dict(status="event_mismatch")
        comp,=header["competitions"]
        status=comp["status"]["type"]
        if status.get("completed") is not True or status.get("name")!="STATUS_FULL_TIME":
            return dict(status="not_final")
        teams=payload["boxscore"]["teams"]
        if not isinstance(teams,list) or len(teams)!=2:
            return dict(status="team_schema")
        ids=[str(t["team"]["id"]) for t in teams]
        if len(set(ids))!=2 or set(ids)!=set(fixture["teams"].values()):
            return dict(status="team_mismatch")
        values={}
        observed=set()
        for team in teams:
            tid=str(team["team"]["id"])
            stats=team["statistics"]
            if not isinstance(stats,list):
                return dict(status="stat_schema")
            found=[]
            for stat in stats:
                observed.add(str(stat.get("name","")))
                if field_name(stat.get("name")) not in XG_NAMES:
                    continue
                raw=stat.get("value",stat.get("displayValue"))
                if isinstance(raw,bool):
                    return dict(status="invalid_xg")
                try:
                    v=float(raw)
                except (TypeError,ValueError):
                    return dict(status="invalid_xg")
                if not math.isfinite(v) or v<0:
                    return dict(status="invalid_xg")
                found.append(v)
            if len(found)==1:
                values[tid]=found[0]
            elif len(found)>1:
                return dict(status="duplicate_xg_field")
        if len(values)!=2:
            return dict(status="xg_missing",statNames=sorted(observed))
        h,a=(values[fixture["teams"][side]] for side in ("home","away"))
        return dict(status="provider_xg_pair",homeXg=h,awayXg=a,homeXga=a,awayXga=h,statNames=sorted(observed))
    except (KeyError,ValueError,TypeError,AttributeError):
        return dict(status="summary_schema")

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
            rows.append(dict(r,source=url,**extract_xg(json.loads(reader(url)),r)))
        except (OSError,ValueError,TypeError,KeyError,AttributeError) as exc:
            rows.append(dict(r,source=url,status="source_error",error=type(exc).__name__))
    return dict(league=league,eligibleEvents=len(events),sampled=len(selected),rows=rows,errors=errors)

def build(now,reader=read):
    now=now.astimezone(TR)
    with ThreadPoolExecutor(max_workers=3) as pool:
        groups=list(pool.map(lambda c:audit(c[0],now,reader),COMPETITIONS))
    rows=[r for g in groups for r in g["rows"]]
    return dict(version="6.50",mode="xg_source_availability_only",updatedAt=now.isoformat(),lookbackDays=LOOKBACK,
        maximumSamplePerLeague=PER_LEAGUE,leagues=groups,sampled=len(rows),statuses=dict(Counter(r["status"] for r in rows)),
        providerXgPairs=sum(r["status"]=="provider_xg_pair" for r in rows),independentlyVerifiedXg=0,
        xgaDerivedFromOpponentXg=True,estimatedMissingXg=False,usedForTraining=False,
        productionModelValidated=False,existingArchivesModified=False)

if __name__=="__main__":
    report=build(datetime.now(TR))
    Path("extra_xg_source_audit.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("XG_SOURCE_650",json.dumps(report))
