"""Prospective three-market research; never backfill missing historical forecasts."""
import math
from datetime import datetime,date
MARKETS=("1.5 Üst","2.5 Üst","KG Var")
MODELS=("old","candidate","baseline")
def actual(h,a): return (int(h+a>=2),int(h+a>=3),int(h>0 and a>0))
def valid(p): return type(p) in (float,int) and math.isfinite(p) and 0<=p<=1
def capture(history,old,new):
    if not history or len(old)!=3 or len(new)!=3: raise ValueError("invalid input")
    base=[sum(actual(x[3],x[4])[i] for x in history)/len(history) for i in range(3)]
    out={m:dict(old=old[i],candidate=new[i],baseline=base[i]) for i,m in enumerate(MARKETS)}
    if not all(valid(v) for row in out.values() for v in row.values()): raise ValueError("invalid probability")
    return out
def summarize(records,now):
    out={}
    for i,m in enumerate(MARKETS):
        rows=[];pending=0;legacy=0;invalid=0
        for r in records.values():
            try:
                if "prospectiveMarkets" not in r:
                    if i!=1: legacy+=1;continue
                    p={k:r[k] for k in MODELS}
                else: p=r["prospectiveMarkets"][m]
                recorded=datetime.fromisoformat(r["recordedAt"])
                if recorded.tzinfo is None or recorded>now or recorded.astimezone(now.tzinfo).date()>=date.fromisoformat(r["date"]): raise ValueError("late")
                if not all(valid(p[k]) for k in MODELS): raise ValueError("probability")
                result=r["result"]
                if result is None: pending+=1;continue
                if not isinstance(result,list) or len(result)!=2 or not all(type(v) is int and v>=0 for v in result): raise ValueError("score")
                if date.fromisoformat(r["date"])>=now.date(): raise ValueError("unsettled date")
                rows.append((p,actual(*result)[i]))
            except (KeyError,TypeError,ValueError,AttributeError): invalid+=1
        scores={k:sum((p[k]-y)**2 for p,y in rows)/len(rows) for k in MODELS} if rows else {}
        out[m]={"tested":len(rows),"pending":pending,"legacyWithoutForecast":legacy,"invalid":invalid,"scores":scores,"minimumMatches":500,"status":"research_only","liveEnabled":False}
    return out
