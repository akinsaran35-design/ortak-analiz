"""Normalize received totals odds without inventing prices or accepting duplicates."""
import math
from collections import Counter
from datetime import datetime,timedelta

MAX_AGE=timedelta(minutes=30)
def instant(value):
    t=datetime.fromisoformat(value.replace("Z","+00:00"))
    if t.tzinfo is None:raise ValueError("timezone required")
    return t

def normalize_event(event,league,received):
    if not isinstance(event,dict) or event.get("sport_key")!=league:return None
    try:
        eid,home,away=event["id"],event["home_team"],event["away_team"]
        if not all(isinstance(v,str) and v.strip() for v in (eid,home,away)) or home==away:return None
        kickoff=instant(event["commence_time"])
        if kickoff<=received:return None
    except (ValueError,TypeError,KeyError,AttributeError,OverflowError):return None
    raw=event.get("bookmakers",[])
    if not isinstance(raw,list):return None
    raw=[b for b in raw if isinstance(b,dict)]
    counts=Counter(b.get("key") for b in raw if isinstance(b.get("key"),str))
    books=[]
    for b in raw:
        k=b.get("key")
        if not isinstance(k,str) or not k or counts[k]!=1:continue
        markets=b.get("markets",[])
        if not isinstance(markets,list):continue
        matches=[m for m in markets if isinstance(m,dict) and m.get("key")=="totals"]
        if len(matches)!=1:continue
        m=matches[0]
        stamp=m.get("last_update") or b.get("last_update")
        try:
            if not timedelta(0)<=received-instant(stamp)<=MAX_AGE:continue
        except (ValueError,TypeError,AttributeError,OverflowError):continue
        outcomes=m.get("outcomes",[])
        if not isinstance(outcomes,list):continue
        lines=[]
        for point in (1.5,2.5):
            side=[o for o in outcomes if isinstance(o,dict) and o.get("point")==point and o.get("name") in ("Over","Under")]
            if len(side)!=2 or {o["name"] for o in side}!={"Over","Under"}:continue
            prices={o["name"]:o.get("price") for o in side}
            if not all(type(v) in (int,float) and math.isfinite(v) and v>1 for v in prices.values()):continue
            over,under=prices["Over"],prices["Under"]
            lines.append(dict(point=point,over=over,under=under,marketOverProbability=round((1/over)/(1/over+1/under),6),lastUpdate=stamp))
        if lines:books.append(dict(key=k,name=b.get("title") if isinstance(b.get("title"),str) else k,lines=lines))
    return dict(id=eid,league=league,home=home,away=away,kickoff=kickoff.isoformat(),bookmakers=books) if books else None

def finalize(report,finished):
    """Timestamp actual completion; omit events/lines expired during collection."""
    ids=Counter(e["id"] for e in report["events"])
    if any(n!=1 for n in ids.values()):report["errors"].append("duplicate_event_identity")
    events=[]
    for e in report["events"]:
        if ids[e["id"]]!=1 or instant(e["kickoff"])<=finished:continue
        books=[]
        for b in e["bookmakers"]:
            lines=[l for l in b["lines"] if timedelta(0)<=finished-instant(l["lastUpdate"])<=MAX_AGE]
            if lines:books.append(dict(b,lines=lines))
        if books:events.append(dict(e,bookmakers=books))
    report.update(updatedAt=finished.isoformat(),events=events,eventCount=len(events))
    return report
