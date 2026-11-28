"""V4.75 structural integrity check for the complete research snapshot."""
import json
from pathlib import Path
from datetime import datetime,timezone

FILES=("daily","odds","matching","prospective_archive","prospective_validation","prediction_archive","performance","data_quality","archive_calendar_evidence","archive_calendar_evidence_status","archive_calendar_result_replay","unified_decision","score_provenance","multi_league_results","fixture_reconciliation","archive_calendar_outcomes","archive_calendar_outcome_status","prospective_leagues","scoreboard_snapshot","fixture_coverage_audit","kickoff_confirmation","model_research","football_statistics_pilot","football_coverage_pilot")

def audit(data):
    errors=[]
    def check(ok,label):
        if not ok: errors.append(label)
    try:
        d,o,m,a,v,p,f,q,e,s,r,u,prov,feeds,calendar,outcomes,outcome_status,league_report,board,fixture_audit,kickoff,models,statistics,coverage=(data[k] for k in FILES)
        check(d["candidateCount"]==len(d["candidates"]),"candidate_count")
        check(d["upcomingCount"]==len(d["upcoming"]),"fixture_count")
        check(o["eventCount"]==len(o["events"]),"odds_count")
        check(m["matchedCount"]==len(m["matched"]) and m["unmatchedCount"]==len(m["unmatched"]) and m["matchedCount"]+m["unmatchedCount"]==d["candidateCount"],"matching_count")
        n=sum(x["result"] is not None for x in a.values())
        check((v["recorded"],v["tested"],v["pending"])==(len(a),n,len(a)-n),"prospective_count")
        from prospective_markets import summarize
        reference=summarize(a,datetime.fromisoformat(v["updatedAt"]))
        from prospective_leagues import build
        league_reference=build(a,datetime.fromisoformat(v["updatedAt"]))
        # Old published snapshots predate classification; verify exactly the old schema.
        # New snapshots must include and exactly reproduce classification counts.
        if v.get("classificationVersion") is None:
            for x in reference.values():x.pop("classification",None)
            for entry in league_reference["leagues"].values():
                for x in entry["markets"].values():x.pop("classification",None)
        check(v.get("classificationVersion") in (None,"6.19") and v["marketResearchVersion"]=="4.85" and v["marketResearch"]==reference,"prospective_market_recompute")
        check(league_report==league_reference,"prospective_league_recompute")
        check((q["archiveRecords"],q["settled"],q["pending"])==(len(a),n,len(a)-n),"quality_count")
        k=sum(x["result"] is not None for x in p.values())
        overall=f["overall"]
        check((overall["recorded"],overall["settled"],overall["pending"])==(len(p),k,len(p)-k),"performance_count")
        check(all(x["tested"]==k for x in overall["markets"].values()),"market_count")
        identities={(x["archive"],x["league"],x["home"],x["away"],x["archivedDate"],x["recordedAt"]) for x in e.values()}
        check(s["observations"]==len(e) and s["archiveIdentities"]==len(identities),"evidence_count")
        rows=r["rows"]
        from collections import Counter
        check(len(rows)==len(identities) and dict(Counter(x["status"] for x in rows))==r["counts"],"calendar_replay_count")
        check({(x["archive"],x["league"],x["home"],x["away"],x["archivedDate"],x["recordedAt"]) for x in rows}==identities,"calendar_replay_identity")
        from league_config import FIXTURE_CODES
        expected=Counter(("prospective",x["league"],x["date"],x["home"],x["away"],tuple(x["result"])) for x in a.values() if x["result"] is not None)
        for x in p.values():
            if x["result"] is not None:
                h,away=x["match"].split(" – ")
                expected[("performance",FIXTURE_CODES[x["league"]],x["date"],h,away,tuple(x["result"]))]+=1
        actual=Counter((x["archive"],x["league"],x["date"],x["home"],x["away"],tuple(x["result"])) for x in prov["rows"])
        check(expected==actual and prov["settledArchiveRecords"]==n+k,"score_provenance_identity")
        check(prov["uniqueSettledMatches"]==len({x[1:5] for x in expected}),"score_provenance_unique_count")
        check(all(prov["counts"][kind]==dict(Counter(x["status"] for x in prov["rows"] if x["archive"]==kind)) for kind in ("prospective","performance")),"score_provenance_status_count")
        check(prov["version"]=="4.80" and feeds["version"]=="4.69","score_report_version")
        check(calendar.get("status")!="research_only" or (calendar["dailyUpdatedAt"]==d["updatedAt"] and calendar["oddsUpdatedAt"]==o["updatedAt"]),"calendar_snapshot_identity")
        score_rows=[x for x in outcomes.values() if x.get("observationType")!="conflict"]
        conflict_rows=[x for x in outcomes.values() if x.get("observationType")=="conflict"]
        outcome_identity=lambda x:(x["archive"],x["league"],x["home"],x["away"],x["archivedDate"],x["recordedAt"])
        check(all(outcome_identity(x) in identities for x in outcomes.values()),"outcome_evidence_identity")
        check(outcome_status["version"]=="4.83" and outcome_status["includedInMainValidation"] is False and outcome_status["decision"]=="PAS","outcome_research_lock")
        check(outcome_status["observations"]==len(score_rows) and outcome_status["conflictObservations"]==len(conflict_rows),"outcome_observation_count")
        check(outcome_status["archiveIdentities"]==len({outcome_identity(x) for x in score_rows}) and outcome_status["quarantinedIdentities"]==len({outcome_identity(x) for x in conflict_rows}),"outcome_identity_count")
        check(sum(outcome_status["counts"].values())==outcome_status["archiveIdentities"],"outcome_status_count")
        check(0<=outcome_status["uniqueEligibleEvents"]<=outcome_status["counts"].get("eligible_research",0),"outcome_event_count")
        from source_report_integrity import audit as audit_sources
        errors.extend(audit_sources(d,board,fixture_audit))
        from kickoff_confirmation import build as build_kickoff
        check(kickoff==build_kickoff(d,fixture_audit,o,datetime.fromisoformat(kickoff["updatedAt"])),"kickoff_recompute")
        from model_research import build as build_models
        check(models==build_models(d,datetime.fromisoformat(models["updatedAt"])),"model_research_recompute")
        from football_statistics_pilot import audit_report as audit_statistics
        from football_coverage_pilot import audit_report as audit_coverage
        check(audit_statistics(d,statistics),"football_statistics_integrity")
        check(audit_coverage(coverage),"football_coverage_integrity")
        check(u["testedMatches"]==n,"decision_validation_count")
        check(u["decision"]=="PAS" and u["realBettingEnabled"] is False and u["selections"]==[] and v["liveEnabled"] is False,"research_lock")
    except (KeyError,TypeError,ValueError,AttributeError) as exc:
        errors.append("invalid_schema:"+type(exc).__name__)
    timestamps={name+".json":data[name]["updatedAt"] for name in FILES if isinstance(data.get(name),dict) and isinstance(data[name].get("updatedAt"),str)}
    for name in ("extra_markets","extra_market_archive","odds_continuity"):
        if isinstance(data.get(name),dict) and isinstance(data[name].get("updatedAt"),str):
            timestamps[name+".json"]=data[name]["updatedAt"]
    return {"version":"4.81","updatedAt":datetime.now(timezone.utc).isoformat(),"status":"PASS" if not errors else "FAIL","errors":errors,"mode":"research_only","reportTimestamps":timestamps}

def main():
    data={}
    try:
        for k in FILES:
            data[k]=json.loads(Path(k+".json").read_text(encoding="utf-8"))
        for k in ("extra_markets","extra_market_archive","odds_continuity"):
            try:data[k]=json.loads(Path(k+".json").read_text(encoding="utf-8"))
            except (OSError,ValueError):pass
        report=audit(data)
    except (OSError,ValueError) as exc:
        report={"version":"4.81","updatedAt":datetime.now(timezone.utc).isoformat(),"status":"FAIL","errors":[type(exc).__name__],"mode":"research_only"}
    Path("snapshot_integrity.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False))
    if report["status"]!="PASS": raise SystemExit(1)
if __name__=="__main__": main()
