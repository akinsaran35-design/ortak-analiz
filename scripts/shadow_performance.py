"""Research-only tracking. Scores must come from verified final results."""
import json
import hashlib
import math
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def stamp(s):
    return datetime.fromisoformat(s.replace("Z","+00:00"))

def archive_coupon(records, coupon, now):
    picks = coupon.get("selections", [])
    if coupon.get("mode") != "shadow" or coupon.get("liveEnabled") is not False or not 1 <= len(picks) <= 3:
        return
    if any(stamp(p["kickoff"]) <= now for p in picks):
        return
    ids = sorted(p["eventId"] for p in picks)
    if len(set(ids)) != len(ids):
        return
    key = hashlib.sha256(json.dumps(ids).encode()).hexdigest()
    if key not in records:
        records[key] = {"recordedAt":now.isoformat(),"stake":100,
                        "selections":picks,"status":"pending"}

def settle(records, results, now):
    for r in records.values():
        if r["status"] != "pending":
            continue
        outcomes = []
        for p in r["selections"]:
            f = results.get(p["eventId"], {})
            score = f.get("score")
            if f.get("status") != "final" or not isinstance(score,list) or len(score)!=2 or not all(type(x) is int and x>=0 for x in score) or stamp(p["kickoff"]) >= now:
                break
            h,a = score
            market = p["market"]
            if market not in ("2.5 Over","1.5 Over","BTTS Yes"):
                break
            outcomes.append({"score":score,"won":{"2.5 Over":h+a>=3,"1.5 Over":h+a>=2,"BTTS Yes":h>0 and a>0}[market]})
        if len(outcomes) == len(r["selections"]):
            won = all(o["won"] for o in outcomes)
            r.update(status="won" if won else "lost", outcomes=outcomes,
                     settledAt=now.isoformat(), profit=round(r["stake"]*(math.prod(p["odds"] for p in r["selections"])-1),2) if won else -r["stake"])

def metrics(rows):
    settled = [r for r in rows if r["status"] in ("won","lost")]
    n = len(settled)
    wins = sum(r["status"]=="won" for r in settled)
    stake = sum(r["stake"] for r in settled)
    profit = sum(r["profit"] for r in settled)
    return {"recorded":len(rows),"settled":n,"pending":len(rows)-n,"won":wins,"lost":n-wins,
            "winRate":wins/n if n else None,"profit":round(profit,2),"roi":profit/stake if stake else None}

def load(name, default):
    path = ROOT/name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default

def save(name, value):
    path = ROOT/name
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding="utf-8")
    tmp.replace(path)

if __name__ == "__main__":
    now = datetime.now(timezone.utc)
    records = load("shadow_archive.json",{})
    archive_coupon(records,load("shadow_coupon.json",{}),now)
    settle(records,load("shadow_verified_results.json",{}),now)
    rows = list(records.values())
    save("shadow_archive.json",records)
    save("shadow_performance.json",{"version":"4.8","mode":"shadow","liveEnabled":False,
         "updatedAt":now.isoformat(),"overall":metrics(rows),
         "bySize":{str(n):metrics([r for r in rows if len(r["selections"])==n]) for n in (1,2,3)}})
