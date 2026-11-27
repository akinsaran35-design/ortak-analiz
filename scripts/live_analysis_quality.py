"""Live analysis input quality report; never emit uncalibrated probabilities."""
import json
import math
from collections import Counter
from datetime import datetime
from pathlib import Path
from live_refresh_snapshot import is_fresh,MAX_AGE_SECONDS,MAX_EVENTS,LIVE_SOURCES
from live_statistics_pilot import BASE
from results_source_pilot import TR

REQUIRED=("corners","shots","shotsOnTarget","yellowCards","redCards","possession")

def pair(value,percentage=False):
    if not isinstance(value,list) or len(value)!=2:return False
    if any(type(v) not in (int,float) or not math.isfinite(v) or v<0 for v in value):return False
    return all(v<=100 for v in value) if percentage else all(type(v) is int for v in value)

def assess(row,now):
    if row.get("error") or not isinstance(row.get("observation"),dict):return "source_error"
    if not is_fresh(row.get("receivedAt"),now,MAX_AGE_SECONDS):return "stale_receipt"
    league=row.get("league");event=row.get("eventId")
    if league not in LIVE_SOURCES or not isinstance(event,str) or not event.isascii() or not event.isdigit():return "invalid_identity"
    if row.get("source")!=BASE+LIVE_SOURCES[league][1]+"/summary?event="+event:return "invalid_identity"
    try:
        start=datetime.fromisoformat(row["kickoff"])
        if start.tzinfo is None or start>now:return "invalid_identity"
    except (ValueError,KeyError,TypeError):return "invalid_identity"
    home,away=row.get("home"),row.get("away")
    if not all(isinstance(x,str) and x.strip() for x in (home,away)) or home==away:return "invalid_identity"
    obs=row["observation"]
    if obs.get("state")!="in":return "not_in_progress"
    if not pair(obs.get("score")) or not isinstance(obs.get("clock"),str) or not obs["clock"].strip():return "incomplete_score_clock"
    metrics=obs.get("metrics")
    if not isinstance(metrics,dict) or not all(k in metrics for k in REQUIRED):return "incomplete_metrics"
    if not all(pair(metrics[k],k=="possession") for k in REQUIRED):return "invalid_metrics"
    if abs(sum(metrics["possession"])-100)>2:return "conflicting_metrics"
    if any(a>b for a,b in zip(metrics["shotsOnTarget"],metrics["shots"])):return "conflicting_metrics"
    return "observation_ready"

def build(snapshot,now):
    rows=snapshot.get("rows")
    if (snapshot.get("mode")!="live_snapshot_only" or snapshot.get("source")!="ESPN"
        or not isinstance(rows,list) or len(rows)>MAX_EVENTS or any(not isinstance(r,dict) for r in rows)):
        raise ValueError("snapshot schema")
    counts=Counter((r.get("league"),r.get("eventId")) for r in rows)
    report=[]
    for row in rows:
        key=(row.get("league"),row.get("eventId"))
        reason="duplicate_identity" if counts[key]>1 else assess(row,now)
        report.append(dict(league=key[0],eventId=key[1],home=row.get("home"),away=row.get("away"),kickoff=row.get("kickoff"),receivedAt=row.get("receivedAt"),quality=reason,observation=row["observation"] if reason=="observation_ready" else None,prediction=None))
    return dict(version="5.15",mode="live_analysis_quality_only",updatedAt=now.isoformat(),sourceUpdatedAt=snapshot.get("updatedAt"),sourceTimestampVerified=False,modelCalibrated=False,predictionsEnabled=False,decision="PAS",counts=dict(Counter(r["quality"] for r in report)),rows=report)

def main():
    snapshot=json.loads(Path("live_refresh_snapshot.json").read_text(encoding="utf-8"))
    report=build(snapshot,datetime.now(TR))
    Path("live_analysis_quality.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k!="rows"},ensure_ascii=False))
if __name__=="__main__":main()
