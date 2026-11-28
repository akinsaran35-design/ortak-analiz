"""V6.58 prospective ML input preflight; no forecasts, fitting or ledger writes."""
import json,hashlib
from collections import Counter
from datetime import datetime,date,timedelta
from pathlib import Path
from extra_league_training_inventory import build,deduplicate
from extra_league_features import summarize,METRICS,MIN_TEAM,feature_rows
from extra_league_prospective import scheduled_fixtures,key,HORIZON
from extra_league_score_audit import COMPETITIONS,team_key
from results_source_pilot import TR,read

MAX_TEAM_AGE=45

def input_features(history,fixture,now):
    now=now.astimezone(TR)
    day=fixture["date"]
    kickoff=datetime.fromisoformat(fixture["kickoff"])
    if kickoff.tzinfo is None or kickoff.astimezone(TR).date().isoformat()!=day or kickoff<=now or not now.date().isoformat()<day:
        return None,"not_future"
    l=fixture["league"]
    past=[r for r in history if r["league"]==l and r["date"]<now.date().isoformat() and r.get("verification")=="single_source_only"]
    past,_,_=deduplicate(past)
    names={r[s] for r in past for s in ("home","away")}
    mapped=[]
    for s in ("home","away"):
        matches={n for n in names if team_key(l,n)==fixture[s]}
        if len(matches)!=1:
            return None,"unmatched_or_ambiguous_identity"
        mapped.append(next(iter(matches)))
    if len(set(mapped))!=2:
        return None,"ambiguous_identity"
    features={}
    last=[]
    for side,name in zip(("home","away"),mapped):
        games=[]
        venue=[]
        for r in past:
            if name not in (r["home"],r["away"]):
                continue
            j=0 if r["home"]==name else 1
            gf,ga=r["score"][j],r["score"][1-j]
            rec=dict(date=r["date"],goals=(gf,ga),points=3 if gf>ga else 1 if gf==ga else 0)
            for metric,values in r.get("stats",{}).items():
                if metric in METRICS[1:]:
                    rec[metric]=(values[j],values[1-j])
            games.append(rec)
            if j==(0 if side=="home" else 1):
                venue.append(rec)
        if len(games)<MIN_TEAM:
            return None,"insufficient_team_history"
        if (now.date()-date.fromisoformat(games[-1]["date"])).days>MAX_TEAM_AGE:
            return None,"stale_team_history"
        last.append(games[-1]["date"])
        features.update(summarize(games,side,day))
        features.update(summarize(venue,side+"Venue",day))
    features.update(leagueHomeGoals=sum(r["score"][0] for r in past)/len(past),
        leagueAwayGoals=sum(r["score"][1] for r in past)/len(past),leagueMatches=len(past))
    return dict(features=features,teamHistoryThrough=last,historyThrough=max(r["date"] for r in past)),None

def preflight(history,fixtures,now,expected_keys):
    entries=[]
    excluded=Counter()
    identities=Counter((r["league"],r["eventId"]) for r in fixtures)
    keys=Counter(key(r) for r in fixtures)
    for f in sorted(fixtures,key=key):
        if identities[(f["league"],f["eventId"])]!=1 or keys[key(f)]!=1:
            excluded["duplicate_fixture"]+=1
            continue
        r,reason=input_features(history,f,now)
        if reason:
            excluded[reason]+=1
            continue
        if set(r["features"])!=expected_keys:
            excluded["feature_schema_mismatch"]+=1
            continue
        canonical=json.dumps(r["features"],sort_keys=True,separators=(",",":"),allow_nan=False)
        entries.append(dict(f,featureCount=len(expected_keys),featureFingerprint=hashlib.sha256(canonical.encode()).hexdigest(),
            historyThrough=r["historyThrough"],teamHistoryThrough=r["teamHistoryThrough"],missingFeatures=sum(v is None for v in r["features"].values())))
    return dict(version="6.58",mode="prospective_ml_input_preflight",fixturesChecked=len(fixtures),
        eligibleFixtures=len(entries),excluded=dict(excluded),featureCount=len(expected_keys),
        historyCutoffExclusive=now.astimezone(TR).date().isoformat(),maxTeamHistoryAgeDays=MAX_TEAM_AGE,
        entries=entries,trainingSourceVerification="single_source_only",modelFitted=False,
        forecastsRecorded=0,productionModelValidated=False,existingArchivesModified=False)

def run():
    now=datetime.now(TR)
    inventory,history=build(end=now.date())
    if inventory["successfulSources"]!=inventory["requestedSources"]:
        raise SystemExit("incomplete source inventory")
    historical=feature_rows([r for r in history if r["date"]<"2024-07-01"])
    if not historical:
        raise SystemExit("no training feature schema")
    expected=set(historical[0]["features"])
    fixtures=[]
    errors=[]
    for l,_ in COMPETITIONS:
        for i in range(1,HORIZON+1):
            day=(now.date()+timedelta(days=i)).strftime("%Y%m%d")
            url=f"https://site.api.espn.com/apis/site/v2/sports/soccer/{l}/scoreboard?dates={day}"
            try:
                fixtures.extend(scheduled_fixtures(json.loads(read(url)),l,now))
            except (OSError,ValueError,TypeError,KeyError,AttributeError) as exc:
                errors.append(dict(league=l,date=day,error=type(exc).__name__))
    result=preflight(history,fixtures,now,expected)
    result.update(sourceErrors=errors,historyMatches=len(history),sourceSuccessful=inventory["successfulSources"],
        updatedAt=now.isoformat())
    Path("extra_ml_preflight.json").write_text(json.dumps(result,indent=2)+"\n")
    print("ML_PREFLIGHT_658",json.dumps({k:v for k,v in result.items() if k!="entries"}))
    if errors:
        raise SystemExit("fixture source errors")
if __name__=="__main__":
    run()
