"""V4.75 structural integrity check for the complete research snapshot."""
import json
from pathlib import Path
from datetime import datetime,timezone

FILES=("daily","odds","matching","prospective_archive","prospective_validation","prediction_archive","performance","data_quality","archive_calendar_evidence","archive_calendar_evidence_status","archive_calendar_result_replay","unified_decision")

def audit(data):
    errors=[]
    def check(ok,label):
        if not ok: errors.append(label)
    try:
        d,o,m,a,v,p,f,q,e,s,r,u=(data[k] for k in FILES)
        check(d["candidateCount"]==len(d["candidates"]),"candidate_count")
        check(d["upcomingCount"]==len(d["upcoming"]),"fixture_count")
        check(o["eventCount"]==len(o["events"]),"odds_count")
        check(m["matchedCount"]==len(m["matched"]) and m["unmatchedCount"]==len(m["unmatched"]) and m["matchedCount"]+m["unmatchedCount"]==d["candidateCount"],"matching_count")
        n=sum(x["result"] is not None for x in a.values())
        check((v["recorded"],v["tested"],v["pending"])==(len(a),n,len(a)-n),"prospective_count")
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
        check(u["testedMatches"]==n,"decision_validation_count")
        check(u["decision"]=="PAS" and u["realBettingEnabled"] is False and u["selections"]==[] and v["liveEnabled"] is False,"research_lock")
    except (KeyError,TypeError,ValueError,AttributeError) as exc:
        errors.append("invalid_schema:"+type(exc).__name__)
    return {"version":"4.75","updatedAt":datetime.now(timezone.utc).isoformat(),"status":"PASS" if not errors else "FAIL","errors":errors,"mode":"research_only"}

def main():
    data={}
    try:
        for k in FILES:
            data[k]=json.loads(Path(k+".json").read_text(encoding="utf-8"))
        report=audit(data)
    except (OSError,ValueError) as exc:
        report={"version":"4.75","updatedAt":datetime.now(timezone.utc).isoformat(),"status":"FAIL","errors":[type(exc).__name__],"mode":"research_only"}
    Path("snapshot_integrity.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False))
    if report["status"]!="PASS": raise SystemExit(1)
if __name__=="__main__": main()
