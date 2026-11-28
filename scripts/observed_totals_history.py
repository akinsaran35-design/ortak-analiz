"""V6.63 exact price observations from existing UK totals snapshot. No new API calls."""
import json,math
from collections import Counter
from datetime import datetime,timezone,timedelta
from pathlib import Path
from statistics import median
from collections import defaultdict

ARCHIVE=Path("observed_totals_history.json")
REPORT=Path("observed_totals_report.json")

def stamp(s):
    t=datetime.fromisoformat(s.replace("Z","+00:00"))
    if t.tzinfo is None:raise ValueError("naive timestamp")
    return t

def price(x):
    return type(x) in (int,float) and math.isfinite(x) and x>1

def key(e,b,p):
    return json.dumps([e["id"],e["league"],e["home"],e["away"],stamp(e["kickoff"]).isoformat(),b["key"],p],ensure_ascii=False,separators=(",",":"))

def collect(archive,odds,now):
    if archive.get("version")!="6.63" or not isinstance(archive.get("records"),dict):raise ValueError("archive schema")
    records=archive["records"]
    observed=stamp(odds["updatedAt"])
    if odds.get("source")!="The Odds API" or odds.get("region")!="uk" or odds.get("market")!="totals" or odds.get("errors")!=[] or not timedelta(0)<=now-observed<=timedelta(minutes=30):
        return dict(status="snapshot_unavailable",added=0,events=[])
    events=odds["events"]
    ids=Counter(e["id"] for e in events)
    groups=defaultdict(list);added=0
    for e in events:
        if ids[e["id"]]!=1 or stamp(e["kickoff"])<=observed:continue
        books=Counter(b["key"] for b in e["bookmakers"])
        for b in e["bookmakers"]:
            if books[b["key"]]!=1:continue
            counts=Counter(l["point"] for l in b["lines"])
            for l in b["lines"]:
                p=l["point"]
                if p not in (1.5,2.5) or counts[p]!=1 or not price(l["over"]) or not price(l["under"]):continue
                try:t=stamp(l["lastUpdate"])
                except (ValueError,TypeError,AttributeError):continue
                if not timedelta(0)<=observed-t<=timedelta(minutes=30):continue
                k=key(e,b,p)
                r=records.setdefault(k,dict(eventId=e["id"],league=e["league"],home=e["home"],away=e["away"],kickoff=e["kickoff"],bookmaker=b["key"],point=p,history=[]))
                h=r["history"]
                item=dict(observedAt=odds["updatedAt"],lastUpdate=l["lastUpdate"],over=l["over"],under=l["under"])
                same=[x for x in h if stamp(x["lastUpdate"])==t]
                if same and any((x["over"],x["under"])!=(item["over"],item["under"]) for x in same):
                    continue
                if not same:
                    if h and t<=stamp(h[-1]["lastUpdate"]):continue
                    h.append(item);added+=1
                if not h or stamp(h[-1]["lastUpdate"])!=t:continue
                first=h[0]
                groups[(e["id"],p)].append(dict(bookmaker=b["key"],firstObserved=first["over"],current=l["over"],firstObservedAt=first["observedAt"],currentLastUpdate=l["lastUpdate"],dropPct=100*(first["over"]-l["over"])/first["over"] if len(h)>=2 else None))
    rows=[]
    for (eid,p),books in sorted(groups.items()):
        comparable=[b for b in books if b["dropPct"] is not None]
        rows.append(dict(eventId=eid,point=p,books=books,currentBookCount=len(books),comparableBookCount=len(comparable),
            firstObservedMedian=median(b["firstObserved"] for b in comparable) if len(comparable)>=3 else None,
            currentComparableMedian=median(b["current"] for b in comparable) if len(comparable)>=3 else None,
            medianDropPct=median(b["dropPct"] for b in comparable) if len(comparable)>=3 else None))
    return dict(status="observed",added=added,events=rows)

def main():
    now=datetime.now(timezone.utc)
    archive=json.loads(ARCHIVE.read_text()) if ARCHIVE.exists() else dict(version="6.63",records={})
    odds=json.loads(Path("odds.json").read_text())
    report=collect(archive,odds,now)
    report.update(version="6.63",mode="research_only",oddsUpdatedAt=odds["updatedAt"],updatedAt=now.isoformat(),firstObservedIsOpening=False,realBettingEnabled=False)
    ARCHIVE.write_text(json.dumps(archive,ensure_ascii=False,separators=(",",":"))+"\n")
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    print("OBSERVED_TOTALS_663",json.dumps({**{k:v for k,v in report.items() if k!="events"},"markets":len(report["events"]),"comparableMarkets":sum(x["comparableBookCount"]>=3 for x in report["events"])}))
if __name__=="__main__":main()
