"""Link pre-kickoff rate snapshots to live observations for research only."""
import json
import re
from datetime import datetime,timedelta
from pathlib import Path
from league_config import FIXTURE_CODES
from live_analysis_quality import build as quality
from live_score_scenario import scenario
from results_source_pilot import TR

def stamp(value):
    try:
        t=datetime.fromisoformat(value)
        return t if t.tzinfo is not None else None
    except (TypeError,ValueError):return None

def audited_name(row,daily,coverage,kickoff):
    if not isinstance(coverage,dict) or coverage.get("version")!="4.92" or coverage.get("source")!="ESPN" or coverage.get("mode")!="research_only" or coverage.get("dailyUpdatedAt")!=daily.get("updatedAt"):return None
    created=stamp(coverage.get("updatedAt")); daily_time=stamp(daily.get("updatedAt"))
    if not created or not daily_time or not daily_time<=created<kickoff:return None
    day=kickoff.astimezone(TR).date().isoformat()
    if day not in coverage.get("dates",[]):return None
    name=row["home"]+" – "+row["away"]
    hits=[]
    for x in coverage.get("rows",[]):
        if x.get("league")!=row["league"]:continue
        for e in x.get("espn",[]):
            if e.get("eventId")==row["eventId"]:hits.append((x,e))
    if len(hits)!=1:return None
    x,e=hits[0]
    if x.get("status")!="same_date" or len(x.get("espn",[]))!=1 or len(x.get("published",[]))!=1:return None
    if e.get("date")!=day or stamp(e.get("kickoff"))!=kickoff or e.get("match")!=name:return None
    p=x["published"][0]
    if p.get("date")!=day or FIXTURE_CODES.get(p.get("league"))!=row["league"]:return None
    match=p.get("match")
    if not isinstance(match,str) or len(match.split(" – "))!=2:return None
    return match

def link(row,daily,now,coverage=None):
    if row["quality"]!="observation_ready":return "quality_rejected",None
    kickoff=stamp(row["kickoff"]);source_time=stamp(daily.get("updatedAt"))
    if not kickoff or not source_time or not kickoff-timedelta(hours=48)<=source_time<kickoff<=now:
        return "no_pre_kickoff_snapshot",None
    day=kickoff.astimezone(TR).date().isoformat()
    name=row["home"]+" – "+row["away"]
    if coverage is not None:
        name=audited_name(row,daily,coverage,kickoff)
        if name is None:return "no_verified_event_link",None
    candidates=[c for c in daily.get("candidates",[]) if isinstance(c,dict) and c.get("date")==day and FIXTURE_CODES.get(c.get("league"))==row["league"] and c.get("match")==name]
    if len(candidates)!=1:return "no_unique_exact_name_match",None
    obs=row["observation"]
    m=re.fullmatch(r"([0-9]{1,2})['′]",obs["clock"].strip())
    if not m or not 0<=int(m.group(1))<90:return "unsupported_clock",None
    if obs["metrics"]["redCards"]!=[0,0]:return "red_card_effect_unmodeled",None
    try:
        rates=candidates[0]["expectedGoals"]
        result=scenario(obs["score"],int(m.group(1)),rates["home"],rates["away"])
    except (KeyError,TypeError,ValueError):return "invalid_rates",None
    return "conditional_scenario",result

def build(snapshot,daily,now,coverage=None):
    q=quality(snapshot,now)
    rows=[]
    for row in q["rows"]:
        reason,result=link(row,daily,now,coverage)
        rows.append(dict(league=row["league"],eventId=row["eventId"],home=row["home"],away=row["away"],kickoff=row["kickoff"],receivedAt=row["receivedAt"],status=reason,scenario=result))
    return dict(version="5.17",mode="live_link_research_only",updatedAt=now.isoformat(),prematchUpdatedAt=daily.get("updatedAt"),identityMethod="pre-kickoff fixture audit event ID, kickoff, league and ordered source names" if coverage is not None else "exact league, local date, ordered team names; prematch event ID absent",sourceTimestampVerified=False,modelCalibrated=False,predictionsEnabled=False,decision="PAS",rows=rows)

def main():
    snapshot=json.loads(Path("live_refresh_snapshot.json").read_text(encoding="utf-8"))
    daily=json.loads(Path("daily.json").read_text(encoding="utf-8"))
    path=Path("fixture_coverage_audit.json")
    coverage=json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    report=build(snapshot,daily,datetime.now(TR),coverage)
    Path("live_rate_link.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Live rate link:",json.dumps({**{k:v for k,v in report.items() if k!="rows"},"statuses":[r["status"] for r in report["rows"]]},ensure_ascii=False))
if __name__=="__main__":main()
