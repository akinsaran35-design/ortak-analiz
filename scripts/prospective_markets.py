"""Prospective three-market research; never backfill missing historical forecasts."""
import math
from datetime import datetime,date,timedelta
MARKETS=("1.5 Üst","2.5 Üst","KG Var")
MODELS=("old","candidate","baseline")
def actual(h,a): return (int(h+a>=2),int(h+a>=3),int(h>0 and a>0))
def valid(p): return type(p) in (float,int) and math.isfinite(p) and 0<=p<=1
def coherent(markets,legacy=None):
    """Nested forecasts must agree with the original 2.5 market and set inclusion."""
    try:
        if not isinstance(markets,dict) or set(markets)!=set(MARKETS):return False
        if any(not isinstance(markets[m],dict) or set(markets[m])!=set(MODELS) for m in MARKETS):return False
        if not all(valid(markets[m][k]) for m in MARKETS for k in MODELS):return False
        if legacy is not None and any(not valid(legacy[k]) or abs(markets["2.5 Üst"][k]-legacy[k])>1e-12 for k in MODELS):return False
        return all(markets["1.5 Üst"][k]+1e-12>=max(markets["2.5 Üst"][k],markets["KG Var"][k]) for k in MODELS)
    except (KeyError,TypeError,ValueError):return False
def capture(history,old,new):
    if not history or len(old)!=3 or len(new)!=3: raise ValueError("invalid input")
    base=[sum(actual(x[3],x[4])[i] for x in history)/len(history) for i in range(3)]
    out={m:dict(old=old[i],candidate=new[i],baseline=base[i]) for i,m in enumerate(MARKETS)}
    if not coherent(out): raise ValueError("incoherent probabilities")
    return out
def classification_counts(rows):
    # Fixed descriptive threshold, not a selection rule or an optimized cutoff.
    correct=sum(int(p["candidate"]>=.5)==y for p,y,_ in rows)
    return {"tested":len(rows),"correct":correct,"incorrect":len(rows)-correct}

def summarize(records,now,include_calibration=False):
    out={}
    for i,m in enumerate(MARKETS):
        rows=[];pending=0;legacy=0;invalid=0
        for r in records.values():
            try:
                if "prospectiveMarkets" not in r:
                    if i!=1: legacy+=1;continue
                    p={k:r[k] for k in MODELS}
                else:
                    if not coherent(r["prospectiveMarkets"],r):raise ValueError("incoherent forecast")
                    p=r["prospectiveMarkets"][m]
                recorded=datetime.fromisoformat(r["recordedAt"])
                if recorded.tzinfo is None or recorded>now or recorded.astimezone(now.tzinfo).date()>=date.fromisoformat(r["date"]): raise ValueError("late")
                if not all(valid(p[k]) for k in MODELS): raise ValueError("probability")
                result=r["result"]
                if result is None: pending+=1;continue
                if not isinstance(result,list) or len(result)!=2 or not all(type(v) is int and v>=0 for v in result): raise ValueError("score")
                if date.fromisoformat(r["date"])>=now.date(): raise ValueError("unsettled date")
                rows.append((p,actual(*result)[i],date.fromisoformat(r["date"])))
            except (KeyError,TypeError,ValueError,AttributeError): invalid+=1
        scores={k:sum((p[k]-y)**2 for p,y,_ in rows)/len(rows) for k in MODELS} if rows else {}
        out[m]={"tested":len(rows),"pending":pending,"legacyWithoutForecast":legacy,"invalid":invalid,"scores":scores,"minimumMatches":500,"status":"research_only","liveEnabled":False}
        out[m]["classification"]={"threshold":.5,"model":"candidate","descriptiveOnly":True,**classification_counts(rows),
            "periods":{str(days):classification_counts([row for row in rows if now.date()-timedelta(days=days)<=row[2]<now.date()]) for days in (1,7,30)}}
        if include_calibration:
            n=len(rows)
            observed=sum(y for _,y,_ in rows)/n if n else None
            predicted={k:sum(p[k] for p,_,_ in rows)/n for k in MODELS} if n else {}
            out[m]["calibration"]={"sample":n,"observedRate":observed,"meanPrediction":predicted,
                "gapPP":{k:(v-observed)*100 for k,v in predicted.items()} if n else {},
                "sampleAdequate":n>=500 and invalid==0,"descriptiveOnly":True}
    return out
