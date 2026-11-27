import os,json
from datetime import date,datetime,timedelta
from pathlib import Path
from scoreboard_snapshot import build,TR
from secondary_fixtures import build as secondary
from cross_source_match import match,norm
MAP={"en.1":2021,"en.2":2016,"de.1":2002,"es.1":2014,"it.1":2019,"fr.1":2015,"nl.1":2003,"pt.1":2017,"uefa.champions":2001}
now=datetime.now(TR)
holdout=os.environ.get("CROSS_HOLDOUT")=="1"
# Fixed, disjoint from V5.83/V5.84 (Oct 23-Nov 2) and V5.79 (Nov 5-7).
start=date(2026,11,9)
offsets=tuple((start-now.date()).days+i for i in range(11)) if holdout else (-1,0,1)
token=os.environ.get("FOOTBALL_DATA_TOKEN")
def secondary_windowed():
    # Overlap boundaries so either inclusive or exclusive dateTo is safe.
    first=(start-now.date()).days
    windows=[(first-1,first+3),(first+3,first+7),(first+7,first+11)]
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
for offset in offsets:
    report=build(now,query_date=(now.date()+timedelta(days=offset)).isoformat(),extra_codes=("uefa.champions",))
    for g in report["groups"]:
        if g["league"] not in MAP or g["error"] or g["invalid"]:continue
        for r in g["rows"]:
            p.append(dict(r,league=g["league"],score=r["score"] if r["state"]=="post" and r["status"]=="STATUS_FULL_TIME" else None))
r=match(p,s["rows"],MAP)
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
r.update(primaryCount=len(p),secondaryCount=len(s["rows"]),secondaryStatus=s["status"],version="5.85",sampleRole="new_holdout" if holdout else "current",coverage=len(r["pairs"])/len(p) if p else None,scoreCompared=sum(x["scoreAgreement"] is not None for x in r["pairs"]),secondaryWindows=s.get("windows",[]),holdout=holdout,dates=[str(now.date()+timedelta(days=x)) for x in offsets])
Path("cross_audit.json").write_text(json.dumps(r,indent=2))
print("Cross audit:",len(p),len(s["rows"]),len(r["pairs"]),sum(x["scoreAgreement"] is True for x in r["pairs"]),sum(x["scoreAgreement"] is False for x in r["pairs"]))
assert s["status"]=="observed" and p, f"Secondary status: {s['status']}; windows: {s.get('windows', [])}"
assert r["pairs"], "No independent matches; coverage audit cannot pass"
assert not any(x["scoreAgreement"] is False for x in r["pairs"])
if holdout:assert r["scoreCompared"]>0, "No comparable completed scores"
print("Independent sample coverage:",r["coverage"],"score comparisons:",r["scoreCompared"])
