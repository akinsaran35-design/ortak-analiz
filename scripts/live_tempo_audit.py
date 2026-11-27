"""Descriptive retrospective windows; never a live probability."""
from collections import Counter
from live_observation_history import delta, WINDOWS, COUNT_METRICS
from live_rate_link import stamp
import json,sys

def audit(archive):
    counts=Counter()
    samples=[]
    for key,entry in archive.items():
        points=entry["points"]
        for i,anchor in enumerate(points):
            for w in WINDOWS:
                def window(a,b):
                    d=delta(a,b,w)
                    if d is None:return None
                    chain=[p for p in points if stamp(a["receivedAt"])<=stamp(p["receivedAt"])<=stamp(b["receivedAt"])]
                    if any(any(y<x for x,y in zip(p["score"] if k=="score" else p["metrics"][k],q["score"] if k=="score" else q["metrics"][k])) for p,q in zip(chain,chain[1:]) for k in ("score",)+COUNT_METRICS):return None
                    return d
                past=next((d for p in reversed(points[:i]) if (d:=window(p,anchor)) is not None),None)
                if past is None:continue
                counts[str(w)+":observed"]+=1
                future=next((d for p in points[i+1:] if (d:=window(anchor,p)) is not None),None)
                if future is None:
                    counts[str(w)+":unlabelled"]+=1
                    continue
                counts[str(w)+":labelled"]+=1
                samples.append(dict(event=key,anchorMinute=anchor["minute"],anchorReceivedAt=anchor["receivedAt"],window=w,observedMinutes=past["observedMatchMinutes"],rates={k:[round(x/past["observedMatchMinutes"],4) for x in past["changes"][k]] for k in ("shots","shotsOnTarget","corners")},futureGoals=future["changes"]["score"]))
    return dict(version="5.56",counts=dict(counts),samples=samples,sourceTimestampVerified=False,modelCalibrated=False,predictionsEnabled=False,decision="PAS")

if __name__=="__main__":
    with open(sys.argv[1]) as f:print(json.dumps(audit(json.load(f))))
