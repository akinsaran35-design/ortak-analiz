"""Select research parameters using validation only; inspected holdout is not independent."""
from historical_baseline import evaluate

def tune(rows, today):
    trials=[]
    for window in (5,10,20):
        for rho in (-0.05,0.0,0.05):
            report=evaluate(rows,today,window=window,rho=rho,phase="validation")
            metrics=report["metrics"]
            if len(metrics)==3 and min(m["n"] for m in metrics.values())>=50:
                trials.append(dict(window=window,rho=rho,brier=sum(m["brier"] for m in metrics.values())/3))
    result=dict(status="research_only",realBettingEnabled=False,modelCalibrated=False,holdoutPreviouslyInspected=True,trials=trials)
    if trials:
        best=min(trials,key=lambda t:t["brier"])
        result["selected"]=best
        result["test"]=evaluate(rows,today,window=best["window"],rho=best["rho"])
    return result
