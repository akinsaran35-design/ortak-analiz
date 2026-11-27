import os,json
from datetime import datetime,timedelta
from pathlib import Path
from scoreboard_snapshot import build,TR
from secondary_fixtures import build as secondary
from cross_source_match import match,norm
MAP={"en.1":2021,"en.2":2016,"de.1":2002,"es.1":2014,"it.1":2019,"fr.1":2015,"nl.1":2003,"pt.1":2017,"uefa.champions":2001}
now=datetime.now(TR)
holdout=os.environ.get("CROSS_HOLDOUT")=="1"
offsets=(-22,-21,-20) if holdout else (-1,0,1)
s=secondary(os.environ.get("FOOTBALL_DATA_TOKEN"),now,now.date()+timedelta(days=-23),now.date()+timedelta(days=-19)) if holdout else secondary(os.environ.get("FOOTBALL_DATA_TOKEN"),now)
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
r.update(primaryCount=len(p),secondaryCount=len(s["rows"]),secondaryStatus=s["status"],version="5.79",holdout=holdout,dates=[str(now.date()+timedelta(days=x)) for x in offsets])
Path("cross_audit.json").write_text(json.dumps(r,indent=2))
print("Cross audit:",len(p),len(s["rows"]),len(r["pairs"]),sum(x["scoreAgreement"] is True for x in r["pairs"]),sum(x["scoreAgreement"] is False for x in r["pairs"]))
assert s["status"]=="observed" and p
assert not any(x["scoreAgreement"] is False for x in r["pairs"])
print("Independent sample coverage:",len(r["pairs"])/len(p))
