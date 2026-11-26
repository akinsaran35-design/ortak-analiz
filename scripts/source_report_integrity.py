"""Structural checks for independent scoreboard and fixture research reports."""
from collections import Counter
from datetime import datetime,date,timedelta
from league_config import FIXTURE_CODES
from scoreboard_snapshot import TR
from fixture_coverage_audit import ident

def audit(daily,board,coverage):
    errors=[]
    def check(ok,label):
        if not ok: errors.append(label)
    try:
        groups=board["groups"]
        rows=[r for g in groups for r in g["rows"]]
        check(board["version"]=="4.90" and board["mode"]=="scoreboard_snapshot" and board["realTime"] is False and board["usedForSettlement"] is False and board["usedForPredictions"] is False,"scoreboard_lock")
        check(Counter(g["league"] for g in groups)==Counter(FIXTURE_CODES.values()),"scoreboard_leagues")
        check(board["loadedLeagues"]==sum(g["error"] is None for g in groups) and board["eventCount"]==len(rows) and board["inProgress"]==sum(r["state"]=="in" for r in rows),"scoreboard_counts")
        check(board["date"]==datetime.fromisoformat(board["updatedAt"]).astimezone(TR).date().isoformat(),"scoreboard_date")
        check(all(len({r["eventId"] for r in g["rows"]})==len(g["rows"]) for g in groups),"scoreboard_duplicate")
        check(all(datetime.fromisoformat(r["kickoff"]).astimezone(TR).date().isoformat()==board["date"] and r["state"] in ("pre","in","post") and (r["score"] is None or isinstance(r["score"],list) and len(r["score"])==2 and all(type(x) is int and x>=0 for x in r["score"])) and (r["state"]!="in" or r["score"] is not None) and (r["state"]!="pre" or r["score"] is None) for r in rows),"scoreboard_row")
        check(coverage["version"]=="4.92" and coverage["mode"]=="research_only" and coverage["archivesModified"] is False and coverage["decision"]=="PAS" and coverage["dailyUpdatedAt"]==daily["updatedAt"],"fixture_audit_lock")
        start=datetime.fromisoformat(coverage["updatedAt"]).astimezone(TR).date()
        dates=[(start+timedelta(days=i)).isoformat() for i in (1,2,3)]
        check(coverage["dates"]==dates and coverage["sourceGroups"]==len(FIXTURE_CODES)*len(dates) and 0<=coverage["healthyGroups"]<=coverage["sourceGroups"],"fixture_audit_coverage")
        cr=coverage["rows"]
        check(coverage["counts"]==dict(Counter(r["status"] for r in cr)),"fixture_audit_counts")
        expected=Counter((r["date"],r["league"],r["match"]) for r in daily["upcoming"] if r["date"] in dates and r["league"] in FIXTURE_CODES)
        actual=Counter((p["date"],p["league"],p["match"]) for r in cr for p in r["published"])
        check(expected==actual,"fixture_audit_published_identity")
        keys=[]
        for r in cr:
            ps,ss=r["published"],r["espn"]
            pkeys=[ident(r["league"],*p["match"].split(" – ")) for p in ps]
            skeys=[ident(r["league"],*s["match"].split(" – ")) for s in ss]
            ids=pkeys+skeys
            check(bool(ids) and len(set(ids))==1 and all(FIXTURE_CODES[p["league"]]==r["league"] for p in ps),"fixture_audit_row_identity")
            keys.extend(set(ids))
            check(all(s["date"] in dates and datetime.fromisoformat(s["kickoff"]).astimezone(TR).date().isoformat()==s["date"] for s in ss),"fixture_audit_espn_date")
            st=r["status"]
            if st=="same_date": check(len(ps)==len(ss)==1 and ps[0]["date"]==ss[0]["date"],"fixture_audit_status")
            elif st=="date_difference": check(len(ps)==len(ss)==1 and ps[0]["date"]!=ss[0]["date"],"fixture_audit_status")
            elif st=="published_only": check(len(ps)==1 and not ss,"fixture_audit_status")
            elif st=="espn_only": check(not ps and len(ss)==1,"fixture_audit_status")
            else: check(st in ("ambiguous","source_incomplete"),"fixture_audit_status")
        check(len(keys)==len(set(keys)),"fixture_audit_duplicate")
    except (KeyError,TypeError,ValueError,AttributeError,IndexError):
        errors.append("source_audit_schema")
    return errors
