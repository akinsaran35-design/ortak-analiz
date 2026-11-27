"""V5.47 retrospective goal-model validation; never insert replay results in prospective archive."""
import json
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,date
from pathlib import Path
from backtest import predict,weighted_predict
from prospective_markets import capture,actual,MARKETS,MODELS,summarize
from h2h_history_research import collect
from league_config import LEAGUES
from results_source_pilot import TR,read
from chronological_statistics_research import reliability

def season(d):return d.year-(d.month<7)

def replay(rows):
    dates=defaultdict(list)
    for r in rows:dates[date.fromisoformat(r["date"])].append(r)
    history=[]
    scores=defaultdict(lambda:[0,0.,0.,0.])
    bins=defaultdict(lambda:defaultdict(lambda:[0,0.,0]))
    for day in sorted(dates):
        # Match the existing prospective model's current and preceding season window.
        history=[x for x in history if season(x[0])>=season(day)-1]
        for r in dates[day]:
            h,a=r["home"],r["away"]
            old=predict(history,h,a);new=weighted_predict(history,h,a)
            if old is None or new is None:continue
            p=capture(history,old,new)
            outcomes=actual(*r["score"])
            for market,y in zip(MARKETS,outcomes):
                for model in MODELS:
                    value=p[market][model]
                    for key in ((market,model,None),(market,model,season(day))):
                        v=scores[key];v[0]+=1;v[1]+=(value-y)**2;v[2]+=value;v[3]+=y
                    b=bins[market,model][min(9,int(value*10))]
                    b[0]+=1;b[1]+=value;b[2]+=y
        # All same-day matches remain unavailable until every evaluation for that date ends.
        history.extend((day,r["home"],r["away"],*r["score"]) for r in dates[day])
    def metric(m,k,y):
        n,b,p,a=scores[m,k,y]
        return dict(sample=n,brier=b/n if n else None,meanPrediction=p/n if n else None,observedRate=a/n if n else None)
    return {m:dict(models={k:dict(**metric(m,k,None),reliability=reliability(bins[m,k])) for k in MODELS},seasons=[dict(season=y,models={k:metric(m,k,y) for k in MODELS}) for y in sorted({season(d) for d in dates})]) for m in MARKETS}

def progress(archive,now):
    data=summarize(archive,now)
    pending=defaultdict(int);overdue=0
    for r in archive.values():
        if r["result"] is not None:continue
        d=date.fromisoformat(r["date"])
        if d<now.date():overdue+=1
        else:pending[d.isoformat()]+=1
    return dict(recorded=len(archive),tested=data["2.5 Üst"]["tested"],minimumMatches=500,pendingByDate=dict(sorted(pending.items())),pastPending=overdue,marketResearch=data)

def build(now,archive,reader=read):
    cutoff=now.astimezone(TR).date()
    def group(entry):
        label,code,sport=entry
        rows,sources,errors,invalid=collect(code,sport,cutoff,reader)
        return dict(league=code,leagueName=label,historicalMatches=len(rows),sourceSeasons=len(sources),errors=errors,invalid=invalid,markets=replay(rows))
    with ThreadPoolExecutor(max_workers=6) as pool:groups=list(pool.map(group,LEAGUES))
    return dict(version="5.47",mode="retrospective_goal_model_research_only",updatedAt=now.isoformat(),cutoffExclusive=cutoff.isoformat(),historyScope="current_and_previous_season_at_each_evaluation",source="football-data.co.uk",prospectiveBackfill=False,modelCalibrated=False,predictionsEnabled=False,decision="PAS",prospectiveProgress=progress(archive,now),groups=groups)

if __name__=="__main__":
    archive=json.loads(Path("prospective_archive.json").read_text(encoding="utf-8"))
    r=build(datetime.now(TR),archive)
    Path("historical_goal_validation.json").write_text(json.dumps(r,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in r.items() if k!="groups"},ensure_ascii=False))
    for g in r["groups"]:
        print(json.dumps(dict(league=g["league"],matches=g["historicalMatches"],errors=g["errors"],markets={m:{k:{x:v for x,v in a.items() if x!="reliability"} for k,a in v["models"].items()} for m,v in g["markets"].items()}),ensure_ascii=False))
    if not any(g["markets"]["2.5 Üst"]["models"]["candidate"]["sample"] for g in r["groups"]):raise SystemExit("No historical evaluations")
