"""V5.25: sample completed match referee records for every configured league."""
import json
import re
from urllib.parse import urlsplit
from collections import Counter,defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timedelta
from pathlib import Path
from scoreboard_snapshot import parse as parse_board
from live_statistics_pilot import BASE,parse_summary
from football_statistics_pilot import parse as parse_csv
from nine_league_results_pilot import SOURCES
from league_config import LEAGUES
from results_source_pilot import read,TR

def extract(payload,fixture):
    observation=parse_summary(payload,fixture)
    if observation["state"]!="post" or observation["status"]!="STATUS_FULL_TIME" or observation["score"]!=fixture["score"]:raise ValueError("final score identity")
    comp,=payload["header"]["competitions"]
    if comp["status"]["type"].get("completed") is not True:raise ValueError("completion")
    officials=payload.get("gameInfo",{}).get("officials",[])
    if not isinstance(officials,list):raise ValueError("officials schema")
    referee=classify_officials(officials)
    return dict(**referee,cards={k:observation["metrics"][k] for k in ("yellowCards","redCards") if k in observation["metrics"]},refereeSource="ESPN summary")

def classify_officials(officials):
    labels=set();roles=set()
    for o in officials:
        p=o.get("position") or o.get("type") or {}
        if not isinstance(p,dict):continue
        role=str(p.get("name") or p.get("displayName") or "").strip().casefold()
        roles.add(role)
        if role not in ("referee","head referee","main referee"):continue
        name=o.get("displayName") or o.get("fullName") or o.get("name")
        if isinstance(name,str) and name.strip():
            labels.add((name.strip(),str(o["id"]) if o.get("id") is not None else None))
    referee=None
    if len(labels)==1:
        name,ident=next(iter(labels));referee=dict(label=name,sourceId=ident)
    return dict(referee=referee,officialRoles=sorted(roles),officialCount=len(officials),status="observed" if referee else "ambiguous" if len(labels)>1 else "missing")

def core_officials(reader,espn,event):
    # Only provider-hosted references for this exact competition.
    if not re.fullmatch(r"[a-z]{3}\.[0-9]+",espn) or not re.fullmatch(r"[0-9]+",event):raise ValueError("event path")
    root=f"https://sports.core.api.espn.com/v2/sports/soccer/leagues/{espn}/events/{event}/competitions/{event}/officials"
    data=json.loads(reader(root+"?limit=25"))
    items=data.get("items")
    if not isinstance(items,list) or len(items)>25 or data.get("pageCount",1)>1 or data.get("count",len(items))!=len(items):raise ValueError("incomplete officials collection")
    officials=[]
    for item in items:
        if not isinstance(item,dict):raise ValueError("official schema")
        ref=item.get("$ref")
        if ref:
            u=urlsplit(ref)
            if u.scheme not in ("http","https") or u.netloc!="sports.core.api.espn.com" or not re.fullmatch(re.escape(urlsplit(root).path)+r"/[0-9]+",u.path):raise ValueError("official reference")
            detail=json.loads(reader("https://sports.core.api.espn.com"+u.path))
            if not isinstance(detail,dict):raise ValueError("official detail")
            officials.append(detail)
        else:officials.append(item)
    return classify_officials(officials),root

def build(now,reader=read,max_per_league=6):
    cutoff=now.astimezone(TR).date();year=cutoff.year-(cutoff.month<7)
    def group(entry):
        label,code,sport=entry;csv_code,espn=SOURCES[code]
        root=BASE+espn
        csv_url=f"https://football-data.co.uk/mmz4281/{year%100:02d}{(year+1)%100:02d}/{csv_code}.csv"
        g=dict(league=code,leagueName=label,csvSource=csv_url,boardSources=[],errors=[],rows=[])
        try:
            rows,_,_=parse_csv(reader(csv_url),code,sport,cutoff)
            days=sorted({r["date"] for r in rows},reverse=True)[:4]
        except (OSError,ValueError,TypeError,KeyError,AttributeError) as exc:
            g["errors"].append("csv:"+type(exc).__name__);days=[]
        if not days:days=[(cutoff-timedelta(days=i)).isoformat() for i in range(1,8)]
        fixtures=[];seen=set()
        for day in days:
            url=root+"/scoreboard?dates="+day.replace("-","");g["boardSources"].append(url)
            try:
                rows,invalid=parse_board(json.loads(reader(url)),day)
                if invalid:raise ValueError("invalid board")
                for f in rows:
                    if f["state"]=="post" and f["status"]=="STATUS_FULL_TIME" and f["eventId"] not in seen:
                        seen.add(f["eventId"]);fixtures.append(f)
            except (OSError,ValueError,TypeError,KeyError,AttributeError) as exc:g["errors"].append(day+":"+type(exc).__name__)
            if len(fixtures)>=max_per_league:break
        for f in fixtures[:max_per_league]:
            url=root+"/summary?event="+f["eventId"];r=dict(f,source=url,error=None,observation=None)
            try:r["observation"]=extract(json.loads(reader(url)),f)
            except (OSError,ValueError,TypeError,KeyError,AttributeError) as exc:r["error"]=type(exc).__name__
            if r["observation"] and r["observation"]["status"]=="missing":
                try:
                    result,source=core_officials(reader,espn,f["eventId"])
                    r["coreSource"]=source
                    r["observation"].update(result,refereeSource="ESPN core officials")
                except (OSError,ValueError,TypeError,KeyError,AttributeError) as exc:r["coreError"]=type(exc).__name__
            g["rows"].append(r)
        g["counts"]=dict(Counter(r["observation"]["status"] if r["observation"] else "error" for r in g["rows"]))
        return g
    with ThreadPoolExecutor(max_workers=6) as pool:groups=list(pool.map(group,LEAGUES))
    return dict(version="5.25",updatedAt=now.isoformat(),cutoffExclusive=cutoff.isoformat(),source="ESPN",mode="historical_referee_source_probe",sampleLimitPerLeague=max_per_league,identityVerified=False,upcomingAssignmentsVerified=False,predictionsEnabled=False,decision="PAS",groups=groups)

if __name__=="__main__":
    report=build(datetime.now(TR))
    Path("referee_coverage_research.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    for g in report["groups"]:
        print(json.dumps(dict(league=g["league"],requested=len(g["rows"]),counts=g["counts"],roles=sorted({role for r in g["rows"] for role in (r["observation"] or {}).get("officialRoles",[])}),errors=g["errors"],coreErrors=dict(Counter(r.get("coreError") for r in g["rows"] if r.get("coreError")))),ensure_ascii=False))
    if not any(g["rows"] for g in report["groups"]):raise SystemExit("No completed fixture observations")
