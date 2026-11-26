"""Replay existing published reports without requests or rewriting production files."""
import json
from collections import Counter
from pathlib import Path
from datetime import datetime
from match_odds import build_report

if __name__=="__main__":
    daily=json.loads(Path("daily.json").read_text())
    odds=json.loads(Path("odds.json").read_text())
    now=datetime.fromisoformat(daily["updatedAt"].replace("Z","+00:00"))
    report=build_report(daily,odds,now)
    reasons=Counter(r["reason"] for r in report["unmatched"])
    assert report["matchedCount"]+report["unmatchedCount"]==len(daily["candidates"])
    assert all(r["reason"]!="date_mismatch" or r["date"] not in r["providerDates"] for r in report["unmatched"])
    print(json.dumps({"snapshotReplay":True,"asOf":now.isoformat(),"candidateCount":len(daily["candidates"]),"matched":report["matchedCount"],"unmatchedReasons":dict(reasons),"apiRequests":0,"decision":report["decision"]},ensure_ascii=False))
