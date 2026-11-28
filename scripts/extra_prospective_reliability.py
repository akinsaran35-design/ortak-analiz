"""V6.56 read-only integrity and reliability diagnostics for the frozen V6.48 cohort."""
import json,math
from collections import Counter,defaultdict
from datetime import datetime,date
from pathlib import Path
from extra_league_prospective import VERSION,START,MIN_SETTLED,MIN_DATES,LEDGER,key
from extra_league_score_audit import MARKETS,labels,MIN_TRAIN_MATCHES,COMPETITIONS
from results_source_pilot import TR

MIN_BIN=30
LEAGUES={c[0] for c in COMPETITIONS}

def aware(value):
    t=datetime.fromisoformat(value)
    if t.tzinfo is None or t.utcoffset() is None:
        raise ValueError("naive timestamp")
    return t.astimezone(TR)

def probabilities(p):
    return isinstance(p,dict) and set(p)==set(MARKETS) and all(type(x) in (int,float) and math.isfinite(x) and 0<=x<=1 for x in p.values()) and p["over15"]+1e-10>=max(p["over25"],p["btts"])

def forecast_valid(k,r,now):
    try:
        capture=aware(r["recordedAt"])
        kickoff=aware(r["kickoff"])
        training=date.fromisoformat(r["trainingThrough"])
        fixture=date.fromisoformat(r["date"])
        return (r["policyVersion"]==VERSION and k==key(r) and r["league"] in LEAGUES
            and isinstance(r["home"],str) and isinstance(r["away"],str) and bool(r["home"]) and bool(r["away"]) and r["home"]!=r["away"]
            and isinstance(r["eventId"],str) and r["eventId"].isdigit()
            and fixture>=date.fromisoformat(START) and kickoff.date()==fixture
            and capture<=now and training<capture.date()<fixture and capture<kickoff
            and type(r["trainingMatches"]) is int and r["trainingMatches"]>=MIN_TRAIN_MATCHES
            and probabilities(r["poisson"]) and probabilities(r["candidate"]))
    except (KeyError,TypeError,ValueError,AttributeError,OverflowError):
        return False

def settlement_valid(r,s,now):
    try:
        t=aware(s["settledAt"])
        score=s["score"]
        return (aware(r["kickoff"])<t<=now and t.date()>date.fromisoformat(r["date"])
            and sorted(s["sources"])==["espn","football-data"]
            and isinstance(score,list) and len(score)==2 and all(type(x) is int and x>=0 for x in score))
    except (KeyError,TypeError,ValueError,AttributeError,OverflowError):
        return False

def reliability(pairs):
    n=len(pairs)
    bins=[[] for _ in range(10)]
    for p,y in pairs:
        bins[min(9,int(p*10))].append((p,y))
    output=[]
    for i,g in enumerate(bins):
        count=len(g)
        output.append(dict(bin=i,n=count,meanProbability=sum(p for p,y in g)/count if count else None,
            observedFrequency=sum(y for p,y in g)/count if count else None,
            descriptiveSampleAdequate=count>=MIN_BIN))
    if not n:
        return dict(n=0,brier=None,logLoss=None,meanProbability=None,observedFrequency=None,ece10=None,bins=output)
    return dict(n=n,brier=sum((p-y)**2 for p,y in pairs)/n,
        logLoss=-sum(y*math.log(max(p,1e-12))+(1-y)*math.log(max(1-p,1e-12)) for p,y in pairs)/n,
        meanProbability=sum(p for p,y in pairs)/n,observedFrequency=sum(y for p,y in pairs)/n,
        ece10=sum(abs(sum(p-y for p,y in g)) for g in bins)/n,bins=output)

def audit(ledger,now):
    now=now.astimezone(TR)
    if ledger.get("version")!=VERSION or any(not isinstance(ledger.get(k),dict) for k in ("forecasts","settlements","quarantine")):
        raise ValueError("unsupported ledger schema")
    forecasts,settlements,quarantine=(ledger[k] for k in ("forecasts","settlements","quarantine"))
    counts=Counter((r.get("league"),r.get("eventId")) for r in forecasts.values() if isinstance(r,dict))
    errors=Counter()
    errors["orphanSettlements"]=len(set(settlements)-set(forecasts))
    errors["orphanQuarantine"]=len(set(quarantine)-set(forecasts))
    valid=[]
    pending=0
    for k,r in forecasts.items():
        if not forecast_valid(k,r,now):
            errors["invalidForecast"]+=1
            continue
        if counts[(r["league"],r["eventId"]) ]!=1:
            errors["duplicateEventIdentity"]+=1
            continue
        if k in settlements and not settlement_valid(r,settlements[k],now):
            errors["invalidSettlement"]+=1
            continue
        if k in quarantine:
            continue
        if k not in settlements:
            pending+=1
            continue
        valid.append((r,settlements[k]["score"]))
    dates=len({r["date"] for r,_ in valid})
    integrity=sum(errors.values())==0
    markets={}
    for i,m in enumerate(MARKETS):
        markets[m]={name:reliability([(r[name][m],labels(*s)[i]) for r,s in valid])
            for name in ("poisson","candidate")}
    return dict(version="6.56",cohortVersion=VERSION,mode="read_only_prospective_reliability",
        recorded=len(forecasts),validSettled=len(valid),validPending=pending,quarantined=len(quarantine),
        dateBlocks=dates,integrityPassed=integrity,errors=dict(errors),
        minimumSettled=MIN_SETTLED,minimumDates=MIN_DATES,minimumBinSample=MIN_BIN,
        sampleTargetReached=integrity and len(valid)>=MIN_SETTLED and dates>=MIN_DATES,
        markets=markets,status="integrity_failure" if not integrity else "descriptive_sample_target_reached" if len(valid)>=MIN_SETTLED and dates>=MIN_DATES else "collecting_data",
        automaticApproval=False,productionModelValidated=False,existingArchivesModified=False)

if __name__=="__main__":
    ledger=json.loads(LEDGER.read_text(encoding="utf-8"))
    report=audit(ledger,datetime.now(TR))
    Path("extra_prospective_reliability.json").write_text(json.dumps(report,indent=2)+"\n")
    print("PROSPECTIVE_RELIABILITY_656",json.dumps({k:v for k,v in report.items() if k!="markets"}))
    if not report["integrityPassed"]:
        raise SystemExit("ledger integrity check failed")
