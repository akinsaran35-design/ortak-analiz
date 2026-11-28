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

def objects(value):
    return [x for x in value if isinstance(x,dict)] if isinstance(value,list) else []

def build(snapshot,movement,now):
    snapshot=snapshot if isinstance(snapshot,dict) else {}
    movement=movement if isinstance(movement,dict) else {}
    valid_source=snapshot.get("source")=="The Odds API" and snapshot.get("region")=="uk" and snapshot.get("errors")==[]
    snapshot_fresh=valid_source and fresh(snapshot.get("updatedAt"),now)
    rows=[]
    events=snapshot.get("events",[])
    if not isinstance(events,list):events=[]
    from collections import Counter
    counts=Counter(str(e.get("id")) for e in events if isinstance(e,dict))
    for event in objects(events):
        ident=event.get("id")
        if not isinstance(ident,str) or not ident or counts[ident]!=1:continue
        try:
            if instant(event["kickoff"])<=now:continue
        except (ValueError,TypeError,KeyError,AttributeError):continue
        books={}
        for book in objects(event.get("bookmakers")):
            key=book.get("key")
            if not isinstance(key,str) or not key:continue
            for line in objects(book.get("lines")):
                if line.get("point")!=2.5 or not price(line.get("over")) or not price(line.get("under")):continue
                if not fresh(line.get("lastUpdate"),now):continue
                if key in books:
                    books[key]=None
                    continue
                books[key]=dict(lastUpdate=line["lastUpdate"])
        count=sum(v is not None for v in books.values())
        if snapshot_fresh and count>=3:
            rows.append(dict(eventId=ident,league=event.get("league"),freshBookmakers=count))
    moves=objects(movement.get("markets"))
    movement_fresh=movement.get("mode")=="research_only" and movement.get("errors")==[] and fresh(movement.get("updatedAt"),now)
    return dict(version="6.4",updatedAt=now.isoformat(),mode="research_only",
        odds=dict(status="observed" if rows else "stale_or_unavailable" if not snapshot_fresh else "insufficient_coverage",snapshotAt=snapshot.get("updatedAt"),archivedEvents=len(events),freshEvents=len(rows),rows=rows,region="uk",remainingCredits=snapshot.get("remainingCredits")),
        movement=dict(status="report_available" if movement_fresh and moves else "no_fresh_evidence",reportAt=movement.get("updatedAt"),reportedMarkets=len(moves) if movement_fresh and isinstance(moves,list) else 0),
        volume=dict(status="source_unavailable",matchedAmount=None,currency=None,amountTRY=None,worldwideTotal=None,reason="Odds and price movement do not establish wager volume."),
        productionEnabled=False,predictionsEnabled=False)

def coverage(snapshot,archive,now):
    """Inventory and freshness are different. No requests or inferred prices."""
    from collections import Counter
    snapshot=snapshot if isinstance(snapshot,dict) else {}
    archive=archive if isinstance(archive,dict) else {}
    source_ok=(snapshot.get("source")=="The Odds API" and snapshot.get("region")=="uk"
        and snapshot.get("market")=="totals" and snapshot.get("errors")==[])
    current=source_ok and fresh(snapshot.get("updatedAt"),now)
    events=objects(snapshot.get("events"))
    ids=Counter(e.get("id") for e in events if isinstance(e.get("id"),str))
    markets={}
    for point,market in ((1.5,"over15"),(2.5,"over25")):
        any_count=ready_count=future_fresh=0
        for e in events if source_ok else []:
            ident=e.get("id")
            if not isinstance(ident,str) or not ident or ids[ident]!=1:continue
            books=objects(e.get("bookmakers"))
            keys=Counter(b.get("key") for b in books if isinstance(b.get("key"),str))
            observed=fresh_count=0
            for b in books:
                k=b.get("key")
                if not isinstance(k,str) or not k or keys[k]!=1:continue
                lines=[l for l in objects(b.get("lines")) if l.get("point")==point]
                if len(lines)!=1:continue
                l=lines[0]
                if not price(l.get("over")) or not price(l.get("under")):continue
                try:instant(l["lastUpdate"])
                except (ValueError,TypeError,KeyError,AttributeError,OverflowError):continue
                observed+=1
                fresh_count+=int(fresh(l.get("lastUpdate"),now))
            any_count+=int(observed>=1)
            ready_count+=int(observed>=3)
            try:future=instant(e["kickoff"])>now
            except (ValueError,TypeError,KeyError,AttributeError,OverflowError):future=False
            future_fresh+=int(current and future and fresh_count>=3)
        markets[market]=dict(sourceScope="totals",observedEvents=any_count,observedThreeBookEvents=ready_count,
            freshFutureThreeBookEvents=future_fresh,status="observed" if future_fresh else "stale_or_invalid_snapshot" if not current else "insufficient_coverage")
    markets["btts"]=dict(sourceScope="not_requested",observedEvents=None,observedThreeBookEvents=None,
        freshFutureThreeBookEvents=None,status="not_requested")
    records=archive.get("records",{})
    archive_ok=archive.get("mode")=="research_only" and isinstance(records,dict)
    historic=Counter(v.get("market") for v in records.values() if isinstance(v,dict) and v.get("market") in ("over15","btts")) if archive_ok else Counter()
    return dict(snapshotAt=snapshot.get("updatedAt"),snapshotFresh=current,sourceAccepted=source_ok,archivedEvents=len(events),
        markets=markets,historicalExtraMarketArchive=dict(updatedAt=archive.get("updatedAt") if archive_ok else None,
            recordCounts={m:historic[m] for m in ("over15","btts")},recordUnit="event_market_bookmaker",usedAsCurrentEvidence=False),
        remainingCreditsAtSnapshot=snapshot.get("remainingCredits"),additionalApiRequests=0,extraMarketCollectionEnabled=False,
        productionEnabled=False)

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
    assert build(None,None,now)["odds"]["freshEvents"]==0
    assert build(dict(snapshot,events=[dict(event,bookmakers=None)]),{},now)["odds"]["freshEvents"]==0
    assert build(dict(snapshot,events=[dict(event,bookmakers=[None,dict(key="a",lines=None)])]),{},now)["odds"]["freshEvents"]==0
    assert build(snapshot,dict(mode="research_only",errors=[],updatedAt=stamp,markets={"unexpected":1}),now)["movement"]["status"]=="no_fresh_evidence"
    assert build(snapshot,dict(mode="research_only",errors=[],updatedAt=stamp,markets=[None,False]),now)["movement"]["reportedMarkets"]==0
    print("Market evidence self-tests passed")

if __name__=="__main__":
    if "--self-test" in sys.argv:self_test()
    else:
        snapshot=json.loads(Path("odds.json").read_text())
        movement=json.loads(Path("market_movement.json").read_text())
        report=build(snapshot,movement,datetime.now(timezone.utc))
        archive_path=Path("extra_market_archive.json")
        try:archive=json.loads(archive_path.read_text()) if archive_path.exists() else {}
        except (OSError,ValueError):archive={}
        report["marketCoverage"]=coverage(snapshot,archive,datetime.now(timezone.utc))
        report["coverageVersion"]="6.75"
        Path("market_data_health.json").write_text(json.dumps(report,ensure_ascii=False,indent=2))
        print(json.dumps({k:v for k,v in report.items() if k!="odds"}))
        print("Odds health:",report["odds"]["status"],report["odds"]["freshEvents"])
