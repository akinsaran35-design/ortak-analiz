"""V6.65 evaluate the existing feature/model policy in the nine main UI leagues.
Historical research only; never change the frozen six-league cohort or live predictions."""
import json
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from league_config import LEAGUES
from nine_league_results_pilot import SOURCES
from extra_league_training_inventory import fetch_season,deduplicate,SEASONS,END
from extra_league_features import feature_rows
from extra_league_retraining import partition,metrics
from extra_league_model_comparison import alternative_fit
from results_source_pilot import TR,read

def evaluate(rows,fit=alternative_fit):
    train,tune,test=partition(feature_rows(rows))
    if len(train)<500 or len(tune)<300 or len(test)<300:
        raise ValueError("insufficient chronological sample")
    keys=sorted(train[0]["features"])
    if len(keys)!=119 or any(set(r["features"])!=set(keys) for r in train+tune+test):
        raise ValueError("feature schema mismatch")
    # Fixed policy from V6.54; do not retune using this test period.
    _,pred=fit(train,tune,test,keys,"catboost")
    if len(pred)!=len(test):raise ValueError("prediction count")
    return dict(trainingMatches=len(train),tuningMatches=len(tune),testMatches=len(test),featureCount=len(keys),
        testLeagueCounts=dict(Counter(r["league"] for r in test)),trainingThrough=train[-1]["date"],testStart=test[0]["date"],testThrough=test[-1]["date"],
        markets=metrics(test,pred,.5,model_name="catboost"))

def run(reader=read):
    jobs=[(code,SOURCES[code][0],year) for _,code,_ in LEAGUES for year in SEASONS]
    with ThreadPoolExecutor(max_workers=4) as pool:
        result=list(pool.map(lambda j:fetch_season(j,reader,end=END),jobs))
    sources=[s for _,s in result]
    if any(s["error"] for s in sources):raise ValueError("incomplete source inventory")
    rows,duplicates,conflicts=deduplicate([r for group,_ in result for r in group])
    if set(r["league"] for r in rows)!={code for _,code,_ in LEAGUES}:raise ValueError("incomplete league coverage")
    report=dict(version="6.65",mode="historical_research_only",sourceSuccessful=len(sources),sourceRequested=len(jobs),
        sourceVerification="single_source_only",historicalMatches=len(rows),duplicateIdentitiesExcluded=duplicates,conflictingIdentitiesExcluded=conflicts,
        fixedPolicy=dict(poisson=.5,catboost=.5),testPeriodUsedForTuning=False,independentProspectiveValidation=False,
        existingArchivesModified=False,productionModelValidated=False,updatedAt=datetime.now(TR).isoformat(),**evaluate(rows))
    Path("main_leagues_ml_research.json").write_text(json.dumps(report,indent=2)+"\n")
    print("MAIN_LEAGUES_ML_665",json.dumps(report))
if __name__=="__main__":run()
