"""Market-specific validation selection; previously inspected test remains research only."""
from historical_baseline import evaluate
def tune_markets(rows,today):
    trials=[]
    for window in (5,10,20,30):
        for rho in (-.05,0,.05):
            report=evaluate(rows,today,window=window,rho=rho,phase="validation")
            trials.append((window,rho,report["metrics"]))
    selected={}
    for market in ("over15","over25","btts"):
        eligible=[(w,r,m[market]) for w,r,m in trials if market in m and m[market]["n"]>=50]
        if not eligible: continue
        w,r,m=min(eligible,key=lambda t:t[2]["brier"])
        test=evaluate(rows,today,window=w,rho=r)["metrics"].get(market)
        selected[market]=dict(window=w,rho=r,validation=m,test=test)
    return dict(status="research_only",realBettingEnabled=False,holdoutPreviouslyInspected=True,selected=selected)
