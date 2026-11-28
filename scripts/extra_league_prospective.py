"""V6.48 prospective research ledger; no production selection or archive changes."""
import json, math
from datetime import datetime,timedelta
from pathlib import Path
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from extra_league_score_audit import (COMPETITIONS,TR,read,audit_league,team_key,verified_rows,
    MIN_TRAIN_MATCHES,MARKETS,labels,goal_probabilities,dc_probabilities,fit_dc_rho,paired_date_bootstrap)

VERSION="6.48"
START="2026-11-29"
MIN_SETTLED=500
MIN_DATES=30
HORIZON=3
LEDGER=Path("extra_league_prospective_ledger.json")
REPORT=Path("extra_league_prospective_report.json")

def empty_ledger():
    return dict(version=VERSION,forecasts={},settlements={},quarantine={})

def key(r):
    return json.dumps([r["league"],r["date"],r["home"],r["away"]],ensure_ascii=False,separators=(",",":"))

def scheduled_fixtures(payload,league,now):
    if not isinstance(payload.get("events"),list):
        raise ValueError("ESPN fixture schema")
    candidates=[]
    for event in payload["events"]:
        try:
            comp,=event["competitions"]
            status=comp.get("status",event.get("status",{}))["type"]
            if status.get("state")!="pre" or status.get("completed") is not False or status.get("name")!="STATUS_SCHEDULED":
                continue
            stamp=datetime.fromisoformat(comp.get("date",event["date"]).replace("Z","+00:00"))
            if stamp.tzinfo is None:
                continue
            day=stamp.astimezone(TR).date().isoformat()
            if day<START or not now.date()<stamp.astimezone(TR).date()<=now.date()+timedelta(days=HORIZON):
                continue
            teams={x["homeAway"]:x["team"]["displayName"] for x in comp["competitors"]}
            if len(comp["competitors"])!=2 or set(teams)!={"home","away"}:
                continue
            h,a=(team_key(league,teams[k]) for k in ("home","away"))
            event_id=str(event["id"])
            if not h or not a or h==a or not event_id.isdigit():
                continue
            candidates.append(dict(league=league,date=day,home=h,away=a,eventId=event_id,kickoff=stamp.isoformat()))
        except (KeyError,ValueError,TypeError,AttributeError):
            continue
    counts=Counter(key(r) for r in candidates)
    ids=Counter(r["eventId"] for r in candidates)
    return [r for r in candidates if counts[key(r)]==1 and ids[r["eventId"]]==1]

def capture(ledger,rows,fixtures,now):
    now=now.astimezone(TR)
    past={}
    for r in verified_rows(rows):
        if r["date"]<now.date().isoformat():
            past.setdefault(r["league"],[]).append(r)
    existing_ids={(r["league"],r["eventId"]) for r in ledger["forecasts"].values()}
    new=0
    counts=Counter(key(r) for r in fixtures)
    ids=Counter((r["league"],r["eventId"]) for r in fixtures)
    for r in sorted(fixtures,key=key):
        k=key(r)
        identity=(r["league"],r["eventId"])
        stamp=datetime.fromisoformat(r["kickoff"])
        if counts[k]!=1 or ids[identity]!=1 or k in ledger["forecasts"] or identity in existing_ids:
            continue
        if stamp.tzinfo is None or stamp<=now or stamp.astimezone(TR).date().isoformat()!=r["date"] or not now.date().isoformat()<r["date"] or r["date"]<START or stamp.astimezone(TR).date()>now.date()+timedelta(days=HORIZON):
            continue
        history=past.get(r["league"],[])
        n=len(history)
        if n<MIN_TRAIN_MATCHES:
            continue
        scores=[v["csv"] for v in history]
        h=sum(s[0] for s in scores)/n
        a=sum(s[1] for s in scores)/n
        base=goal_probabilities(h,a)
        dc=dc_probabilities(h,a,fit_dc_rho(scores,h,a))
        candidate=tuple(0.4*p+0.6*q for p,q in zip(base,dc))
        ledger["forecasts"][k]=dict(r,recordedAt=now.isoformat(),trainingThrough=max(v["date"] for v in history),
            trainingMatches=n,policyVersion=VERSION,poisson=dict(zip(MARKETS,base)),candidate=dict(zip(MARKETS,candidate)))
        existing_ids.add(identity)
        new+=1
    return new

