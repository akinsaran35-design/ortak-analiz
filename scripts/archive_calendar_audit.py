"""V4.70 research audit of archived forecasts against corroborated date proposals.
Never rewrite dates, probabilities, scores or validation counts.
"""
import json
from collections import Counter
from datetime import date,datetime,timedelta,timezone
from pathlib import Path
from league_config import FIXTURE_CODES
from zoneinfo import ZoneInfo

TR=ZoneInfo("Europe/Istanbul")
def stamp(s):
    t=datetime.fromisoformat(s.replace("Z","+00:00"))
    if t.tzinfo is None: raise ValueError("missing timezone")
    return t
def audit(archive,calendar,daily,odds,now,performance=False):
    report={"version":"4.70","updatedAt":now.isoformat(),"mode":"research_only","status":"unavailable","rows":[],"counts":{},"decision":"PAS"}
    try:
        if calendar["status"]!="research_only" or calendar["oddsFresh"] is not True: return report
        if calendar["dailyUpdatedAt"]!=daily["updatedAt"] or calendar["oddsUpdatedAt"]!=odds["updatedAt"]: return report
        if any(not timedelta(0)<=now-stamp(t)<=timedelta(minutes=30) for t in (calendar["updatedAt"],odds["updatedAt"],daily["updatedAt"])): return report
        proposals=calendar["proposedCorrections"]
        events=odds["events"]
        byid=Counter(e["id"] for e in events)
        lookup={e["id"]:e for e in events}
        identities=Counter()
        records=[]
        for r in archive.values():
            if performance:
                h,a=r["match"].split(" – ")
                league=FIXTURE_CODES[r["league"]]
            else:
                h,a=r["home"],r["away"]
                league=r["league"]
            ident=(league,h,a,r["date"])
            identities[ident]+=1
            records.append((ident,r))
        for p in proposals:
            h,a=p["match"].split(" – ")
            league=FIXTURE_CODES[p["league"]]
            old,new=p["originalDate"],p["corroboratedDate"]
            if old==new or abs((date.fromisoformat(new)-date.fromisoformat(old)).days)>2: continue
            eid=p["eventId"]
            if byid[eid]!=1: continue
            ev=lookup[eid]
            from league_config import RESULT_CODES
            if RESULT_CODES.get(ev["league"])!=league: continue
            from match_odds import canonical
            if (canonical(h,ev["league"]),canonical(a,ev["league"]))!=(canonical(ev["home"],ev["league"]),canonical(ev["away"],ev["league"])): continue
            kickoff=stamp(ev["kickoff"])
            if kickoff.astimezone(TR).date().isoformat()!=new: continue
            oldid=(league,h,a,old); newid=(league,h,a,new)
            for ident,r in records:
                if ident!=oldid: continue
                recorded=stamp(r["recordedAt"])
                state="review_pending"
                if identities[oldid]!=1 or identities[newid]: state="duplicate_risk"
                elif r["result"] is not None: state="already_settled"
                elif recorded>=kickoff or recorded>now: state="late_prediction"
                elif recorded.astimezone(TR).date()>=date.fromisoformat(new): state="same_day_review"
                report["rows"].append(dict(league=league,home=h,away=a,archivedDate=old,corroboratedDate=new,eventId=eid,kickoff=kickoff.isoformat(),recordedAt=r["recordedAt"],status=state))
        report["status"]="research_only"
        report["counts"]=dict(Counter(r["status"] for r in report["rows"]))
    except (KeyError,TypeError,ValueError,AttributeError):
        report.update(status="unavailable",rows=[],counts={})
    return report
def main():
    now=datetime.now(timezone.utc)
    def read(p): return json.loads(Path(p).read_text())
    try:
        calendar=read("fixture_reconciliation.json")
        daily=read("daily.json");odds=read("odds.json")
        prospective=audit(read("prospective_archive.json"),calendar,daily,odds,now)
        performance=audit(read("prediction_archive.json"),calendar,daily,odds,now,True)
    except (OSError,ValueError):
        prospective=performance={"status":"unavailable","counts":{},"rows":[]}
    report={"version":"4.70","updatedAt":now.isoformat(),"mode":"research_only","decision":"PAS","prospective":prospective,"performance":performance}
    Path("archive_calendar_audit.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({"prospective":prospective["counts"],"performance":performance["counts"],"statuses":[prospective["status"],performance["status"]]},ensure_ascii=False))
if __name__=="__main__": main()
