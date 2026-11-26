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

def link(row,daily,now):
    if row["quality"]!="observation_ready":return "quality_rejected",None
    kickoff=stamp(row["kickoff"]);source_time=stamp(daily.get("updatedAt"))
    if not kickoff or not source_time or not kickoff-timedelta(hours=48)<=source_time<kickoff<=now:
        return "no_pre_kickoff_snapshot",None
    day=kickoff.astimezone(TR).date().isoformat()
    name=row["home"]+" – "+row["away"]
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

def build(snapshot,daily,now):
    q=quality(snapshot,now)
    rows=[]
    for row in q["rows"]:
        reason,result=link(row,daily,now)
        rows.append(dict(league=row["league"],eventId=row["eventId"],home=row["home"],away=row["away"],kickoff=row["kickoff"],receivedAt=row["receivedAt"],status=reason,scenario=result))
    return dict(version="5.17",mode="live_link_research_only",updatedAt=now.isoformat(),prematchUpdatedAt=daily.get("updatedAt"),identityMethod="exact league, local date, ordered team names; prematch event ID absent",sourceTimestampVerified=False,modelCalibrated=False,predictionsEnabled=False,decision="PAS",rows=rows)

def main():
    snapshot=json.loads(Path("live_refresh_snapshot.json").read_text(encoding="utf-8"))
    daily=json.loads(Path("daily.json").read_text(encoding="utf-8"))
    report=build(snapshot,daily,datetime.now(TR))
    Path("live_rate_link.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Live rate link:",json.dumps({**{k:v for k,v in report.items() if k!="rows"},"statuses":[r["status"] for r in report["rows"]]},ensure_ascii=False))
if __name__=="__main__":main()
