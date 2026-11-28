"""V5.46: compare a bounded official TFF sample within the daily fixture date window."""
import json
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from tff_fixture_link_discovery import discover,FIXTURE_URL
from tff_match_identity_probe import extract
from turkey_source import team_key
from results_source_pilot import read,TR

# Known official source labels from TFF 2026-27 round 13 fixture page.
LABELS={
"corendon alanyaspor":"alanyaspor","tumosan konyaspor":"konyaspor",
"caykur rizespor a s":"rizespor","kasimpasa a s":"kasimpasa",
"samsunspor a s":"samsunspor","genclerbirligi":"genclerbirligi",
"gaziantep futbol kulubu a s":"gaziantep","amed sportif faaliyetler":"amed",
"arca corum fk":"corum","kocaelispor":"kocaelispor","eyupspor":"eyupspor",
"istanbul basaksehir fk":"basaksehir","fenerbahce a s":"fenerbahce",
"erzurumspor fk":"erzurumspor","goztepe a s":"goztepe",
"trabzonspor a s":"trabzonspor","besiktas a s":"besiktas","galatasaray a s":"galatasaray",
}
# Explicit bounded inspection range around already verified match 317894.
# Only fetch IDs returned by the official fixture listing, never generate URLs.
START_ID=317885
SAMPLE_SIZE=27
LEAGUE="Türkiye Süper Lig"
def source_key(label):
    key=team_key(label)
    return LABELS.get(key,key if key in LABELS.values() else None)
def match_key(day,teams):
    if len(teams)!=2 or not all(teams) or teams[0]==teams[1]:return None
    return (day,*sorted(teams))
def compare(daily,rows,now):
    stamp=datetime.fromisoformat(daily["updatedAt"])
    if stamp.tzinfo is None or stamp.astimezone(TR).date()!=now.astimezone(TR).date():raise ValueError("daily snapshot date mismatch")
    index={}
    for f in daily["upcoming"]:
        if f["league"]!=LEAGUE:continue
        names=f["match"].split(" – ")
        key=match_key(f["date"],[team_key(n) for n in names])
        if key:index.setdefault(key,[]).append(f["match"])
    if not index:raise ValueError("no daily league fixtures")
    first=min(k[0] for k in index);last=max(k[0] for k in index)
    out=[]
    seen=set()
    for r in rows:
        result=dict(r)
        if r.get("status")!="observed" or not r.get("kickoff"):
            result["comparison"]="unavailable";out.append(result);continue
        day=datetime.fromisoformat(r["kickoff"]).astimezone(TR).date().isoformat()
        if not first<=day<=last:
            result["comparison"]="outside_daily_window";out.append(result);continue
        key=match_key(day,[source_key(c["label"]) for c in r["clubs"]])
        result["comparison"]="unmapped" if key is None else "duplicate_official_pair" if key in seen else "pair_date_match" if len(index.get(key,[]))==1 else "ambiguous_daily_pair" if key in index else "absent_from_daily"
        result["dailyMatches"]=index.get(key,[])
        if key:seen.add(key)
        out.append(result)
    return out
def build(daily,now,reader=read):
    links=discover(reader(FIXTURE_URL))
    selected=[x for x in links if START_ID<=int(x["matchId"])<START_ID+SAMPLE_SIZE]
    if len(selected)!=SAMPLE_SIZE:raise ValueError("bounded source sample incomplete")
    def fetch(link):
        try:return dict(link,status="observed",**extract(reader(link["source"])))
        except (OSError,ValueError,TypeError,KeyError) as exc:return dict(link,status="error",error=type(exc).__name__)
    with ThreadPoolExecutor(max_workers=3) as pool:rows=list(pool.map(fetch,selected))
    rows=compare(daily,rows,now)
    days=sorted({f["date"] for f in daily["upcoming"] if f["league"]==LEAGUE})
    matched={(datetime.fromisoformat(r["kickoff"]).astimezone(TR).date().isoformat(),name) for r in rows if r["comparison"]=="pair_date_match" for name in r["dailyMatches"]}
    unmatched=[dict(date=f["date"],match=f["match"]) for f in daily["upcoming"] if f["league"]==LEAGUE and (f["date"],f["match"]) not in matched]
    return dict(version="5.46",mode="official_fixture_pair_date_coverage_only",windowStart=days[0],windowEnd=days[-1],sampleOnly=True,unmatchedDaily=unmatched,outsideWindow=sum(r["comparison"]=="outside_daily_window" for r in rows),dailyUpdatedAt=daily["updatedAt"],updatedAt=now.isoformat(),requested=len(rows),pairDateMatches=sum(r["comparison"]=="pair_date_match" for r in rows),absentFromDaily=sum(r["comparison"]=="absent_from_daily" for r in rows),orientationVerified=False,automaticFixtureLinking=False,predictionsEnabled=False,decision="PAS",rows=rows)
if __name__=="__main__":
    daily=json.loads(Path("daily.json").read_text(encoding="utf-8"))
    r=build(daily,datetime.now(TR))
    Path("tff_fixture_coverage_probe.json").write_text(json.dumps(r,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(r,ensure_ascii=False))
    if not r["pairDateMatches"]:raise SystemExit("No verified pair/date matches")
