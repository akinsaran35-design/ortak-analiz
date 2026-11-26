"""Walk-forward baseline on primary archive only; no odds or betting claims."""
import json,math
from pathlib import Path
from collections import defaultdict
from itertools import groupby
from historical_split import split
from datetime import date
from dixon_coles import markets

def evaluate(rows,as_of):
    groups,meta=split(rows,as_of)
    history=defaultdict(list)
    scores=defaultdict(list)
    skipped=0
    for day,batch in groupby(sorted(rows,key=lambda r:r["date"]),key=lambda r:r["date"]):
        if not meta["asOf"]>day>=min((r["date"] for r in groups["train"]),default=meta["asOf"]): continue
        batch=list(batch)
        for r in batch:
            h=history[(r["league"],r["home"])]
            a=history[(r["league"],r["away"])]
            if day<meta["testStart"]: continue
            if min(len(h),len(a))<5:
                skipped+=1
                continue
            h=h[-10:];a=a[-10:]
            avg=lambda z,i:sum(x[i] for x in z)/len(z)
            lam=max(.15,min(4,(avg(h,0)+avg(a,1))/2))
            mu=max(.15,min(4,(avg(a,0)+avg(h,1))/2))
            p=markets(lam,mu,0.0)
            x,y=r["ft"]
            for k,o in (("over15",x+y>=2),("over25",x+y>=3),("btts",x>0 and y>0)):
                scores[k].append((p[k]-int(o))**2)
        for r in batch:
            x,y=r["ft"]
            history[(r["league"],r["home"])].append((x,y))
            history[(r["league"],r["away"])].append((y,x))
    return dict(status="research_only",realBettingEnabled=False,modelCalibrated=False,skipped=skipped,metrics={k:dict(n=len(v),brier=sum(v)/len(v)) for k,v in scores.items()})
if __name__=="__main__":
    a=json.loads(Path("historical_data.json").read_text())
    r=evaluate(a["matches"],date.fromisoformat(a["asOf"]))
    Path("historical_baseline.json").write_text(json.dumps(r,indent=2))
    print(r)
