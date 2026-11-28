"""V6.52 historical feature availability research, no fitted model or production predictions."""
import json
from collections import Counter,defaultdict
from datetime import date,datetime
from pathlib import Path
from extra_league_training_inventory import build,deduplicate
from results_source_pilot import TR

METRICS=("goals","shots","shotsOnTarget","corners")
WINDOWS=(5,10)
MIN_TEAM=5

def summarize(history,side,day):
    result={}
    for window in WINDOWS:
        recent=history[-window:]
        prefix=f"{side}_last{window}"
        result[prefix+"_matches"]=len(recent)
        result[prefix+"_points"]=sum(r["points"] for r in recent)/len(recent) if recent else None
        for metric in METRICS:
            present=[r[metric] for r in recent if metric in r]
            for j,direction in enumerate(("for","against")):
                result[f"{prefix}_{metric}_{direction}"]=sum(p[j] for p in present)/len(present) if present else None
            result[f"{prefix}_{metric}_sample"]=len(present)
    result[side+"_restDays"]=(date.fromisoformat(day)-date.fromisoformat(history[-1]["date"])).days if history else None
    return result

def feature_rows(rows):
    unique,_,_=deduplicate(rows)
    groups=defaultdict(list)
    for r in unique:
        if r.get("verification")=="single_source_only":
            groups[r["date"]].append(r)
    history=defaultdict(list)
    venue=defaultdict(list)
    league=defaultdict(list)
    output=[]
    for day,group in sorted(groups.items()):
        for r in group:
            l,h,a=r["league"],r["home"],r["away"]
            hs,aw=history[(l,h)],history[(l,a)]
            if min(len(hs),len(aw))<MIN_TEAM:
                continue
            features={}
            features.update(summarize(hs,"home",day))
            features.update(summarize(aw,"away",day))
            features.update(summarize(venue[(l,h,"home")],"homeVenue",day))
            features.update(summarize(venue[(l,a,"away")],"awayVenue",day))
            past=league[l]
            features["leagueHomeGoals"]=sum(x[0] for x in past)/len(past)
            features["leagueAwayGoals"]=sum(x[1] for x in past)/len(past)
            features["leagueMatches"]=len(past)
            x,y=r["score"]
            output.append(dict(league=l,date=day,home=h,away=a,features=features,
                labels=dict(over15=int(x+y>=2),over25=int(x+y>=3),btts=int(x>0 and y>0)),
                verification="single_source_only",source=r["source"]))
        # Update only after every fixture on this date has been processed.
        for r in group:
            l=r["league"]
            x,y=r["score"]
            league[l].append((x,y))
            for j,side in enumerate(("home","away")):
                gf,ga=r["score"][j],r["score"][1-j]
                record=dict(date=day,goals=(gf,ga),points=3 if gf>ga else 1 if gf==ga else 0)
                for metric,values in r.get("stats",{}).items():
                    if metric in METRICS[1:]:
                        record[metric]=(values[j],values[1-j])
                history[(l,r[side])].append(record)
                venue[(l,r[side],side)].append(record)
    return output

def report(rows,inventory):
    features=feature_rows(rows)
    n=len(features)
    present=Counter(k for r in features for k,v in r["features"].items() if v is not None)
    keys=sorted({k for r in features for k in r["features"]})
    result=dict(version="6.52",mode="single_source_feature_research",inputMatches=len(rows),
        eligibleFeatureRows=n,featureCount=len(keys),leagueCounts=dict(Counter(r["league"] for r in features)),
        featureCoverage={k:round(100*present[k]/n,2) for k in keys} if n else {},
        minTeamMatches=MIN_TEAM,windows=list(WINDOWS),sourceSuccessful=inventory["successfulSources"],
        sameDayTraining=False,independentlyVerified=0,xgIncluded=False,xtIncluded=False,
        missingValuesEstimated=False,usedForTraining=False,productionModelValidated=False,existingArchivesModified=False)
    return result,features

if __name__=="__main__":
    inventory,rows=build()
    result,features=report(rows,inventory)
    result["updatedAt"]=datetime.now(TR).isoformat()
    Path("extra_feature_report.json").write_text(json.dumps(result,indent=2)+"\n")
    Path("extra_feature_candidates.json").write_text(json.dumps(features,ensure_ascii=False)+"\n")
    print("FEATURE_RESEARCH_652",json.dumps(result))
    if not features:
        raise SystemExit("no historical features")
