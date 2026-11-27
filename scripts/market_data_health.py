"""Read-only market evidence and readiness. No trades, selections, or inferred money."""
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

MAX_AGE=1800

def instant(value):
    stamp=datetime.fromisoformat(value.replace("Z","+00:00"))
    if stamp.tzinfo is None:
        raise ValueError("timezone required")
    return stamp

def fresh(value,now):
    try:return 0 <= (now-instant(value)).total_seconds() <= MAX_AGE
    except (ValueError,TypeError,AttributeError,OverflowError):return False

def price(value):
    return type(value) in (int,float) and math.isfinite(value) and value>1

def build(snapshot,movement,now):
    valid_source=snapshot.get("source")=="The Odds API" and snapshot.get("region")=="uk" and snapshot.get("errors")==[]
    snapshot_fresh=valid_source and fresh(snapshot.get("updatedAt"),now)
    rows=[]
    events=snapshot.get("events",[])
    if not isinstance(events,list):events=[]
    from collections import Counter
    counts=Counter(str(e.get("id")) for e in events if isinstance(e,dict))
    for event in events:
        if not isinstance(event,dict):continue
        ident=event.get("id")
        if not isinstance(ident,str) or not ident or counts[ident]!=1:continue
        try:
            if instant(event["kickoff"])<=now:continue
        except (ValueError,TypeError,KeyError,AttributeError):continue
        books={}
        for book in event.get("bookmakers",[]):
            key=book.get("key")
            if not isinstance(key,str) or not key:continue
            for line in book.get("lines",[]):
                if line.get("point")!=2.5 or not price(line.get("over")) or not price(line.get("under")):continue
                if not fresh(line.get("lastUpdate"),now):continue
                if key in books:
                    books[key]=None
                    continue
                books[key]=dict(lastUpdate=line["lastUpdate"])
        count=sum(v is not None for v in books.values())
        if snapshot_fresh and count>=3:
            rows.append(dict(eventId=ident,league=event.get("league"),freshBookmakers=count))
    moves=movement.get("markets",[])
    movement_fresh=movement.get("mode")=="research_only" and movement.get("errors")==[] and fresh(movement.get("updatedAt"),now)
    return dict(version="6.0",updatedAt=now.isoformat(),mode="research_only",
        odds=dict(status="observed" if rows else "stale_or_unavailable" if not snapshot_fresh else "insufficient_coverage",snapshotAt=snapshot.get("updatedAt"),archivedEvents=len(events),freshEvents=len(rows),rows=rows,region="uk",remainingCredits=snapshot.get("remainingCredits")),
        movement=dict(status="report_available" if movement_fresh and moves else "no_fresh_evidence",reportAt=movement.get("updatedAt"),reportedMarkets=len(moves) if movement_fresh and isinstance(moves,list) else 0),
        volume=dict(status="source_unavailable",matchedAmount=None,currency=None,amountTRY=None,worldwideTotal=None,reason="Odds and price movement do not establish wager volume."),
        productionEnabled=False,predictionsEnabled=False)

def self_test():
    now=datetime(2026,11,27,12,tzinfo=timezone.utc)
    stamp=now.isoformat()
    lines=[dict(point=2.5,over=1.9,under=2.0,lastUpdate=stamp)]
    event=dict(id="a",league="example",kickoff="2026-11-28T00:00:00+00:00",bookmakers=[dict(key=k,lines=lines) for k in ("a","b","c")])
    snapshot=dict(source="The Odds API",region="uk",errors=[],updatedAt=stamp,events=[event])
    good=build(snapshot,{},now)
    assert good["odds"]["freshEvents"]==1 and good["volume"]["amountTRY"] is None
    assert not good["productionEnabled"]
    assert build(dict(snapshot,updatedAt="2026-11-26T00:00:00Z"),{},now)["odds"]["freshEvents"]==0
    assert build(dict(snapshot,region="tr"),{},now)["odds"]["freshEvents"]==0
    assert build(dict(snapshot,events=[event,event]),{},now)["odds"]["freshEvents"]==0
    assert build(dict(snapshot,events=[dict(event,bookmakers=event["bookmakers"][:2])]),{},now)["odds"]["freshEvents"]==0
    assert build(dict(snapshot,events=[dict(event,kickoff=stamp)]),{},now)["odds"]["freshEvents"]==0
    assert build(snapshot,dict(mode="research_only",errors=[],updatedAt=stamp,markets=[]),now)["movement"]["status"]=="no_fresh_evidence"
    print("Market evidence self-tests passed")

if __name__=="__main__":
    if "--self-test" in sys.argv:self_test()
    else:
        snapshot=json.loads(Path("odds.json").read_text())
        movement=json.loads(Path("market_movement.json").read_text())
        report=build(snapshot,movement,datetime.now(timezone.utc))
        Path("market_data_health.json").write_text(json.dumps(report,ensure_ascii=False,indent=2))
        print(json.dumps({k:v for k,v in report.items() if k!="odds"}))
        print("Odds health:",report["odds"]["status"],report["odds"]["freshEvents"])
