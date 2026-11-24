import json
import math
from pathlib import Path
from datetime import datetime, timezone, timedelta
from statistics import median

def metrics(over, under):
    if not all(isinstance(x, (int, float)) and math.isfinite(x) and x > 1 for x in (over, under)):
        raise ValueError("Invalid odds")
    total = 1/over + 1/under
    return total-1, (1/over)/total

def main():
    now = datetime.now(timezone.utc)
    daily, odds, matching = [json.loads(Path(p).read_text(encoding="utf-8")) for p in ("daily.json","odds.json","matching.json")]
    try:
        snapshot_age = now - datetime.fromisoformat(odds["updatedAt"].replace("Z","+00:00"))
        fresh = timedelta(0) <= snapshot_age <= timedelta(minutes=30)
    except (KeyError, ValueError, TypeError):
        fresh = False
    events = {e["id"]: e for e in odds["events"]} if fresh else {}
    candidates = {}
    for c in daily["candidates"]:
        candidates.setdefault(c["match"], []).append(c)
    rows = []
    for m in matching["matched"]:
        e = events.get(m["eventId"])
        cs = candidates.get(m["match"], [])
        if not e or len(cs) != 1:
            continue
        if datetime.fromisoformat(e["kickoff"].replace("Z","+00:00")) <= now:
            continue
        books = {}
        for b in e["bookmakers"]:
            for l in b["lines"]:
                try:
                    age = now - datetime.fromisoformat(l["lastUpdate"].replace("Z","+00:00"))
                    if l["point"] != 2.5 or not timedelta(0) <= age <= timedelta(minutes=30):
                        continue
                    margin, probability = metrics(l["over"], l["under"])
                    if not 0 <= margin <= .2:
                        continue
                    books[b["key"]] = (margin, probability)
                except (ValueError, TypeError, KeyError, OverflowError):
                    continue
        if len(books) < 3:
            continue
        p = cs[0]["markets"]["2.5 Üst"]/100
        market = median(x[1] for x in books.values())
        rows.append({"match":m["match"],"eventId":m["eventId"],"bookCount":len(books),"marketProbability":round(market,4),"modelProbabilityUncalibrated":p,"difference":round(p-market,4),"medianMargin":round(median(x[0] for x in books.values()),4)})
    report = {"version":"3.1","snapshotFresh":fresh,"updatedAt":now.isoformat(),"decision":"PAS","modelCalibrated":False,"market":"2.5","comparedCount":len(rows),"rows":rows}
    Path("market_analysis.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print("Market comparisons:",len(rows))

if __name__ == "__main__":
    assert abs(metrics(2,2)[1]-.5)<1e-9
    assert abs(metrics(1.9,1.9)[0]-(2/1.9-1))<1e-9
    main()
