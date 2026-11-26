"""Research-only flat-stake ROI; provenance must be verified upstream."""
import math
from datetime import datetime
from collections import defaultdict
def timestamp(s):
    t=datetime.fromisoformat(s.replace("Z","+00:00"))
    if t.tzinfo is None: raise ValueError("timezone required")
    return t
def evaluate(records):
    groups=defaultdict(list)
    rejected=0
    for r in records:
        try:
            key=(str(r["matchID"]),r["market"])
            if key[1] not in ("over15","over25","btts"): raise ValueError()
            p=float(r["probability"]); odds=float(r["odds"])
            if not (math.isfinite(p) and math.isfinite(odds) and 0<=p<=1 and odds>1 and timestamp(r["predictionAt"])<=timestamp(r["oddsAt"])<timestamp(r["kickoff"]) and r["outcome"] in (0,1) and r["verified"] is True): raise ValueError()
            groups[key].append((p,odds,r["outcome"],timestamp(r["predictionAt"]),timestamp(r["oddsAt"]),timestamp(r["kickoff"])))
        except (KeyError,ValueError,TypeError,AttributeError,OverflowError):
            rejected+=1
    selected=0; profit=0.; ev=0.; conflicts=0
    for values in groups.values():
        if len(set(values))!=1:
            conflicts+=1
            continue
        p,odds,o,*_=values[0]
        if p<.70 or p*odds<=1: continue
        selected+=1; profit+=odds-1 if o else -1; ev+=p*odds-1
    return dict(status="research_only",realBettingEnabled=False,selected=selected,rejected=rejected,conflicts=conflicts,profitUnits=profit,roi=profit/selected if selected else None,meanEV=ev/selected if selected else None)
