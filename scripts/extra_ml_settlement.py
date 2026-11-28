"""V6.60 independent two-source score settlement for the frozen ML research cohort."""
import csv,io,json,math
from collections import Counter,defaultdict
from datetime import datetime,date,timedelta
from pathlib import Path
from extra_ml_prospective import LEDGER,META,VERSION,WEIGHT,read_json,write_json
from extra_league_score_audit import COMPETITIONS,MARKETS,team_key,labels,paired_date_bootstrap
from extra_league_prospective import key,MIN_SETTLED,MIN_DATES
from extra_prospective_reliability import aware,probabilities,reliability
from results_source_pilot import TR,read,score

CODES=dict(COMPETITIONS)
MODELS=("poisson","catboost","candidate")
RECHECK_DAYS=14

def csv_evidence(raw,league,identity_fn=team_key):
    reader=csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    if not {"Date","HomeTeam","AwayTeam","FTHG","FTAG"}.issubset(reader.fieldnames or []):
        raise ValueError("CSV schema")
    out=defaultdict(list)
    for r in reader:
        day=None
        for fmt in ("%d/%m/%Y","%d/%m/%y"):
            try:
                day=datetime.strptime(r["Date"],fmt).date().isoformat()
                break
            except (TypeError,ValueError):
                pass
        if not day or not r["HomeTeam"] or not r["AwayTeam"]:
            continue
        k=(day,identity_fn(league,r["HomeTeam"]),identity_fn(league,r["AwayTeam"]))
        try:
            result=score(r["FTHG"],r["FTAG"])
        except ValueError:
            result=None
        out[k].append(result)
    return out

def espn_evidence(payload,fixture,identity_fn=team_key):
    if not isinstance(payload.get("events"),list):
        raise ValueError("ESPN schema")
    events=[e for e in payload["events"] if isinstance(e,dict) and str(e.get("id"))==fixture["eventId"]]
    if len(events)>1:
        return None,"duplicate_event"
    if not events:
        return None,None
    try:
        e=events[0]
        comp,=e["competitions"]
        status=comp.get("status",e.get("status",{}))["type"]
        if status.get("completed") is not True or status.get("name")!="STATUS_FULL_TIME":
            return None,None
        t=aware(comp.get("date",e["date"]).replace("Z","+00:00"))
        teams={x["homeAway"]:x for x in comp["competitors"]}
        if len(comp["competitors"])!=2 or set(teams)!={"home","away"}:
            return None,"event_identity_mismatch"
        h,a=teams["home"],teams["away"]
        if (t.date().isoformat()!=fixture["date"] or t<=aware(fixture["recordedAt"])
            or identity_fn(fixture["league"],h["team"]["displayName"])!=fixture["home"]
            or identity_fn(fixture["league"],a["team"]["displayName"])!=fixture["away"]):
            return None,"event_identity_mismatch"
        return score(h["score"],a["score"]),None
    except (KeyError,TypeError,ValueError,AttributeError):
        return None,"malformed_final_event"

def validate(ledger,meta,now,version=VERSION,codes=CODES):
    if ledger.get("version")!=version or ledger.get("modelSha256")!=meta["modelSha256"] or any(not isinstance(ledger.get(k),dict) for k in ("forecasts","settlements","quarantine")):
        raise ValueError("cohort mismatch")
    f=ledger["forecasts"]
    if set(ledger["settlements"])-set(f) or set(ledger["quarantine"])-set(f):
        raise ValueError("orphan evidence")
    seen=set()
    for k,r in f.items():
        ident=(r["league"],r["eventId"])
        if (k!=key(r) or ident in seen or r["league"] not in codes or r["policyVersion"]!=version
            or r["modelSha256"]!=meta["modelSha256"] or not aware(meta["frozenAt"])<=aware(r["recordedAt"])<=now
            or not aware(r["recordedAt"]).date()<aware(r["kickoff"]).date()
            or aware(r["kickoff"]).date().isoformat()!=r["date"]
            or not r["historyThrough"]<aware(r["recordedAt"]).date().isoformat()
            or not all(probabilities(r[m]) for m in MODELS)
            or any(abs(r["candidate"][m]-(1-WEIGHT)*r["poisson"][m]-WEIGHT*r["catboost"][m])>1e-10 for m in MARKETS)):
            raise ValueError("invalid frozen forecast")
        seen.add(ident)
        if k in ledger["settlements"]:
            s=ledger["settlements"][k]
            if (s["eventId"]!=r["eventId"] or sorted(s["sources"])!=["espn","football-data"]
                or not isinstance(s["score"],list) or len(s["score"])!=2 or any(type(x) is not int or x<0 for x in s["score"])
                or not aware(r["kickoff"])<aware(s["settledAt"])<=now or aware(s["settledAt"]).date()<=date.fromisoformat(r["date"])):
                raise ValueError("invalid stored settlement")

