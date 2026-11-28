"""V6.55 separate model selection and calibration windows; historical research only."""
import json,math
from datetime import datetime
from pathlib import Path
from extra_league_training_inventory import build
from extra_league_features import feature_rows
from extra_league_retraining import partition,label,baseline,blend,fit_predict,MIN_TRAIN,MIN_TEST,TUNE_START,TEST_START
from extra_league_model_comparison import alternative_fit,choose
from extra_league_score_audit import MARKETS,paired_date_bootstrap
from results_source_pilot import TR

CAL_START="2025-01-01"
MIN_PHASE=300
SLOPES=(.75,.9,1.,1.1,1.25)
INTERCEPTS=(-.2,-.1,0.,.1,.2)
MIN_GAIN=.0005

def calibrate(p,slope,intercept):
    if slope==1 and intercept==0:
        return p
    p=min(1-1e-12,max(1e-12,p))
    return 1/(1+math.exp(-(slope*math.log(p/(1-p))+intercept)))

def fit_calibration(rows,pred):
    if len(rows)!=len(pred):
        raise ValueError("calibration length")
    if len(rows)<MIN_PHASE:
        return 1.,0.
    def loss(s,b):
        return sum((calibrate(p,s,b)-y)**2 for r,ps in zip(rows,pred) for p,y in zip(ps,label(r)))/(3*len(rows))
    base=loss(1,0)
    best=(base,1.,0.)
    for s in SLOPES:
        for b in INTERCEPTS:
            v=loss(s,b)
            if v<best[0]-1e-12:
                best=(v,s,b)
    return best[1:] if base-best[0]>=MIN_GAIN else (1.,0.)

def reliability(pairs):
    n=len(pairs)
    bins=[[] for _ in range(10)]
    for p,y in pairs:
        bins[min(9,int(p*10))].append((p,y))
    out=[]
    for i,group in enumerate(bins):
        if not group:
            continue
        count=len(group)
        p=sum(x[0] for x in group)/count
        y=sum(x[1] for x in group)/count
        out.append(dict(bin=i,n=count,meanProbability=round(p,6),observedFrequency=round(y,6)))
    return dict(brier=round(sum((p-y)**2 for p,y in pairs)/n,6),
        logLoss=round(-sum(y*math.log(max(p,1e-12))+(1-y)*math.log(max(1-p,1e-12)) for p,y in pairs)/n,6),
        accuracyPct=round(100*sum((p>=.5)==bool(y) for p,y in pairs)/n,2),
        ece10=round(sum(abs(sum(p-y for p,y in g)) for g in bins)/n,6),
        bins=out)

def evaluate(rows,fitters=None):
    train,tune,test=partition(rows)
    selection=[r for r in tune if r["date"]<CAL_START]
    cal=[r for r in tune if r["date"]>=CAL_START]
    report=dict(version="6.55",mode="historical_research_only",trainingMatches=len(train),
        selectionMatches=len(selection),calibrationMatches=len(cal),testMatches=len(test),
        selectionStart=TUNE_START,calibrationStart=CAL_START,testStart=TEST_START,
        repeatedHoldout=True,independentValidation=False,productionModelValidated=False,
        existingArchivesModified=False,trainingSourceVerification="single_source_only",status="insufficient_data")
    if len(train)<MIN_TRAIN or min(len(selection),len(cal))<MIN_PHASE or len(test)<MIN_TEST:
        return report
    keys=sorted(train[0]["features"])
    if not all(set(r["features"])==set(keys) for r in train+tune+test):
        raise ValueError("feature schema mismatch")
    if fitters is None:
        fitters={"xgboost":fit_predict,"lightgbm":lambda *a:alternative_fit(*a,"lightgbm"),
            "catboost":lambda *a:alternative_fit(*a,"catboost")}
    results={name:fit(train,tune,test,keys) for name,fit in fitters.items()}
    if any(len(t)!=len(tune) or len(v)!=len(test) for t,v in results.values()):
        raise ValueError("prediction length")
    n=len(selection)
    _,selected,w=choose(selection,{name:t[:n] for name,(t,v) in results.items()})
    def selected_predictions(group,pred):
        return [blend(baseline(r),q,w) for r,q in zip(group,pred)] if selected!="poisson" else [baseline(r) for r in group]
    cal_pred=selected_predictions(cal,results[selected][0][n:] if selected!="poisson" else [])
    test_pred=selected_predictions(test,results[selected][1] if selected!="poisson" else [])
    s,b=fit_calibration(cal,cal_pred)
    markets={}
    for i,k in enumerate(MARKETS):
        pairs=[(r["date"],ps[i],calibrate(ps[i],s,b),label(r)[i]) for r,ps in zip(test,test_pred)]
        blocks={}
        for d,p,q,y in pairs:
            blocks.setdefault(d,[]).append((p-y)**2-(q-y)**2)
        markets[k]=dict(n=len(pairs),uncalibrated=reliability([(p,y) for d,p,q,y in pairs]),
            calibrated=reliability([(q,y) for d,p,q,y in pairs]),descriptiveBootstrap=paired_date_bootstrap(blocks))
    report.update(status="evaluated",featureCount=len(keys),selectedModel=selected,selectedWeight=w,
        calibrationSlope=s,calibrationIntercept=b,calibrationGridSize=len(SLOPES)*len(INTERCEPTS),
        minimumCalibrationGain=MIN_GAIN,markets=markets)
    return report

if __name__=="__main__":
    inventory,rows=build()
    if inventory["successfulSources"]!=inventory["requestedSources"]:
        raise SystemExit("incomplete historical source inventory")
    report=evaluate(feature_rows(rows))
    report["updatedAt"]=datetime.now(TR).isoformat()
    Path("extra_calibration_655.json").write_text(json.dumps(report,indent=2)+"\n")
    print("HISTORICAL_CALIBRATION_655",json.dumps(report))
    if report["status"]!="evaluated":
        raise SystemExit("insufficient historical sample")
