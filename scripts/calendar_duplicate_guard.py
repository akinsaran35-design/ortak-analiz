"""Suppress new duplicate forecast records only when stored pre-kickoff evidence links dates."""
import json
from collections import defaultdict
from datetime import date,timedelta
from pathlib import Path
from archive_calendar_audit import stamp,TR
from league_config import FIXTURE_CODES

def blocked_dates(ledger,records,kind,now):
    existing=defaultdict(list)
    for r in records.values():
        if kind=="performance":
            league=FIXTURE_CODES.get(r["league"])
            h,a=r["match"].split(" – ")
        else:
            league,h,a=r["league"],r["home"],r["away"]
        existing[(league,h,a,r["date"])].append(r)
    observations=defaultdict(list)
    for e in ledger.values():
        if e.get("archive")==kind:
            observations[(e["league"],e["home"],e["away"],e["archivedDate"],e["recordedAt"])].append(e)
    blocked=set()
    for (league,h,a,old,recorded),rows in observations.items():
        original=existing.get((league,h,a,old),[])
        if len(original)!=1 or original[0]["recordedAt"]!=recorded: continue
        for e in rows:
            try:
                new=e["corroboratedDate"]
                olddate,newdate=date.fromisoformat(old),date.fromisoformat(new)
                kickoff=stamp(e["kickoff"])
                observed=stamp(e["observedAt"])
                captured=stamp(recorded)
                if e["status"]!="review_pending" or not e["eventId"]: continue
                if not 0<abs((newdate-olddate).days)<=2: continue
                if kickoff.astimezone(TR).date()!=newdate or captured.astimezone(TR).date()>=newdate: continue
                if not captured<=observed<kickoff or observed>now: continue
                blocked.add((league,h,a,new))
            except (KeyError,TypeError,ValueError,AttributeError):
                continue
    return blocked

def load_guard(root,records,kind,now):
    p=Path(root)/"archive_calendar_evidence.json"
    if not p.exists(): return set()
    ledger=json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(ledger,dict): raise ValueError("invalid calendar ledger")
    return blocked_dates(ledger,records,kind,now)