def settle(ledger,rows,now):
    now=now.astimezone(TR)
    evidence={}
    for r in rows:
        evidence.setdefault(key(r),[]).append(r)
    confirmed={key(r):r["csv"] for r in verified_rows(rows)}
    n=0
    for k,r in ledger["forecasts"].items():
        if r["date"]>=now.date().isoformat() or k in ledger["quarantine"]:
            continue
        score=confirmed.get(k)
        prior=ledger["settlements"].get(k)
        conflict=any(v.get("status")=="conflict" for v in evidence.get(k,[])) or len(evidence.get(k,[]))>1
        if conflict or (prior and score is not None and prior["score"]!=score):
            ledger["quarantine"][k]=dict(reason="source_conflict_or_duplicate",detectedAt=now.isoformat())
        elif prior is None and score is not None:
            ledger["settlements"][k]=dict(score=score,settledAt=now.isoformat(),sources=["football-data","espn"])
            n+=1
    return n

def summarize(ledger):
    valid=[(r,ledger["settlements"][k]["score"]) for k,r in ledger["forecasts"].items()
        if k in ledger["settlements"] and k not in ledger["quarantine"]]
    n=len(valid)
    dates=len({r["date"] for r,_ in valid})
    markets={}
    for i,m in enumerate(MARKETS):
        paired=[(r["date"],r["poisson"][m],r["candidate"][m],labels(*s)[i]) for r,s in valid]
        by_day={}
        for d,p,q,y in paired:
            by_day.setdefault(d,[]).append((p-y)**2-(q-y)**2)
        def metric(j):
            return dict(brier=round(sum((r[j]-r[3])**2 for r in paired)/n,6) if n else None,
                accuracyPct=round(100*sum((r[j]>=0.5)==bool(r[3]) for r in paired)/n,2) if n else None)
        markets[m]=dict(poisson=metric(1),candidate=metric(2),pairedBootstrap=paired_date_bootstrap(by_day))
    return dict(version=VERSION,mode="prospective_research_only",protocolStart=START,
        fixedWeights={"poisson":0.4,"dixonColes":0.6},recorded=len(ledger["forecasts"]),
        settled=n,pending=sum(k not in ledger["settlements"] and k not in ledger["quarantine"] for k in ledger["forecasts"]),
        quarantined=len(ledger["quarantine"]),dateBlocks=dates,minSettled=MIN_SETTLED,minDateBlocks=MIN_DATES,
        sampleTargetReached=n>=MIN_SETTLED and dates>=MIN_DATES,markets=markets,
        automaticApproval=False,productionModelValidated=False,decision="PAS")

def run():
    started=datetime.now(TR)
    with ThreadPoolExecutor(max_workers=3) as pool:
        audits=list(pool.map(lambda x:audit_league(*x,started),COMPETITIONS))
    rows=[dict(r,league=g["league"]) for g in audits for r in g["rows"]]
    eligible={g["league"] for g in audits if not g["errors"]}
    fixtures=[]
    errors=[dict(league=g["league"],errors=g["errors"]) for g in audits if g["errors"]]
    for league,_ in COMPETITIONS:
        if league not in eligible:
            continue
        for i in range(1,HORIZON+1):
            day=(started.date()+timedelta(days=i)).strftime("%Y%m%d")
            url=f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league}/scoreboard?dates={day}"
            try:
                fixtures.extend(scheduled_fixtures(json.loads(read(url)),league,started))
            except (OSError,ValueError,TypeError,KeyError,AttributeError) as exc:
                errors.append(dict(league=league,date=day,error=type(exc).__name__))
    now=datetime.now(TR)
    ledger=json.loads(LEDGER.read_text()) if LEDGER.exists() else empty_ledger()
    if ledger["version"]!=VERSION or any(not isinstance(ledger[k],dict) for k in ("forecasts","settlements","quarantine")):
        raise ValueError("invalid ledger schema; refuse replacement")
    settled=settle(ledger,rows,now)
    new=capture(ledger,[r for r in rows if r["league"] in eligible],fixtures,now)
    report=dict(summarize(ledger),newForecasts=new,newSettlements=settled,sourceErrors=errors,updatedAt=now.isoformat())
    LEDGER.write_text(json.dumps(ledger,ensure_ascii=False,indent=2,sort_keys=True)+"\n")
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    print("PROSPECTIVE_648",json.dumps(report))

if __name__=="__main__":
    run()
