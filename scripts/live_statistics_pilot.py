"""Read-only ESPN football match summary observations; no live predictions."""
import json
from datetime import datetime,timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from scoreboard_snapshot import build as board
from results_source_pilot import read,TR
from nine_league_results_pilot import SOURCES

METRICS={"wonCorners":"corners","totalShots":"shots","shotsOnTarget":"shotsOnTarget","yellowCards":"yellowCards","redCards":"redCards","possessionPct":"possession"}
BASE="https://site.api.espn.com/apis/site/v2/sports/soccer/"
def parse_summary(payload,fixture):
    comp,=payload["header"]["competitions"]
    if str(comp["id"])!=fixture["eventId"]:raise ValueError("event identity")
    kickoff=datetime.fromisoformat(comp["date"].replace("Z","+00:00"))
    if kickoff!=datetime.fromisoformat(fixture["kickoff"]):raise ValueError("kickoff identity")
    teams={t["homeAway"]:t for t in comp["competitors"]}
    if len(comp["competitors"])!=2 or set(teams)!={"home","away"}:raise ValueError("team orientation")
    ids={}
    for side in ("home","away"):
        t=teams[side]["team"]
        if t["displayName"]!=fixture[side]:raise ValueError("team identity")
        ids[str(t["id"])]=side
    if len(ids)!=2:raise ValueError("duplicate team")
    result={side:{} for side in ("home","away")}
    seen=set()
    for t in payload.get("boxscore",{}).get("teams",[]):
        ident=str(t["team"]["id"])
        if ident not in ids or ident in seen:raise ValueError("boxscore identity")
        seen.add(ident)
        metrics=result[ids[ident]]
        for x in t.get("statistics",[]):
            key=METRICS.get(x.get("name"))
            if not key:continue
            raw=str(x.get("displayValue","")).strip().rstrip("%")
            try:
                value=float(raw)
                if not __import__("math").isfinite(value) or value<0 or (key=="possession" and value>100) or (key!="possession" and not value.is_integer()):continue
            except ValueError:continue
            value=value if key=="possession" else int(value)
            if key in metrics and metrics[key]!=value:raise ValueError("metric conflict")
            metrics[key]=value
    paired={k:[result["home"][k],result["away"][k]] for k in result["home"] if k in result["away"]}
    status=comp["status"]["type"]
    if status["state"] not in ("in","post"):raise ValueError("not played")
    score=[]
    for side in ("home","away"):
        raw=str(teams[side].get("score",""))
        if not raw.isascii() or not raw.isdigit():raise ValueError("score")
        score.append(int(raw))
    return dict(state=status["state"],status=status["name"],clock=str(comp["status"].get("displayClock") or ""),score=score,metrics=paired)
def select_candidates(candidates,max_events):
    """Prefer in-progress fixtures, then round-robin leagues within each state."""
    counts={}
    for x in candidates:
        k=(x["league"],x["eventId"]);counts[k]=counts.get(k,0)+1
    unique=[x for x in candidates if counts[(x["league"],x["eventId"])]==1]
    selected=[]
    for state in ("in","post"):
        groups={}
        for row in sorted(unique,key=lambda x:(x["kickoff"],x["league"],x["eventId"]),reverse=True):
            if row["state"]==state:groups.setdefault(row["league"],[]).append(row)
        while groups and len(selected)<max_events:
            for league in list(groups):
                if len(selected)>=max_events:break
                selected.append(groups[league].pop(0))
                if not groups[league]:del groups[league]
    return selected

def build(now,reader=read,board_reader=board,max_events=12):
    day=now.astimezone(TR).date()
    candidates=[]
    for i in range(5):
        b=board_reader(now,reader=reader,query_date=(day-timedelta(days=i)).isoformat())
        for group in b["groups"]:
            if group["error"] is not None or group["invalid"]:continue
            for row in group["rows"]:
                if row["state"]=="in" or row["state"]=="post" and row["status"]=="STATUS_FULL_TIME":
                    candidates.append(dict(row,league=group["league"]))
        if i>=1 and len(candidates)>=max_events and set(x["league"] for x in candidates)>=set(SOURCES):break
    candidates=select_candidates(candidates,max_events)
    def fetch(row):
        url=BASE+SOURCES[row["league"]][1]+"/summary?event="+row["eventId"]
        out=dict(league=row["league"],eventId=row["eventId"],home=row["home"],away=row["away"],kickoff=row["kickoff"],source=url,observation=None,error=None)
        try:out["observation"]=parse_summary(json.loads(reader(url)),row)
        except (OSError,ValueError,TypeError,KeyError,AttributeError) as exc:out["error"]=type(exc).__name__
        return out
    with ThreadPoolExecutor(max_workers=4) as pool:rows=list(pool.map(fetch,candidates))
    return dict(version="5.12",updatedAt=now.isoformat(),mode="source_observation_only",source="ESPN",rows=rows,requested=len(rows),responding=sum(x["error"] is None for x in rows),withMetrics=sum(bool((x["observation"] or {}).get("metrics")) for x in rows),sampledLeagues=sorted({x["league"] for x in rows}),metricLeagues=sorted({x["league"] for x in rows if (x["observation"] or {}).get("metrics")}),liveObserved=sum((x["observation"] or {}).get("state")=="in" for x in rows),realTime=False,predictionsEnabled=False,usedForSettlement=False,decision="PAS")
def main():
    r=build(datetime.now(TR))
    Path("live_statistics_pilot.json").write_text(json.dumps(r,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Match summary source:",json.dumps({k:v for k,v in r.items() if k!="rows"},ensure_ascii=False))
    print("Source observations:",json.dumps([{"league":x["league"],"eventId":x["eventId"],"error":x["error"],"metrics":list((x["observation"] or {}).get("metrics",{}))} for x in r["rows"]]))
    if not r["withMetrics"]:raise SystemExit("No verified match statistics in sample")
if __name__=="__main__":main()
