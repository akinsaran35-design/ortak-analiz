import json
import math
from datetime import datetime, timezone
from pathlib import Path

def report(records):
    bins = [{"count":0,"sumP":0.0,"sumY":0} for _ in range(10)]
    losses = []
    seen = set()
    for r in records.values():
        p, ft = r.get("candidate"), r.get("result")
        if r.get("modelVersion") != "4.4" or type(p) not in (int,float) or not math.isfinite(p) or not 0 <= p <= 1:
            continue
        if not isinstance(ft,list) or len(ft)!=2 or any(type(x) is not int or x<0 for x in ft):
            continue
        try:
            if datetime.fromisoformat(r["recordedAt"]).date().isoformat() >= r["date"]:
                continue
            key = tuple(r[k] for k in ("date","league","home","away"))
        except (KeyError,ValueError,TypeError):
            continue
        if key in seen:
            continue
        seen.add(key)
        y = int(sum(ft)>=3)
        b = bins[min(9,int(p*10))]
        b["count"] += 1
        b["sumP"] += p
        b["sumY"] += y
        losses.append((p-y)**2)
    n = len(losses)
    rows = [{"lower":i/10,"upper":(i+1)/10,"count":b["count"],"meanProbability":b["sumP"]/b["count"] if b["count"] else None,"actualRate":b["sumY"]/b["count"] if b["count"] else None} for i,b in enumerate(bins)]
    return {"version":"4.17","market":"2.5 Over","modelVersion":"4.4","tested":n,"minimumMatches":500,"brier":sum(losses)/n if n else None,"ece":sum(abs(b["sumP"]-b["sumY"]) for b in bins)/n if n else None,"bins":rows,"status":"review_required" if n>=500 else "collecting_data","modelCalibrated":False,"realBettingEnabled":False}

if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent
    result = report(json.loads((root/"prospective_archive.json").read_text(encoding="utf-8")))
    result["updatedAt"] = datetime.now(timezone.utc).isoformat()
    (root/"calibration.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
