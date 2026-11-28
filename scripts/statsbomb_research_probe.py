"""StatsBomb Open Data: bounded source-readiness research only.
No raw event redistribution, no betting use or production integration.
"""
import json,math
from datetime import date
from collections import Counter
from pathlib import Path
from urllib.request import Request,urlopen

BASE="https://raw.githubusercontent.com/hudl/open-data/master/data/"
SAMPLES=((9,281),(16,4))
LIMIT=3
ATTRIBUTION="StatsBomb Open Data (https://github.com/hudl/open-data)"

def read(path):
    with urlopen(Request(BASE+path,headers={"User-Agent":"OrtakAnaliz research source audit"}),timeout=25) as f:
        raw=f.read(20_000_001)
    if len(raw)>20_000_000:
        raise ValueError("size limit")
    return json.loads(raw)

def coords(v):
    return isinstance(v,list) and len(v)==2 and all(type(x) in (int,float) and math.isfinite(x) and 0<=x<=b for x,b in zip(v,(120,80)))

def inspect(events,teams):
    if not isinstance(events,list):
        raise ValueError("events schema")
    counts=Counter()
    xg={team:0.0 for team in teams}
    seen=set()
    for e in events:
        if not isinstance(e,dict):
            counts["invalid"]+=1
            continue
        eid=e.get("id")
        if not isinstance(eid,str) or not eid or eid in seen:
            counts["invalid"]+=1
            continue
        seen.add(eid)
        if e.get("period") not in (1,2,3,4):
            continue
        typ=(e.get("type") or {}).get("name")
        tid=(e.get("team") or {}).get("id")
        if typ not in ("Shot","Pass","Carry"):
            continue
        if tid not in teams:
            counts["invalid"]+=1
            continue
        if typ=="Shot":
            counts["shots"]+=1
            v=(e.get("shot") or {}).get("statsbomb_xg")
            if type(v) in (int,float) and math.isfinite(v) and 0<=v<=1:
                xg[tid]+=v
                counts["shotsWithXg"]+=1
            else:
                counts["missingXg"]+=1
        else:
            counts["movements"]+=1
            obj=e.get(typ.lower()) or {}
            if coords(e.get("location")) and coords(obj.get("end_location")):
                counts["coordinatePairs"]+=1
                if typ=="Pass":
                    counts["passesWithCoordinates"]+=1
                    if "outcome" not in obj:
                        counts["completedPassesWithCoordinates"]+=1
                else:
                    counts["carriesWithCoordinates"]+=1
    ready=counts["shots"]>0 and counts["missingXg"]==0 and counts["invalid"]==0
    # Do not publish match-level xG or raw events; only report coverage counts.
    return dict(counts=dict(counts),xgComplete=ready,xgaDerivable=ready,
        movementCoordinatesPresent=counts["coordinatePairs"]>0,xtComputed=False)

def build(reader=read):
    catalog=reader("competitions.json")
    if not isinstance(catalog,list):
        raise ValueError("catalog schema")
    pairs={(r["competition_id"],r["season_id"]):r for r in catalog}
    report=dict(version="6.51d",source=ATTRIBUTION,mode="research_only",catalogEntries=len(catalog),
        sampled=0,xgComplete=0,xgaDerivable=0,movementCoordinatesPresent=0,xtComputed=False,
        currentLeagueCoverageVerified=False,usedForTraining=False,productionModelValidated=False,
        existingArchivesModified=False,groups=[],errors=[])
    for comp,season in SAMPLES:
        if (comp,season) not in pairs:
            report["errors"].append(dict(competition=comp,season=season,error="catalog_missing"))
            continue
        meta=pairs[comp,season]
        group=dict(competition=meta["competition_name"],season=meta["season_name"],sampled=0,xgComplete=0,xgaDerivable=0,movementCoordinatesPresent=0,counts={})
        report["groups"].append(group)
        try:
            matches=reader(f"matches/{comp}/{season}.json")
            if not isinstance(matches,list):
                raise ValueError("matches schema")
            ids=Counter(m["match_id"] for m in matches)
            rows=sorted((m for m in matches if ids[m["match_id"]]==1 and type(m["match_id"]) is int and m["match_id"]>0 and date.fromisoformat(m["match_date"])<date.today()),key=lambda m:(m["match_date"],m["match_id"]))[:LIMIT]
            for m in rows:
                try:
                    teams={m["home_team"]["home_team_id"],m["away_team"]["away_team_id"]}
                    if len(teams)!=2:
                        raise ValueError("team identity")
                    r=inspect(reader(f'events/{m["match_id"]}.json'),teams)
                    group["sampled"]+=1
                    for k in ("xgComplete","xgaDerivable","movementCoordinatesPresent"):
                        group[k]+=int(r[k])
                    for k,v in r["counts"].items():
                        group["counts"][k]=group["counts"].get(k,0)+v
                except (OSError,ValueError,KeyError,TypeError,AttributeError) as exc:
                    report["errors"].append(dict(competition=comp,season=season,error=type(exc).__name__))
        except (OSError,ValueError,KeyError,TypeError,AttributeError) as exc:
            report["errors"].append(dict(competition=comp,season=season,error=type(exc).__name__))
        for k in ("sampled","xgComplete","xgaDerivable","movementCoordinatesPresent"):
            report[k]+=group[k]
    return report

if __name__=="__main__":
    report=build()
    Path("statsbomb_research_report.json").write_text(json.dumps(report,indent=2)+"\n")
    print("STATSBOMB_RESEARCH",json.dumps({k:v for k,v in report.items() if k!="groups"}))
    if not report["sampled"]:
        raise SystemExit("no source samples")
