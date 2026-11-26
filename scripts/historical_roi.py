"""Research-only flat-stake ROI on verified pre-match price records."""
import math
def evaluate(records):
    seen=set()
    selected=0
    profit=0.0
    rejected=0
    for r in records:
        try:
            key=(r["matchID"],r["market"])
            p=float(r["probability"]); odds=float(r["odds"])
            if not (math.isfinite(p) and math.isfinite(odds) and 0<=p<=1 and odds>1 and r["predictionAt"]<=r["oddsAt"]<r["kickoff"] and r["outcome"] in (0,1) and r["verified"] is True):
                raise ValueError()
            if key in seen: raise ValueError()
            seen.add(key)
            if p<.70 or p*odds<=1: continue
            selected+=1
            profit+=odds-1 if r["outcome"] else -1
        except (KeyError,ValueError,TypeError):
            rejected+=1
    return dict(status="research_only",realBettingEnabled=False,selected=selected,rejected=rejected,profitUnits=profit,roi=profit/selected if selected else None)
