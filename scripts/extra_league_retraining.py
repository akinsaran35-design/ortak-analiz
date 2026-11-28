"""V6.53 fixed chronological historical research; not independent or production validation."""
import json,math
from collections import Counter
from datetime import datetime
from pathlib import Path
from extra_league_training_inventory import build
from extra_league_features import feature_rows
from extra_league_score_audit import MARKETS,goal_probabilities,score_class,xgb_market_probabilities,paired_date_bootstrap
from results_source_pilot import TR

TUNE_START="2024-07-01"
TEST_START="2025-07-01"
MIN_TRAIN=500
MIN_TUNE=300
MIN_TEST=300
WEIGHTS=(0,.25,.5,.75,1)

def partition(rows):
    rows=sorted(rows,key=lambda r:(r["date"],r["league"],r["home"],r["away"]))
    return ([r for r in rows if r["date"]<TUNE_START],
        [r for r in rows if TUNE_START<=r["date"]<TEST_START],
        [r for r in rows if r["date"]>=TEST_START])

def label(r):
    return tuple(r["labels"][k] for k in MARKETS)

def vector(rows,keys):
    import numpy as np
    return np.array([[r["features"].get(k) if r["features"].get(k) is not None else np.nan for k in keys] for r in rows],dtype=float)

def fit_predict(train,tune,test,keys):
    import numpy as np
    from xgboost import XGBClassifier
    y=np.array([score_class(label(r)) for r in train])
    if set(y)!=set(range(5)):
        raise ValueError("missing class")
    model=XGBClassifier(objective="multi:softprob",num_class=5,n_estimators=100,max_depth=3,
        learning_rate=.05,min_child_weight=10,reg_lambda=10,random_state=653,n_jobs=1,tree_method="hist")
    model.fit(vector(train,keys),y)
    return [[xgb_market_probabilities(p) for p in model.predict_proba(vector(group,keys))] for group in (tune,test)]

def baseline(r):
    f=r["features"]
    return goal_probabilities(f["leagueHomeGoals"],f["leagueAwayGoals"])

def blend(a,b,w):
    return tuple((1-w)*x+w*y for x,y in zip(a,b))

def tune_weight(rows,pred):
    if not rows or len(rows)!=len(pred):
        raise ValueError("missing tune predictions")
    def loss(w):
        return sum((p-y)**2 for r,q in zip(rows,pred) for p,y in zip(blend(baseline(r),q,w),label(r)))/(len(rows)*3)
    selected=min(WEIGHTS,key=loss)
    return selected if loss(0)-loss(selected)>=.001 else 0

def metrics(rows,pred,w,*,model_name="xgboost"):
    result={}
    for i,k in enumerate(MARKETS):
        pairs=[(r["date"],baseline(r)[i],q[i],blend(baseline(r),q,w)[i],label(r)[i]) for r,q in zip(rows,pred)]
        def score(j):
            n=len(pairs)
            return dict(brier=round(sum((r[j]-r[4])**2 for r in pairs)/n,6),
                logLoss=round(-sum(r[4]*math.log(max(1e-12,r[j]))+(1-r[4])*math.log(max(1e-12,1-r[j])) for r in pairs)/n,6),
                accuracyPct=round(100*sum((r[j]>=.5)==bool(r[4]) for r in pairs)/n,2))
        by_day={}
        for d,p,q,v,y in pairs:
            by_day.setdefault(d,[]).append((p-y)**2-(v-y)**2)
        result[k]=dict(n=len(pairs),poisson=score(1),blended=score(3),descriptiveBootstrap=paired_date_bootstrap(by_day))
        result[k][model_name]=score(2)
    return result

def evaluate(rows,fit=fit_predict):
    train,tune,test=partition(rows)
    result=dict(version="6.53",mode="historical_single_source_research",trainingMatches=len(train),tuningMatches=len(tune),
        testMatches=len(test),tuneStart=TUNE_START,testStart=TEST_START,independentValidation=False,
        productionModelValidated=False,existingArchivesModified=False,xgIncluded=False,xtIncluded=False,
        trainingSourceVerification="single_source_only",status="insufficient_data",markets={})
    if min(len(train)/MIN_TRAIN,len(tune)/MIN_TUNE,len(test)/MIN_TEST)<1:
        return result
    keys=sorted(train[0]["features"])
    if not all(set(r["features"])==set(keys) for r in train+tune+test):
        raise ValueError("feature schema mismatch")
    tune_pred,test_pred=fit(train,tune,test,keys)
    if len(tune_pred)!=len(tune) or len(test_pred)!=len(test):
        raise ValueError("prediction length")
    w=tune_weight(tune,tune_pred)
    result.update(status="evaluated",featureCount=len(keys),selectedBlendWeight=w,
        testLeagueCounts=dict(Counter(r["league"] for r in test)),markets=metrics(test,test_pred,w),
        trainingLastDate=train[-1]["date"],tuningLastDate=tune[-1]["date"],testLastDate=test[-1]["date"])
    return result

if __name__=="__main__":
    inventory,rows=build()
    if inventory["successfulSources"]!=inventory["requestedSources"]:
        raise SystemExit("incomplete historical source inventory")
    r=evaluate(feature_rows(rows))
    r["updatedAt"]=datetime.now(TR).isoformat()
    Path("extra_retraining_report.json").write_text(json.dumps(r,indent=2)+"\n")
    print("HISTORICAL_RETRAIN_653",json.dumps(r))
    if r["status"]!="evaluated":
        raise SystemExit("insufficient historical sample")
