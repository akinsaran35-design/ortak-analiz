"""V6.54 matched historical model comparison. Reused holdout, research only."""
import json
from datetime import datetime
from pathlib import Path
from extra_league_training_inventory import build
from extra_league_features import feature_rows
from extra_league_retraining import (partition,label,vector,fit_predict,baseline,blend,
    metrics,MIN_TRAIN,MIN_TUNE,MIN_TEST,WEIGHTS,TUNE_START,TEST_START)
from extra_league_score_audit import score_class,xgb_market_probabilities
from results_source_pilot import TR

def alternative_fit(train,tune,test,keys,name):
    import numpy as np
    y=np.array([score_class(label(r)) for r in train])
    if set(y)!=set(range(5)):
        raise ValueError("missing class")
    if name=="lightgbm":
        from lightgbm import LGBMClassifier
        model=LGBMClassifier(objective="multiclass",num_class=5,n_estimators=100,max_depth=3,
            num_leaves=8,learning_rate=.05,min_child_samples=20,reg_lambda=10,
            random_state=653,n_jobs=1,deterministic=True,force_col_wise=True,verbosity=-1)
    elif name=="catboost":
        from catboost import CatBoostClassifier
        model=CatBoostClassifier(loss_function="MultiClass",iterations=100,depth=3,
            learning_rate=.05,l2_leaf_reg=10,random_seed=653,thread_count=1,
            bootstrap_type="No",random_strength=0,allow_writing_files=False,verbose=False)
    else:
        raise ValueError("unknown model")
    model.fit(vector(train,keys),y)
    if list(model.classes_)!=list(range(5)):
        raise ValueError("unexpected class order")
    return [[xgb_market_probabilities(p) for p in model.predict_proba(vector(group,keys))] for group in (tune,test)]

def choose(tune,predictions):
    if not tune or any(len(q)!=len(tune) for q in predictions.values()):
        raise ValueError("invalid tuning predictions")
    def loss(pred,w):
        return sum((p-y)**2 for r,q in zip(tune,pred) for p,y in zip(blend(baseline(r),q,w),label(r)))/(3*len(tune))
    ref=[baseline(r) for r in tune]
    baseline_loss=loss(ref,0)
    best=(baseline_loss,"poisson",0)
    for name,pred in sorted(predictions.items()):
        for w in WEIGHTS[1:]:
            score=loss(pred,w)
            if score<best[0]-1e-12:
                best=(score,name,w)
    return best if baseline_loss-best[0]>=.001 else (baseline_loss,"poisson",0)

def compare(rows,fitters=None):
    train,tune,test=partition(rows)
    report=dict(version="6.54",mode="historical_research_only",trainingMatches=len(train),
        tuningMatches=len(tune),testMatches=len(test),tuneStart=TUNE_START,testStart=TEST_START,
        repeatedHoldout=True,independentValidation=False,productionModelValidated=False,
        existingArchivesModified=False,trainingSourceVerification="single_source_only",
        status="insufficient_data")
    if len(train)<MIN_TRAIN or len(tune)<MIN_TUNE or len(test)<MIN_TEST:
        return report
    keys=sorted(train[0]["features"])
    if not all(set(r["features"])==set(keys) for r in train+tune+test):
        raise ValueError("feature schema mismatch")
    if fitters is None:
        fitters={"xgboost":fit_predict,
            "lightgbm":lambda *a:alternative_fit(*a,"lightgbm"),
            "catboost":lambda *a:alternative_fit(*a,"catboost")}
    results={name:fit(train,tune,test,keys) for name,fit in fitters.items()}
    if any(len(t)!=len(tune) or len(v)!=len(test) for t,v in results.values()):
        raise ValueError("prediction length")
    loss,selected,w=choose(tune,{name:t for name,(t,v) in results.items()})
    # The test data cannot change selection. All comparisons are descriptive.
    comparisons={}
    for name,(_,pred) in results.items():
        comparisons[name]={k:m["xgboost"] for k,m in metrics(test,pred,1).items()}
    selected_pred=results[selected][1] if selected!="poisson" else [baseline(r) for r in test]
    final=metrics(test,selected_pred,w)
    report.update(status="evaluated",featureCount=len(keys),selectedModel=selected,selectedWeight=w,
        tuningMeanBrier=round(loss,6),minimumTuneImprovement=.001,candidateMetrics=comparisons,
        markets={k:dict(n=m["n"],poisson=m["poisson"],selected=m["blended"],
        descriptiveBootstrap=m["descriptiveBootstrap"]) for k,m in final.items()})
    return report

if __name__=="__main__":
    inventory,rows=build()
    if inventory["successfulSources"]!=inventory["requestedSources"]:
        raise SystemExit("incomplete historical source inventory")
    report=compare(feature_rows(rows))
    report["updatedAt"]=datetime.now(TR).isoformat()
    Path("extra_model_comparison.json").write_text(json.dumps(report,indent=2)+"\n")
    print("HISTORICAL_COMPARISON_654",json.dumps(report))
    if report["status"]!="evaluated":
        raise SystemExit("insufficient historical sample")
