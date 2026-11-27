"""V5.33 chronological descriptive baseline validation; never publishes selections."""
import json
from collections import defaultdict,deque
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from h2h_history_research import collect
from league_config import LEAGUES
from results_source_pilot import TR,read
from historical_metric_coverage import valid_pair

EVENTS=("firstHalfGoal","secondHalfGoal","bothHalvesScoreBothTeams","totalCornersAtLeast10","totalYellowCardsAtLeast5")
MIN_LEAGUE=100
MIN_VENUE=5
SHRINK=10

def observations(row):
    s=row["score"];m=row["stats"];out={}
    h=m.get("halfTimeGoals")
    if valid_pair(s) and valid_pair(h) and all(a<=b for a,b in zip(h,s)):
        second=[b-a for a,b in zip(h,s)]
        out.update(firstHalfGoal=int(sum(h)>0),secondHalfGoal=int(sum(second)>0),bothHalvesScoreBothTeams=int(min(*h,*second)>0))
    for name,key,threshold in (("totalCornersAtLeast10","corners",10),("totalYellowCardsAtLeast5","yellowCards",5)):
        p=m.get(key)
        if valid_pair(p):out[name]=int(sum(p)>=threshold)
    return out

def replay(rows):
    league=defaultdict(lambda:[0,0])
    venues=defaultdict(lambda:deque(maxlen=20))
    scores=defaultdict(lambda:[0,0.,0.,0])
    dates=defaultdict(list)
    for row in rows:dates[row["date"]].append(row)
    for day in sorted(dates):
        updates=[]
        for r in dates[day]:
            for name,y in observations(r).items():
                n,k=league[name];h=venues[name,"home",r["home"]];a=venues[name,"away",r["away"]]
                if n>=MIN_LEAGUE and len(h)>=MIN_VENUE and len(a)>=MIN_VENUE:
                    p=(k+1)/(n+2)
                    q=((sum(h)+SHRINK*p)/(len(h)+SHRINK)+(sum(a)+SHRINK*p)/(len(a)+SHRINK))/2
                    x=scores[name];x[0]+=1;x[1]+=(p-y)**2;x[2]+=(q-y)**2;x[3]+=y
                updates.append((name,r["home"],r["away"],y))
        # Outcomes on the same date never enter any earlier prediction.
        for name,h,a,y in updates:
            league[name][0]+=1;league[name][1]+=y
            venues[name,"home",h].append(y);venues[name,"away",a].append(y)
    result={}
    for name in EVENTS:
        n,b,c,k=scores[name]
        result[name]=dict(sample=n,observedEvents=k,leagueBrier=b/n if n else None,venueBrier=c/n if n else None,availableHistoricalRows=league[name][0])
    return result

def build(now,reader=read):
    cutoff=now.astimezone(TR).date()
    def group(entry):
        label,code,sport=entry
        rows,sources,errors,invalid=collect(code,sport,cutoff,reader)
        return dict(league=code,leagueName=label,sourceSeasons=len(sources),sourceErrors=errors,invalid=invalid,matches=len(rows),metrics=replay(rows))
    with ThreadPoolExecutor(max_workers=6) as pool:groups=list(pool.map(group,LEAGUES))
    return dict(version="5.33",mode="chronological_research_only",updatedAt=now.isoformat(),cutoffExclusive=cutoff.isoformat(),modelCalibrated=False,predictionsEnabled=False,decision="PAS",groups=groups)

if __name__=="__main__":
    r=build(datetime.now(TR))
    Path("chronological_statistics_research.json").write_text(json.dumps(r,ensure_ascii=False,indent=2)+"\n")
    for g in r["groups"]:
        print(json.dumps(dict(league=g["league"],matches=g["matches"],metrics=g["metrics"],sourceErrors=g["sourceErrors"]),ensure_ascii=False))
    if not any(g["matches"] for g in r["groups"]):raise SystemExit("No historical source data")
