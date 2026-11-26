"""Freeze pre-kickoff candidate evidence before daily reports are replaced."""
import json
from datetime import datetime,timedelta
from pathlib import Path
from collections import Counter
from live_rate_link import stamp,audited_name,link
from live_analysis_quality import build as quality
from live_score_scenario import scenario
from league_config import FIXTURE_CODES
from results_source_pilot import TR

def freeze(daily,coverage,previous,now):
    out={k:v for k,v in previous.items() if stamp(v.get("kickoff")) and now-stamp(v["kickoff"])<=timedelta(days=7)}
    dt=stamp(daily.get("updatedAt"));ct=stamp(coverage.get("updatedAt"))
    if not dt or not ct or not dt<=ct<=now or now-dt>timedelta(hours=48):return out
    if coverage.get("dailyUpdatedAt")!=daily.get("updatedAt"):return out
    for x in coverage.get("rows",[]):
        if x.get("status")!="same_date" or len(x.get("published",[]))!=1 or len(x.get("espn",[]))!=1:continue
        e=x["espn"][0];p=x["published"][0];kickoff=stamp(e.get("kickoff"))
        if not kickoff or not now<kickoff<=now+timedelta(days=3) or kickoff-dt>timedelta(hours=48):continue
        try:h,a=e["match"].split(" – ");key=x["league"]+":"+e["eventId"]
        except (ValueError,KeyError,TypeError):continue
        row=dict(league=x["league"],eventId=e["eventId"],home=h,away=a,kickoff=e["kickoff"])
        name=audited_name(row,daily,coverage,kickoff)
        if name is None:continue
        cs=[c for c in daily.get("candidates",[]) if c.get("date")==p.get("date") and FIXTURE_CODES.get(c.get("league"))==x["league"] and c.get("match")==name]
        if len(cs)!=1:continue
        try:scenario([0,0],0,cs[0]["expectedGoals"]["home"],cs[0]["expectedGoals"]["away"])
        except (ValueError,TypeError,KeyError):continue
        if key in out:continue
        minimal={k:coverage[k] for k in ("version","source","mode","dailyUpdatedAt","updatedAt","dates")}
        minimal["rows"]=[dict(league=x["league"],status=x["status"],espn=[e],published=[{k:p[k] for k in ("date","league","match")}])]
        out[key]=dict(kickoff=e["kickoff"],frozenAt=now.isoformat(),daily=dict(updatedAt=daily["updatedAt"],candidates=[{k:cs[0][k] for k in ("date","league","match","expectedGoals")}]),coverage=minimal)
    return out

def build(snapshot,frozen,now):
    rows=[]
    for r in quality(snapshot,now)["rows"]:
        f=frozen.get(r["league"]+":"+r["eventId"])
        t=stamp(f.get("frozenAt")) if f else None;k=stamp(r.get("kickoff"))
        if not f or not t or not k or not t<k:
            status,result="no_frozen_prematch_evidence",None
        else:status,result=link(r,f["daily"],now,f["coverage"])
        rows.append(dict(league=r["league"],eventId=r["eventId"],home=r["home"],away=r["away"],kickoff=r["kickoff"],receivedAt=r["receivedAt"],prematchUpdatedAt=f["daily"]["updatedAt"] if f else None,status=status,scenario=result))
    return dict(version="5.22",mode="live_link_research_only",updatedAt=now.isoformat(),sourceTimestampVerified=False,modelCalibrated=False,predictionsEnabled=False,decision="PAS",rows=rows,counts=dict(Counter(r["status"] for r in rows)))

def main():
    def load(path):return json.loads(Path(path).read_text(encoding="utf-8"))
    path=Path("prior-live-data/live_prematch_frozen.json")
    previous=load(path) if path.exists() else {}
    now=datetime.now(TR)
    frozen=freeze(load("daily.json"),load("fixture_coverage_audit.json"),previous,now)
    report=build(load("live_refresh_snapshot.json"),frozen,datetime.now(TR))
    for name,value in (("live_prematch_frozen.json",frozen),("live_rate_link.json",report)):
        Path(name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Frozen pre-kickoff evidence:",len(frozen),"Live research statuses:",report["counts"])
if __name__=="__main__":main()
