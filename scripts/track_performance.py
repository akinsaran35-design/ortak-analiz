import json
import urllib.request
from datetime import datetime, timedelta, timezone, date
from pathlib import Path

root = Path(__file__).resolve().parent.parent
now = datetime.now(timezone(timedelta(hours=3)))
today = now.date()
daily = json.loads((root/"daily.json").read_text(encoding="utf-8"))
archive = root/"prediction_archive.json"
records = json.loads(archive.read_text(encoding="utf-8")) if archive.exists() else {}
from fixture_schema import matches_in, final_score
from league_config import FIXTURE_CODES as leagues
markets = ["1.5 Üst","2.5 Üst","KG Var"]
def key(d,l,m):
    return json.dumps([d,l,m],ensure_ascii=False)
from calendar_duplicate_guard import load_guard
blocked=load_guard(root,records,"performance",now)
calendar_duplicate_prevented=0
# Only future calendar dates; kickoff times are not verified.
for c in daily.get("candidates",[]):
    if c["date"] <= today.isoformat() or c["league"] not in leagues:
        continue
    k = key(c["date"],c["league"],c["match"])
    if k not in records and (leagues[c["league"]], *c["match"].split(" – "), c["date"]) in blocked:
        calendar_duplicate_prevented+=1
        continue
    if k not in records and all(type(c["markets"].get(m)) in (int,float) and 0<=c["markets"][m]<=100 for m in markets):
        records[k] = {"date":c["date"],"league":c["league"],"match":c["match"],
                      "recordedAt":now.isoformat(),"modelVersion":daily.get("version"),
                      "markets":c["markets"],"result":None}
def team(x):
    return str(x.get("name") or x.get("code") or "").strip() if isinstance(x,dict) else str(x or "").strip()
errors = []
# No single-source settlement; use corroborated results only.
from verified_results import load_verified, settle_verified
try:
    verified_count = settle_verified(records, load_verified(root,now), now, leagues)
except (OSError, ValueError, KeyError, TypeError) as exc:
    verified_count = 0
    errors.append(f"verified_results: {exc}")
def metrics(rows):
    settled = [r for r in rows if r["result"] is not None]
    out = {"recorded":len(rows),"settled":len(settled),"pending":len(rows)-len(settled),"markets":{}}
    for i,m in enumerate(markets):
        pairs = []
        for r in settled:
            h,a = r["result"]
            y = [h+a>=2,h+a>=3,h>0 and a>0][i]
            pairs.append((r["markets"][m]/100,int(y)))
        n=len(pairs)
        out["markets"][m]={"tested":n,"brier":round(sum((p-y)**2 for p,y in pairs)/n,6) if n else None,"actualRate":round(100*sum(y for p,y in pairs)/n,2) if n else None}
    return out
rows=list(records.values())
report={"version":"2.4","updatedAt":now.isoformat(),"method":"First recorded future-date candidates; new scores require corroborated sources; kickoff unverified; no profit measurement.","errors":errors,"verifiedFallbackSettled":verified_count,"calendarDuplicatePrevented":calendar_duplicate_prevented,"overall":metrics(rows),"leagues":{l:metrics([r for r in rows if r["league"]==l]) for l in leagues},"periods":{str(n):metrics([r for r in rows if r["date"] >= (today-timedelta(days=n)).isoformat() and r["date"]<today.isoformat()]) for n in (30,90)}}
archive.write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding="utf-8")
(root/"performance.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps(report,ensure_ascii=False))
