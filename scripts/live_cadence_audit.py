"""V5.30: audit actual live collection cadence without inventing observations."""
import json,math,sys
from pathlib import Path
from datetime import datetime,timedelta
from collections import Counter
from live_rate_link import stamp

RETENTION=timedelta(days=7)
MAX_RUNS=1000
def build(snapshot,previous,now):
    if snapshot.get("mode")!="live_snapshot_only" or snapshot.get("source")!="ESPN":raise ValueError("snapshot provenance")
    started=stamp(snapshot.get("startedAt"));ended=stamp(snapshot.get("updatedAt"))
    if not started or not ended or not started<=ended<=now:raise ValueError("snapshot timing")
    fields=("detected","requested","freshAtBuild")
    values={k:snapshot.get(k) for k in fields}
    if any(type(v) is not int or v<0 for v in values.values()) or not values["freshAtBuild"]<=values["requested"]<=values["detected"]:raise ValueError("snapshot counts")
    if not isinstance(snapshot.get("sourceIssues"),list) or not isinstance(snapshot.get("rows"),list) or len(snapshot["rows"])!=values["requested"]:raise ValueError("snapshot rows")
    if not isinstance(previous,list):raise ValueError("archive")
    row=dict(startedAt=started.isoformat(),endedAt=ended.isoformat(),**values,sourceIssues=len(snapshot["sourceIssues"]))
    entries={}
    for item in previous:
        if not isinstance(item,dict):continue
        a,b=stamp(item.get("startedAt")),stamp(item.get("endedAt"))
        if a and b and now-RETENTION<=a<=b<=now and all(type(item.get(k)) is int and item[k]>=0 for k in (*fields,"sourceIssues")):
            entries[a]=item
    if started>=now-RETENTION:
        if started in entries and entries[started]!=row:raise ValueError("conflicting run")
        entries[started]=row
    history=[v for _,v in sorted(entries.items())][-MAX_RUNS:]
    gaps=[]
    for a,b in zip(history,history[1:]):
        # Overnight inactivity is not necessarily a missed scheduled run.
        minutes=(stamp(b["startedAt"])-stamp(a["startedAt"])).total_seconds()/60
        gaps.append(minutes)
    active_gaps=[x for x in gaps if x<=180]
    def percentile(xs,p):
        return round(sorted(xs)[max(0,math.ceil(len(xs)*p)-1)],2) if xs else None
    status=Counter("source_issues" if x["sourceIssues"] else "no_live_detected" if not x["detected"] else "no_fresh_summary" if not x["freshAtBuild"] else "partial_observation" if x["freshAtBuild"]<x["detected"] else "fresh_observation" for x in history)
    return history,dict(version="5.30",mode="collection_cadence_audit_only",updatedAt=now.isoformat(),scheduledIntervalMinutes=15,scheduleGuaranteed=False,sourceTimestampVerified=False,predictionsEnabled=False,decision="PAS",runs=len(history),counts=dict(status),actualGapCount=len(gaps),gapsOver180Minutes=sum(g>180 for g in gaps),within180Minutes=dict(sample=len(active_gaps),median=percentile(active_gaps,.5),p90=percentile(active_gaps,.9),max=round(max(active_gaps),2) if active_gaps else None,within5=sum(g<=6 for g in active_gaps),within10=sum(g<=11 for g in active_gaps),within15=sum(g<=16 for g in active_gaps)),latestRun=row)

def main():
    from results_source_pilot import TR
    source,archive,report=map(Path,sys.argv[1:])
    snapshot=json.loads(source.read_text(encoding="utf-8"))
    prior=json.loads(archive.read_text(encoding="utf-8")) if archive.exists() else []
    history,result=build(snapshot,prior,datetime.now(TR))
    for p,value in ((archive,history),(report,result)):
        p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False))
if __name__=="__main__":main()
