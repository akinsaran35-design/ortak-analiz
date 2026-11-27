"""V5.48: future-only research capture window and canonical duplicate protection."""
from datetime import timedelta,date
from collections import Counter
from nine_league_results_pilot import result_key
from league_config import LEAGUES

HORIZON_DAYS=14
SPORTS={code:sport for _,code,sport in LEAGUES}

def identity(league,day,home,away):
    sport=SPORTS[league]
    h,a=result_key(home,league,sport),result_key(away,league,sport)
    if not h or not a or h==a:raise ValueError("invalid team identity")
    return league,day,h,a

def existing_identities(records):
    out=set()
    for r in records.values():
        if r["league"] in SPORTS:
            out.add(identity(r["league"],r["date"],r["home"],r["away"]))
    return out

def capture_status(league,day,home,away,score,today,existing,blocked):
    if score is not None or not today<day<=today+timedelta(days=HORIZON_DAYS):return "outside_future_window"
    k=identity(league,day.isoformat(),home,away)
    if k in existing:return "already_recorded"
    if (league,home,away,day.isoformat()) in blocked:return "calendar_blocked"
    return "eligible"
