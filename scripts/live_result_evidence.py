"""Bounded corroboration of archived live scenarios, independent of daily archive."""
import json
from datetime import datetime,timedelta
from pathlib import Path
from multi_league_results import build_report,verified_rows,APPROVED
from live_rate_link import stamp
from results_source_pilot import TR

def update(records,prior,now,probe=build_report):
    attempts=dict(prior.get("attempts",{}))
    verified={tuple(r[k] for k in ("date","league","home","away")):r for r in prior.get("verified",[])}
    blocked={tuple(x) for x in prior.get("blocked",[])}
    groups={}
    for key,r in records.items():
        day=r["date"];code=r["league"]
        if code not in APPROVED or not (now.date()-timedelta(days=14)).isoformat()<=day<now.date().isoformat():continue
        ident=(day,code,r["home"],r["away"])
        if ident in verified and ident not in blocked:continue
        group=code+":"+day
        groups.setdefault(group,{})[key]=dict(r,result=None)
    due=[g for g in groups if not stamp(attempts.get(g)) or now-stamp(attempts[g])>=timedelta(hours=3)]
    due.sort(key=lambda g:(attempts.get(g,""),g))
    chosen=due[:2]
    if chosen:
        report=probe({k:r for g in chosen for k,r in groups[g].items()},now)
        for g in chosen:attempts[g]=now.isoformat()
        for group in report["groups"]:
            if group["errors"]:continue
            for r in group["rows"]:
                ident=(r["date"],group["league"],r["home"],r["away"])
                if r["status"] in ("conflict","ambiguous","archive_conflict"):
                    blocked.add(ident);verified.pop(ident,None)
        for r in verified_rows(report,now):
            ident=tuple(r[k] for k in ("date","league","home","away"))
            if ident not in blocked:verified[ident]=r
    return dict(version="5.22",updatedAt=now.isoformat(),mode="research_only",verified=list(verified.values()),blocked=[list(x) for x in sorted(blocked)],attempts=attempts,groupsQueried=len(chosen))

def main():
    def load(p,default):return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default
    root=Path("prior-live-data")
    report=update(load(root/"live_scenario_archive.json",{}),load(root/"live_result_evidence.json",{}),datetime.now(TR))
    Path("live_result_evidence.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Live result evidence:",len(report["verified"]),"blocked:",len(report["blocked"]),"groups queried:",report["groupsQueried"])
if __name__=="__main__":main()