def settle(ledger,meta,now,reader=read,version=VERSION,codes=CODES,identity_fn=team_key,espn_codes=None,diagnostics=None):
    now=now.astimezone(TR)
    validate(ledger,meta,now,version=version,codes=codes)
    cutoff=now.date()-timedelta(days=RECHECK_DAYS)
    primary={}
    secondary={}
    errors=[]
    added=0
    counts=Counter()
    by_league=defaultdict(Counter)
    def note(f,reason):
        counts[reason]+=1
        by_league[f["league"]][reason]+=1
    def parse_espn(raw):
        payload=json.loads(raw)
        if not isinstance(payload,dict) or not isinstance(payload.get("events"),list):
            raise ValueError("ESPN schema")
        return payload
    for k,f in sorted(ledger["forecasts"].items()):
        d=date.fromisoformat(f["date"])
        if k in ledger["quarantine"]:
            note(f,"already_quarantined");continue
        if d>=now.date():
            note(f,"not_yet_eligible");continue
        if k in ledger["settlements"] and d<cutoff:
            note(f,"outside_recheck_window");continue
        l=f["league"]
        year=d.year if d.month>=7 else d.year-1
        cu=f"https://football-data.co.uk/mmz4281/{year%100:02d}{(year+1)%100:02d}/{codes[l]}.csv"
        eu=f"https://site.api.espn.com/apis/site/v2/sports/soccer/{espn_codes[l] if espn_codes is not None else l}/scoreboard?dates={d:%Y%m%d}"
        for cache,url,parse in ((primary,cu,lambda raw:csv_evidence(raw,l,identity_fn)),(secondary,eu,parse_espn)):
            if url not in cache:
                try:
                    cache[url]=parse(reader(url))
                except (OSError,ValueError,TypeError,KeyError,AttributeError) as exc:
                    cache[url]=None
                    errors.append(dict(league=l,date=f["date"],source="football-data" if cache is primary else "espn",error=type(exc).__name__))
        csv_unavailable=primary[cu] is None
        espn_unavailable=secondary[eu] is None
        entries=[] if csv_unavailable else primary[cu].get((f["date"],f["home"],f["away"]),[])
        b,reason=(None,None) if espn_unavailable else espn_evidence(secondary[eu],f,identity_fn)
        a=entries[0] if len(entries)==1 else None
        prior=ledger["settlements"].get(k)
        if len(entries)>1:
            reason="duplicate_csv_identity"
        if a is not None and b is not None and a!=b:
            reason="source_score_conflict"
        if prior and any(v is not None and v!=prior["score"] for v in (a,b)):
            reason="settled_score_changed"
        if reason:
            note(f,reason)
            ledger["quarantine"][k]=dict(reason=reason,detectedAt=now.isoformat())
        elif csv_unavailable or espn_unavailable:
            prefix="previously_verified_" if prior else ""
            note(f,prefix+("both_sources_unavailable" if csv_unavailable and espn_unavailable else "csv_source_unavailable" if csv_unavailable else "espn_source_unavailable"))
        elif not prior and a is not None and a==b:
            ledger["settlements"][k]=dict(score=a,eventId=f["eventId"],settledAt=now.isoformat(),
                sources=["football-data","espn"],sourceUrls=[cu,eu])
            added+=1
            note(f,"newly_verified")
        elif prior and a is not None and a==b:
            note(f,"previously_verified_rechecked")
        else:
            prefix="previously_verified_" if prior else ""
            note(f,prefix+("both_scores_missing" if a is None and b is None else "csv_score_missing" if a is None else "espn_final_score_missing"))
    if diagnostics is not None:
        diagnostics.update(counts=dict(counts),byLeague={k:dict(v) for k,v in sorted(by_league.items())},
            classifiedFixtures=sum(counts.values()),uniqueCSVRequests=len(primary),uniqueESPNRequests=len(secondary),
            missingScoreDoesNotProveDelayCause=True)
    validate(ledger,meta,now,version=version,codes=codes)
    return added,errors

def summarize(ledger,version=VERSION):
    valid=[(r,ledger["settlements"][k]["score"]) for k,r in ledger["forecasts"].items() if k in ledger["settlements"] and k not in ledger["quarantine"]]
    n=len(valid)
    days=len({r["date"] for r,_ in valid})
    markets={}
    for i,m in enumerate(MARKETS):
        pairs=[(r,labels(*s)[i]) for r,s in valid]
        metrics={}
        for name in MODELS:
            v=reliability([(r[name][m],y) for r,y in pairs])
            v["accuracyPct"]=100*sum((r[name][m]>=.5)==bool(y) for r,y in pairs)/n if n else None
            metrics[name]=v
        blocks=defaultdict(list)
        for r,y in pairs:
            blocks[r["date"]].append((r["poisson"][m]-y)**2-(r["candidate"][m]-y)**2)
        markets[m]=dict(models=metrics,pairedBootstrap=paired_date_bootstrap(blocks))
    return dict(version="6.60",cohortVersion=version,mode="prospective_research_only",
        recorded=len(ledger["forecasts"]),validSettled=n,quarantined=len(ledger["quarantine"]),
        pending=sum(k not in ledger["settlements"] and k not in ledger["quarantine"] for k in ledger["forecasts"]),
        dateBlocks=days,minimumSettled=MIN_SETTLED,minimumDates=MIN_DATES,
        sampleTargetReached=n>=MIN_SETTLED and days>=MIN_DATES,
        markets=markets,automaticApproval=False,productionModelValidated=False,existingOtherArchivesModified=False)

if __name__=="__main__":
    ledger=read_json(LEDGER)
    now=datetime.now(TR)
    added,errors=settle(ledger,read_json(META),now)
    report=dict(summarize(ledger),newSettlements=added,sourceErrors=errors,updatedAt=now.isoformat())
    write_json(LEDGER,ledger)
    write_json(Path("extra_ml_settlement_report.json"),report)
    print("ML_SETTLEMENT_660",json.dumps({k:v for k,v in report.items() if k!="markets"}))
