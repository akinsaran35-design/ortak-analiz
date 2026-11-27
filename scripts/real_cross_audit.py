import os,json
from datetime import date,datetime,timedelta
from pathlib import Path
from scoreboard_snapshot import build,TR
from secondary_fixtures import build as secondary
from cross_source_match import match,norm
MAP={"en.1":2021,"en.2":2016,"de.1":2002,"es.1":2014,"it.1":2019,"fr.1":2015,"nl.1":2003,"pt.1":2017,"uefa.champions":2001}
now=datetime.now(TR)
holdout=os.environ.get("CROSS_HOLDOUT")=="1"
# Fixed original Nov 9–19 plus separately reported Nov 20–22 extension.
# Original empty sample must not be described as validated.
start=date(2026,11,9)
offsets=tuple((start-now.date()).days+i for i in range(14)) if holdout else (-1,0,1)
token=os.environ.get("FOOTBALL_DATA_TOKEN")
def secondary_windowed():
    # Overlap boundaries so either inclusive or exclusive dateTo is safe.
    first=(start-now.date()).days
    windows=[(first-1,first+3),(first+3,first+7),(first+7,first+11),(first+11,first+14)]
    rows={}
    details=[]
    conflict=False
    for window_start,window_end in windows:
        date_from=now.date()+timedelta(days=window_start)
        date_to=now.date()+timedelta(days=window_end)
        batch=secondary(token,now,date_from,date_to)
        details.append(dict(dateFrom=str(date_from),dateTo=str(date_to),status=batch["status"],count=len(batch["rows"]),rejectedRows=batch.get("rejectedRows",0),errorType=batch.get("errorType"),missingField=batch.get("missingField")))
        for row in batch["rows"]:
            ident=row["eventId"]
            if ident in rows and rows[ident]!=row:
                conflict=True
            rows[ident]=row
    failed=any(d["status"] not in ("observed","empty") for d in details)
    status="conflicting_rows" if conflict else "window_error" if failed else "observed" if rows else "empty"
    print("Secondary windows:",json.dumps(details))
    return dict(rows=list(rows.values()),status=status,windows=details)
s=secondary_windowed() if holdout else secondary(token,now)
p=[]
primary_days=[]
for offset in offsets:
    report=build(now,query_date=(now.date()+timedelta(days=offset)).isoformat(),extra_codes=("uefa.champions",))
    primary_days.append(dict(date=report["date"],groups=[dict(league=g["league"],count=len(g["rows"]),invalid=g["invalid"],error=g["error"]) for g in report["groups"] if g["league"] in MAP]))
    for g in report["groups"]:
        if g["league"] not in MAP or g["error"] or g["invalid"]:continue
        for r in g["rows"]:
            p.append(dict(r,league=g["league"],score=r["score"] if r["state"]=="post" and r["status"]=="STATUS_FULL_TIME" else None))
r=match(p,s["rows"],MAP)
print("Primary daily diagnostics:",json.dumps(primary_days))
def sample_counts(date_from,date_to):
    def within(row):
        day=datetime.fromisoformat(row["kickoff"].replace("Z","+00:00")).astimezone(TR).date()
        return date_from<=day<=date_to
    primary=[row for row in p if within(row)]
    secondary_rows=[row for row in s["rows"] if within(row) and row["competitionId"] in MAP.values()]
    result=match(primary,secondary_rows,MAP)
    paired=len(result["pairs"])
    secondary_ids={x["secondaryId"] for x in result["pairs"]}
    return dict(primaryCount=len(primary),secondaryCount=len(secondary_rows),matched=paired,primaryCoverage=paired/len(primary) if primary else None,secondaryCoverage=paired/len(secondary_rows) if secondary_rows else None,secondaryOnly=[row["eventId"] for row in secondary_rows if row["eventId"] not in secondary_ids],scoreCompared=sum(x["scoreAgreement"] is not None for x in result["pairs"]),scoreMismatch=sum(x["scoreAgreement"] is False for x in result["pairs"]),status="empty_both" if not primary and not secondary_rows else "no_primary_data" if not primary else "no_secondary_data" if not secondary_rows else "partial" if paired!=len(primary) or paired!=len(secondary_rows) else "complete")
