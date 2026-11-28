"""Preserve last successful odds evidence separately; never serve archive as current odds."""
import json,math
from pathlib import Path
from datetime import timedelta
from odds_snapshot_validation import instant
from league_config import ODDS_CODES

ARCHIVE=Path("odds_last_good.json")
STATUS=Path("odds_continuity.json")
LEAGUES=list(ODDS_CODES.values())

def valid(snapshot,now):
    try:
        if not isinstance(snapshot,dict) or snapshot.get("source")!="The Odds API" or snapshot.get("region")!="uk" or snapshot.get("market")!="totals" or snapshot.get("errors")!=[] or snapshot.get("configuredLeagues")!=LEAGUES:return False
        stamp=instant(snapshot["updatedAt"])
        if stamp>now:return False
        queried=snapshot["queriedLeagues"];inactive=snapshot["inactiveLeagues"]
        if not isinstance(queried,list) or not isinstance(inactive,list) or len(set(queried+inactive))!=len(queried+inactive) or set(queried+inactive)!=set(LEAGUES):return False
        events=snapshot["events"]
        if not isinstance(events,list) or not events or snapshot["eventCount"]!=len(events):return False
        ids=set()
        for e in events:
            if not all(isinstance(e[k],str) and e[k] for k in ("id","home","away")) or e["home"]==e["away"] or e["id"] in ids or e["league"] not in queried or instant(e["kickoff"])<=stamp:return False
            ids.add(e["id"])
            books=e["bookmakers"];keys=set()
            if not isinstance(books,list) or not books:return False
            for b in books:
                k=b["key"]
                if not isinstance(k,str) or not k or k in keys:return False
                keys.add(k);points=set()
                if not isinstance(b["lines"],list) or not b["lines"]:return False
                for l in b["lines"]:
                    p=l["point"]
                    if p not in (1.5,2.5) or p in points:return False
                    points.add(p)
                    if not all(type(l[x]) in (float,int) and math.isfinite(l[x]) and l[x]>1 for x in ("over","under")) or not timedelta(0)<=stamp-instant(l["lastUpdate"])<=timedelta(minutes=30):return False
        return True
    except (KeyError,TypeError,ValueError,AttributeError,OverflowError):return False

def read(path):
    try:return json.loads(path.read_text(encoding="utf-8"))
    except (OSError,ValueError):return None

def write(path,doc):
    tmp=path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    tmp.replace(path)

def record(current,previous,now,reason,live_balance=None,errors=None):
    old=read(ARCHIVE)
    candidates=[s for s in (old,previous,current) if valid(s,now)]
    best=max(candidates,key=lambda s:instant(s["updatedAt"])) if candidates else None
    if best is not None and best!=old:write(ARCHIVE,best)
    fresh=valid(current,now) and now-instant(current["updatedAt"])<=timedelta(minutes=30)
    normal=fresh and reason in ("collected","recent_cache")
    balance=live_balance if type(live_balance) is int and live_balance>=0 else None
    status=dict(version="6.94",updatedAt=now.isoformat(),mode="normal" if normal else "fallback",
        reason=reason,currentOddsAt=current.get("updatedAt") if isinstance(current,dict) else None,
        currentOddsUsable=normal,liveRemainingCredits=balance,errors=list(errors or []),
        lastGoodAt=best["updatedAt"] if best else None,lastGoodEventCount=best["eventCount"] if best else None,
        archiveUsedForCurrentOdds=False,independentAnalysisMayContinue=True,productionEnabled=False)
    write(STATUS,status)
    print("ODDS_CONTINUITY_694",json.dumps(status))
    return status
