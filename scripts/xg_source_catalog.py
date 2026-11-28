"""xGTables public catalog coverage only; not permission to ingest underlying data."""
import json
from datetime import datetime,timedelta
from results_source_pilot import read,TR
URL="https://www.xgtables.io/data/index.json"
CODES=("epl","serie-a","la-liga","bundesliga","ligue-1","ucl","uel","uecl")
def count(n):
    if type(n) is not int or n<0:raise ValueError("count")
    return n
def inspect(doc,now,season):
    if doc.get("schema_version")!=1:raise ValueError("schema")
    stamp=datetime.fromisoformat(doc["generated_at"].replace("Z","+00:00"))
    if stamp.tzinfo is None or stamp>now+timedelta(minutes=5):raise ValueError("timestamp")
    rows=[]; seen=set()
    for c in doc["competitions"]:
        slug=c["slug"]
        if slug not in CODES:continue
        if slug in seen:raise ValueError("duplicate competition")
        seen.add(slug)
        matches=[s for s in c["seasons"] if s["year"]==season]
        if not matches:continue
        s,=matches
        if s["source"]!="Sportmonks" or s["team_xg_source"]!="Sportmonks":raise ValueError("source model")
        total=count(s["fixtures"]);results=count(s["results"])
        stages=s["stages"]; ids=set();xg=0;fixtures=0;played=0
        for t in stages:
            tid=count(t["id"])
            if tid in ids:raise ValueError("duplicate stage")
            ids.add(tid)
            a,b,d=(count(t[k]) for k in ("fixtures","results","with_xg"))
            if not d<=b<=a:raise ValueError("coverage")
            fixtures+=a;played+=b;xg+=d
        if fixtures!=total or played!=results:raise ValueError("stage totals")
        rows.append(dict(competition=slug,fixtures=total,results=results,reportedWithXg=xg))
    return dict(version="7.25",mode="catalog_metadata_only",source="xGTables",upstream="Sportmonks",
                season=season,generatedAt=stamp.isoformat(),catalogFresh=now-stamp<=timedelta(days=3),
                competitions=rows,reportedWithXg=sum(r["reportedWithXg"] for r in rows),
                status="checked" if rows else "empty",individualMatchesValidated=False,
                redistributionPermissionVerified=False,predictionsEnabled=False,decision="PAS")
def probe(now,reader=read):
    try:
        day=now.astimezone(TR).date()
        return inspect(json.loads(reader(URL)),now,day.year-(day.month<7))
    except (OSError,ValueError,TypeError,KeyError,AttributeError) as exc:
        return dict(version="7.25",status="unverified",error=type(exc).__name__,predictionsEnabled=False,decision="PAS")
if __name__=="__main__":
    print(json.dumps(probe(datetime.now(TR)),ensure_ascii=False))
