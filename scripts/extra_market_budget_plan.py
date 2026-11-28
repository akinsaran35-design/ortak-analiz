"""V6.86 read-only capacity planning. Never authorizes or performs API requests."""
import json
from datetime import datetime,date,time,timedelta,timezone
from pathlib import Path
from league_config import ODDS_CODES

RESERVE=20
EXTRA_COST_CAP=2
MAX_EXTRA_EVENTS=3
MAX_SNAPSHOT_AGE=timedelta(minutes=30)
BASE_SLOTS=((5,0),(15,0))
WEEKEND_SLOTS=((8,10),(11,10),(13,10),(18,10))
EXPECTED_CRONS={"0 5,15 * * *","10 8,11,13,18 * * 6,0"}

def schedule_matches(workflow):
    import re
    # Fail closed if the scheduled workflow changes without updating the budget.
    return set(re.findall(r"^\s*- cron: '([^']+)'\s*$",workflow,re.M))==EXPECTED_CRONS

def utc(value):
    t=datetime.fromisoformat(value.replace("Z","+00:00"))
    if t.tzinfo is None:raise ValueError("timezone required")
    return t.astimezone(timezone.utc)

def scheduled_slots(after):
    """Conservatively count all remaining scheduled runs in the snapshot UTC month."""
    start=after.date()
    end=date(start.year+(start.month==12),1 if start.month==12 else start.month+1,1)
    slots=[]
    for offset in range((end-start).days):
        day=start+timedelta(days=offset)
        times=BASE_SLOTS+(WEEKEND_SLOTS if day.weekday()>=5 else ())
        for h,m in sorted(times):
            stamp=datetime.combine(day,time(h,m),timezone.utc)
            if stamp>after:slots.append(stamp)
    return slots

def plan(snapshot,now,workflow):
    now=now.astimezone(timezone.utc)
    report=dict(version="6.86",mode="read_only_budget_planning",updatedAt=now.isoformat(),
        additionalApiRequests=0,collectionEnabled=False,liveQuotaVerificationRequired=True,
        scheduledRunsOnly=True,unscheduledRunsNotReserved=True,resetNotAssumedVerified=True,
        emergencyReserve=RESERVE,maximumCostPerExtraEvent=EXTRA_COST_CAP,
        remainingCreditsAtSnapshot=None,snapshotAt=None,snapshotFresh=False,
        scheduledRunsRemaining=None,baseCreditsReserved=None,totalCreditsReserved=None,
        reserveShortfall=None,theoreticalExtraEventCapacity=None,status="invalid_snapshot")
    if not schedule_matches(workflow):
        report["status"]="schedule_changed";return report
    if not isinstance(snapshot,dict):return report
    leagues=list(ODDS_CODES.values())
    if (snapshot.get("source")!="The Odds API" or snapshot.get("region")!="uk"
        or snapshot.get("market")!="totals" or snapshot.get("errors")!=[]
        or snapshot.get("configuredLeagues")!=leagues):return report
    balance=snapshot.get("remainingCredits")
    if type(balance) is not int or balance<0:return report
    try:stamp=utc(snapshot["updatedAt"])
    except (KeyError,TypeError,ValueError,AttributeError,OverflowError):return report
    if stamp>now:return report
    slots=scheduled_slots(stamp)
    base=len(slots)*len(leagues)
    total=base+RESERVE
    fresh=now-stamp<=MAX_SNAPSHOT_AGE and (stamp.year,stamp.month)==(now.year,now.month)
    report.update(remainingCreditsAtSnapshot=balance,snapshotAt=stamp.isoformat(),snapshotFresh=fresh,
        scheduledRunsRemaining=len(slots),baseCreditsReserved=base,totalCreditsReserved=total,
        reserveShortfall=max(0,total-balance),
        theoreticalExtraEventCapacity=min(MAX_EXTRA_EVENTS,max(0,balance-total)//EXTRA_COST_CAP) if fresh else None,
        status="stale_balance" if not fresh else "reserve_shortfall" if balance<total else "planning_only")
    return report

if __name__=="__main__":
    snapshot=json.loads(Path("odds.json").read_text())
    r=plan(snapshot,datetime.now(timezone.utc),Path(".github/workflows/daily.yml").read_text())
    Path("extra_market_budget_plan.json").write_text(json.dumps(r,indent=2)+"\n")
    print("EXTRA_MARKET_BUDGET_686",json.dumps(r))
