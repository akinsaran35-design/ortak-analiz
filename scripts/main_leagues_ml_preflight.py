"""V6.66 main nine-league prospective input verification.
No revised production predictions; reuse reviewed team mappings and existing feature engine."""
import json
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timedelta
from pathlib import Path
from league_config import LEAGUES
from nine_league_results_pilot import SOURCES,result_key
from extra_league_training_inventory import fetch_season,deduplicate,SEASONS
from extra_league_features import feature_rows
from extra_league_retraining import TUNE_START
from extra_ml_preflight import preflight
from results_source_pilot import TR,read
SPORTS={code:sport for _,code,sport in LEAGUES}

def identity(code,name):
    return result_key(name,code,SPORTS[code])

def fixtures(payload,code,day,now):
    if not isinstance(payload.get("events"),list):
        raise ValueError("ESPN schema")
    out=[]
    for e in payload["events"]:
        try:
            comp,=e["competitions"]
            status=comp.get("status",e.get("status",{}))["type"]
            if status.get("name")!="STATUS_SCHEDULED" or status.get("completed") is not False:
                continue
            kickoff=datetime.fromisoformat(comp.get("date",e["date"]).replace("Z","+00:00"))
            if kickoff.tzinfo is None or kickoff<=now or kickoff.astimezone(TR).date()!=day:
                continue
            teams={x["homeAway"]:x for x in comp["competitors"]}
            if len(comp["competitors"])!=2 or set(teams)!={"home","away"}:
                continue
            h,a=[identity(code,teams[k]["team"]["displayName"]) for k in ("home","away")]
            eid=str(e["id"])
            if not h or not a or h==a or not eid.isascii() or not eid.isdigit():
                continue
            out.append(dict(league=code,date=day.isoformat(),home=h,away=a,eventId=eid,kickoff=kickoff.isoformat()))
        except (ValueError,TypeError,KeyError,AttributeError):
            continue
    return out

def run(reader=read):
    now=datetime.now(TR)
    jobs=[(code,SOURCES[code][0],year) for _,code,_ in LEAGUES for year in SEASONS]
    with ThreadPoolExecutor(max_workers=4) as pool:
        res=list(pool.map(lambda j:fetch_season(j,reader,end=now.date()),jobs))
    if any(s["error"] for _,s in res):raise ValueError("incomplete historical inventory")
    history,_,_=deduplicate([r for rs,_ in res for r in rs])
    training=feature_rows([r for r in history if r["date"]<TUNE_START])
    if len(training)!=2848:raise ValueError("V6.65 training inventory changed")
    keys=set(training[0]["features"])
    if len(keys)!=119 or any(set(r["features"])!=keys for r in training):raise ValueError("feature schema")
    jobs=[(code,now.date()+timedelta(days=i)) for _,code,_ in LEAGUES for i in (1,2,3)]
    def load(j):
        code,day=j
        url=f"https://site.api.espn.com/apis/site/v2/sports/soccer/{SOURCES[code][1]}/scoreboard?dates={day:%Y%m%d}"
        return fixtures(json.loads(reader(url)),code,day,now)
    with ThreadPoolExecutor(max_workers=4) as pool:
        games=[f for rs in pool.map(load,jobs) for f in rs]
    if datetime.now(TR).date()!=now.date():raise ValueError("date changed; rerun")
    r=preflight(history,games,now,keys,identity_fn=identity)
    r.update(version="6.66",mode="main_league_prospective_input_preflight",historyMatches=len(history),trainingMatches=len(training),
        sourceSuccessful=len(res),configuredLeagues=len(LEAGUES),eligibleByLeague=dict(Counter(x["league"] for x in r["entries"])),
        productionModelValidated=False,updatedAt=datetime.now(TR).isoformat())
    Path("main_leagues_ml_preflight.json").write_text(json.dumps(r,indent=2)+"\n")
    print("MAIN_ML_PREFLIGHT_666",json.dumps({k:v for k,v in r.items() if k!="entries"}))
if __name__=="__main__":run()