samples=dict(original=sample_counts(start,start+timedelta(days=10)),extension=sample_counts(start+timedelta(days=11),start+timedelta(days=13))) if holdout else {}
print("Separate sample counts:",json.dumps(samples))
audit_start=now.date()+timedelta(days=min(offsets))
audit_end=now.date()+timedelta(days=max(offsets))
scope=sample_counts(audit_start,audit_end)
daily=[dict(date=str(audit_start+timedelta(days=i)),**sample_counts(audit_start+timedelta(days=i),audit_start+timedelta(days=i))) for i in range((audit_end-audit_start).days+1)]
print("Bidirectional coverage:",json.dumps(scope))
print("Daily coverage:",json.dumps(daily))
expected_leagues=set(MAP)
primary_issues=[dict(date=day["date"],missing=sorted(expected_leagues-{g["league"] for g in day["groups"]}),failed=[g["league"] for g in day["groups"] if g["error"] or g["invalid"]]) for day in primary_days]
primary_issues=[day for day in primary_issues if day["missing"] or day["failed"]]
secondary_rejected=sum(w["rejectedRows"] for w in s["windows"]) if holdout else s.get("rejectedRows",0)
health=dict(primaryIssues=primary_issues,secondaryStatus=s["status"],secondaryRejected=secondary_rejected,emptyBothDays=[d["date"] for d in daily if d["status"]=="empty_both"],oneSidedDays=[d["date"] for d in daily if d["status"] in ("no_primary_data","no_secondary_data")],partialDays=[d["date"] for d in daily if d["status"]=="partial"])
health["observedScopeComplete"]=scope["status"]=="complete" and not primary_issues and s["status"]=="observed" and secondary_rejected==0 and not health["oneSidedDays"] and not health["partialDays"]
# Two agreeing feeds cannot independently prove that an empty schedule is complete.
health["allDatesVerified"]=health["observedScopeComplete"] and not health["emptyBothDays"]
print("Scope health:",json.dumps(health))
diagnostics=[]
for a in p:
    candidates=[]
    for b in s["rows"]:
        if MAP.get(a["league"])!=b["competitionId"]:continue
        delta=abs((datetime.fromisoformat(a["kickoff"].replace("Z","+00:00"))-datetime.fromisoformat(b["kickoff"].replace("Z","+00:00"))).total_seconds())/60
        if delta<=120:
            candidates.append(dict(secondaryId=b["eventId"],home=b["home"],away=b["away"],deltaMinutes=delta,exactHome=norm(a["home"])==norm(b["home"]),exactAway=norm(a["away"])==norm(b["away"])))
    diagnostics.append(dict(primaryId=a["eventId"],league=a["league"],home=a["home"],away=a["away"],candidates=candidates))
r["diagnostics"]=diagnostics
print("Candidate diagnostics:",json.dumps(diagnostics,ensure_ascii=False))
r.update(primaryCount=len(p),secondaryCount=len(s["rows"]),secondaryStatus=s["status"],version="5.87",scopeCoverage=scope,dailyCoverage=daily,scopeHealth=health,fullCoverageVerified=health["allDatesVerified"],sampleRole="holdout_with_reported_extension" if holdout else "current",primaryDays=primary_days,samples=samples,coverage=len(r["pairs"])/len(p) if p else None,scoreCompared=sum(x["scoreAgreement"] is not None for x in r["pairs"]),secondaryWindows=s.get("windows",[]),holdout=holdout,dates=[str(now.date()+timedelta(days=x)) for x in offsets])
Path("cross_audit.json").write_text(json.dumps(r,indent=2))
print("Cross audit:",len(p),len(s["rows"]),len(r["pairs"]),sum(x["scoreAgreement"] is True for x in r["pairs"]),sum(x["scoreAgreement"] is False for x in r["pairs"]))
assert s["status"]=="observed" and p, f"Secondary status: {s['status']}; windows: {s.get('windows', [])}"
assert r["pairs"], "No independent matches; coverage audit cannot pass"
assert not any(x["scoreAgreement"] is False for x in r["pairs"])
if holdout:assert r["scoreCompared"]>0, "No comparable completed scores"
print("Combined sample coverage:",r["coverage"],"score comparisons:",r["scoreCompared"])
