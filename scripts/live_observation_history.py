"""V5.29: bounded archive and observed match-clock deltas; never a forecast."""
import json,re,sys
from datetime import datetime,timedelta
from pathlib import Path
from collections import Counter
from live_rate_link import stamp
from live_refresh_snapshot import is_fresh,MAX_AGE_SECONDS
from live_analysis_quality import pair,REQUIRED
from league_config import LEAGUES

COUNT_METRICS=("corners","shots","shotsOnTarget","yellowCards","redCards")
LEAGUE_CODES={code for _,code,_ in LEAGUES}
WINDOWS=(5,10,15)
MAX_OBSERVATIONS=64
MAX_EVENTS=500
def minute(clock):
    if not isinstance(clock,str):return None
    m=re.fullmatch(r"([0-9]{1,2})['′]",clock.strip())
    return int(m.group(1)) if m and 0<=int(m.group(1))<90 else None

def point(row,created):
    try:
        if row["quality"]!="observation_ready" or row["league"] not in LEAGUE_CODES:return None
        ident=row["eventId"];kickoff=stamp(row["kickoff"]);received=stamp(row["receivedAt"])
        if not isinstance(ident,str) or not ident.isascii() or not ident.isdigit() or not kickoff or not received or kickoff>received or not is_fresh(row["receivedAt"],created,MAX_AGE_SECONDS):return None
        names=[row["home"],row["away"]]
        if not all(isinstance(n,str) and n.strip() for n in names) or names[0]==names[1]:return None
        obs=row["observation"];m=minute(obs["clock"]);metrics=obs["metrics"]
        if m is None or obs["state"]!="in" or not pair(obs["score"]):return None
        if not all(pair(metrics[k],k=="possession") for k in REQUIRED):return None
        if abs(sum(metrics["possession"])-100)>2 or any(a>b for a,b in zip(metrics["shotsOnTarget"],metrics["shots"])):return None
        return dict(receivedAt=received.isoformat(),minute=m,score=obs["score"],metrics={k:metrics[k] for k in COUNT_METRICS})
    except (KeyError,TypeError,ValueError,AttributeError):return None

def delta(old,new,target):
    a,b=stamp(old.get("receivedAt")),stamp(new.get("receivedAt"))
    if not a or not b or b<=a:return None
    gap=new["minute"]-old["minute"]
    seconds=(b-a).total_seconds()
    # Do not bridge halftime, added-time/unsupported clock, corrections or gaps.
    if old["minute"]<45<=new["minute"] or abs(gap-target)>1 or abs(seconds/60-gap)>3:return None
    result={}
    for k in ("score",)+COUNT_METRICS:
        before=old["score"] if k=="score" else old["metrics"][k]
        after=new["score"] if k=="score" else new["metrics"][k]
        if not pair(before) or not pair(after) or any(y<x for x,y in zip(before,after)):return None
        result[k]=[y-x for x,y in zip(before,after)]
    return dict(targetMinutes=target,observedMatchMinutes=gap,receiptGapSeconds=round(seconds),fromMinute=old["minute"],toMinute=new["minute"],changes=result)

def build(quality,previous,now):
    created=stamp(quality.get("updatedAt"))
    if not created or created>now or quality.get("mode")!="live_analysis_quality_only" or quality.get("predictionsEnabled") is not False:raise ValueError("quality report")
    if not isinstance(previous,dict):raise ValueError("archive")
    entries={k:v for k,v in previous.items() if isinstance(v,dict) and stamp(v.get("kickoff")) and now-timedelta(days=7)<=stamp(v["kickoff"])<=now}
    accepted=0;reasons=Counter();report=[]
    rows=quality.get("rows",[])
    if not isinstance(rows,list):raise ValueError("rows")
    duplicates=Counter((r.get("league"),r.get("eventId")) for r in rows if isinstance(r,dict))
    for r in rows:
        if not isinstance(r,dict):continue
        ident=(r.get("league"),r.get("eventId"));key=str(ident[0])+":"+str(ident[1])
        p=point(r,created)
        if duplicates[ident]>1 or not p:
            reasons["rejected_observation"]+=1;continue
        entry=entries.get(key)
        identity=dict(league=r["league"],eventId=r["eventId"],home=r["home"],away=r["away"],kickoff=r["kickoff"])
        if entry is None:entry=dict(**identity,points=[])
        if any(entry.get(k)!=v for k,v in identity.items()):
            reasons["identity_conflict"]+=1;continue
        points=entry["points"]
        if points and stamp(p["receivedAt"])<=stamp(points[-1]["receivedAt"]):
            reasons["duplicate_or_old_receipt"]+=1;continue
        if points and p["minute"]<=points[-1]["minute"]:
            reasons["clock_not_advanced"]+=1;continue
        windows={}
        for target in WINDOWS:
            options=[x for x in points if abs(p["minute"]-x["minute"]-target)<=1]
            for old in sorted(options,key=lambda x:abs(p["minute"]-x["minute"]-target)):
                # Reject a window if any intervening cumulative count was corrected.
                chain=[x for x in points if stamp(x["receivedAt"])>=stamp(old["receivedAt"])]+[p]
                fields=("score",)+COUNT_METRICS
                val=lambda x,k:x["score"] if k=="score" else x["metrics"][k]
                if any(any(y<x for x,y in zip(val(a,k),val(b,k))) for a,b in zip(chain,chain[1:]) for k in fields):continue
                d=delta(old,p,target)
                if d is not None:windows[str(target)]=d;break
        entry["points"]=(points+[p])[-MAX_OBSERVATIONS:]
        entries[key]=entry;accepted+=1
        report.append(dict(**identity,receivedAt=p["receivedAt"],minute=p["minute"],observations=len(entry["points"]),windows=windows))
    entries=dict(sorted(entries.items(),key=lambda kv:stamp(kv[1]["kickoff"]),reverse=True)[:MAX_EVENTS])
    return entries,dict(version="5.29",mode="observed_deltas_only",updatedAt=now.isoformat(),sourceUpdatedAt=quality["updatedAt"],sourceTimestampVerified=False,modelCalibrated=False,predictionsEnabled=False,decision="PAS",accepted=accepted,archivedEvents=len(entries),archivedPoints=sum(len(v["points"]) for v in entries.values()),reasons=dict(reasons),windowCounts={str(w):sum(str(w) in r["windows"] for r in report) for w in WINDOWS},rows=report)

def main():
    quality_path,archive_path,report_path=map(Path,sys.argv[1:])
    q=json.loads(quality_path.read_text(encoding="utf-8"))
    previous=json.loads(archive_path.read_text(encoding="utf-8")) if archive_path.exists() else {}
    from results_source_pilot import TR
    entries,report=build(q,previous,datetime.now(TR))
    for p,data in ((archive_path,entries),(report_path,report)):
        p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k!="rows"},ensure_ascii=False))
if __name__=="__main__":main()
