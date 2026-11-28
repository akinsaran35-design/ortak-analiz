"""V6.72 historical weight sensitivity in main leagues; reused holdout, no promotion."""
import json,math
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from league_config import LEAGUES
from nine_league_results_pilot import SOURCES
from extra_league_training_inventory import fetch_season,deduplicate,SEASONS,END
from extra_league_features import feature_rows
from extra_league_retraining import partition,baseline,blend,label,MIN_TRAIN,MIN_TUNE,MIN_TEST
from extra_league_model_comparison import alternative_fit
from extra_league_score_audit import MARKETS,paired_date_bootstrap
from extra_prospective_reliability import reliability,probabilities
from results_source_pilot import TR,read

WEIGHTS=(0,.25,.5,.75,1)
REFERENCE=.5
MIN_GAIN=.001

def prepare(rows,pred):
    if not rows or len(rows)!=len(pred):raise ValueError("prediction count")
    out=[]
    for r,q in zip(rows,pred):
        p=baseline(r)
        if not all(probabilities(dict(zip(MARKETS,v))) for v in (p,q)):raise ValueError("incoherent probability")
        out.append((r["date"],p,q,label(r)))
    return out

def select(sample):
    if not sample:raise ValueError("empty tuning set")
    losses={w:sum((p-y)**2 for _,a,b,ys in sample for p,y in zip(blend(a,b,w),ys))/(3*len(sample)) for w in WEIGHTS}
    best=min(WEIGHTS,key=lambda w:(losses[w],abs(w-REFERENCE),w))
    selected=best if losses[REFERENCE]-losses[best]>=MIN_GAIN else REFERENCE
    return selected,{str(w):losses[w] for w in WEIGHTS}

def assess(sample,w):
    out={}
    for i,m in enumerate(MARKETS):
        pairs=[(d,blend(a,b,REFERENCE)[i],blend(a,b,w)[i],ys[i]) for d,a,b,ys in sample]
        blocks=defaultdict(list)
        for d,p,q,y in pairs:blocks[d].append((p-y)**2-(q-y)**2)
        def summary(index):
            data=[(x[index],x[3]) for x in pairs]
            r=reliability(data)
            r["accuracyPct"]=100*sum((p>=.5)==bool(y) for p,y in data)/len(data)
            return {k:r[k] for k in ("n","brier","logLoss","ece10","accuracyPct")}
        out[m]=dict(fixedBlend=summary(1),tunedBlend=summary(2),pairedBootstrap=paired_date_bootstrap(blocks))
    return out

def evaluate(rows,fit=alternative_fit):
    train,tune,test=partition(feature_rows(rows))
    if min(len(train)/MIN_TRAIN,len(tune)/MIN_TUNE,len(test)/MIN_TEST)<1:raise ValueError("insufficient sample")
    keys=sorted(train[0]["features"])
    if len(keys)!=119 or any(set(r["features"])!=set(keys) for r in train+tune+test):raise ValueError("feature schema")
    tp,vp=fit(train,tune,test,keys,"catboost")
    w,losses=select(prepare(tune,tp))
    result=assess(prepare(test,vp),w)
    return dict(trainingMatches=len(train),tuningMatches=len(tune),testMatches=len(test),featureCount=len(keys),
        trainingThrough=train[-1]["date"],tuningThrough=tune[-1]["date"],testStart=test[0]["date"],testThrough=test[-1]["date"],
        fixedWeight=REFERENCE,tunedWeight=w,tuningLosses=losses,minimumTuningGain=MIN_GAIN,markets=result)

def run(reader=read):
    jobs=[(code,SOURCES[code][0],year) for _,code,_ in LEAGUES for year in SEASONS]
    with ThreadPoolExecutor(max_workers=4) as pool:
        groups=list(pool.map(lambda job:fetch_season(job,reader,end=END),jobs))
    if any(s["error"] for _,s in groups):raise ValueError("incomplete source inventory")
    rows,duplicates,conflicts=deduplicate([r for rs,_ in groups for r in rs])
    if {r["league"] for r in rows}!={code for _,code,_ in LEAGUES}:raise ValueError("league coverage")
    report=dict(version="6.72",mode="historical_weight_sensitivity_only",historicalMatches=len(rows),sourceSuccessful=len(groups),
        sourceVerification="single_source_only",duplicateIdentitiesExcluded=duplicates,conflictingIdentitiesExcluded=conflicts,
        repeatedHoldout=True,testPeriodUsedForTuning=False,independentProspectiveValidation=False,
        existingFrozenCohortsModified=False,productionModelValidated=False,automaticApproval=False,
        updatedAt=datetime.now(TR).isoformat(),**evaluate(rows))
    Path("main_ml_weight_research.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    print("MAIN_ML_WEIGHT_672",json.dumps(report))
if __name__=="__main__":run()
