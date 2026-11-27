"""Bounded, live-only source snapshot. Observation timestamps are receipt times."""
import json
from datetime import datetime,timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from scoreboard_snapshot import build as board
from results_source_pilot import read,TR
from live_statistics_pilot import BASE,SOURCES,parse_summary,select_candidates

EXTRA_CODES=("eng.3","ger.2","esp.2","ita.2","fra.2","den.1","nor.1","jpn.1","aus.1","ind.1","rsa.1","uefa.europa","eng.4","sco.1","swe.1","gre.1","arg.1","uefa.champions","afc.champions","ned.2","sco.2")
LIVE_SOURCES={**SOURCES,**{c:(None,c) for c in EXTRA_CODES}}
def live_board(now,reader,query_date):
    return board(now,reader=reader,query_date=query_date,extra_codes=EXTRA_CODES)

MAX_EVENTS=48
MAX_WORKERS=8
MAX_AGE_SECONDS=120

def is_fresh(received,now,max_age=MAX_AGE_SECONDS):
    try:
        stamp=datetime.fromisoformat(received)
        if stamp.tzinfo is None or now.tzinfo is None:return False
        return 0<=(now-stamp).total_seconds()<=max_age
    except (TypeError,ValueError):return False

def build(now,reader=read,board_reader=live_board,clock=lambda:datetime.now(TR)):
    day=now.astimezone(TR).date()
    candidates=[];issues=[]
    for date in (day,day-timedelta(days=1)):
        snapshot=board_reader(now,reader=reader,query_date=date.isoformat())
        for group in snapshot["groups"]:
            if group["error"] is not None or group["invalid"]:
                issues.append(dict(date=date.isoformat(),league=group["league"],error=group["error"],invalid=group["invalid"]))
                continue
            candidates.extend(dict(row,league=group["league"]) for row in group["rows"] if row["state"]=="in")
    chosen=select_candidates(candidates,MAX_EVENTS)
    def fetch(row):
        url=BASE+LIVE_SOURCES[row["league"]][1]+"/summary?event="+row["eventId"]
        result={k:row[k] for k in ("league","eventId","home","away","kickoff")}
        result.update(source=url,receivedAt=None,observation=None,error=None)
        try:
            raw=reader(url)
            received=clock()
            observation=parse_summary(json.loads(raw),row)
            if observation["state"]!="in":raise ValueError("no longer in progress")
            result.update(receivedAt=received.isoformat(),observation=observation)
        except (OSError,ValueError,TypeError,KeyError,AttributeError) as exc:
            result["error"]=type(exc).__name__
        return result
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:rows=list(pool.map(fetch,chosen))
    end=clock()
    fresh=sum(bool(r["observation"]) and is_fresh(r["receivedAt"],end) for r in rows)
    return dict(version="5.77",configuredCompetitions=len(LIVE_SOURCES),mode="live_snapshot_only",source="ESPN",startedAt=now.isoformat(),updatedAt=end.isoformat(),maxAgeSeconds=MAX_AGE_SECONDS,sourceTimestampVerified=False,rows=rows,sourceIssues=issues,detected=len(candidates),capacity=MAX_EVENTS,workers=MAX_WORKERS,unrequested=len(candidates)-len(rows),requested=len(rows),freshAtBuild=fresh,realTime=False,predictionsEnabled=False,usedForSettlement=False,decision="PAS")

def main():
    report=build(datetime.now(TR))
    Path("live_refresh_snapshot.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k!="rows"},ensure_ascii=False))
    if len(report["sourceIssues"])>=2*len(LIVE_SOURCES):raise SystemExit("No valid scoreboard groups")
    if report["requested"] and not report["freshAtBuild"]:raise SystemExit("No verified live summary")
if __name__=="__main__":main()
