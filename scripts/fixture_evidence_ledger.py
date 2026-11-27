"""Read-only reconciliation of verified fixture IDs across audit reports."""
import json
import sys
from collections import defaultdict
from pathlib import Path

def reconcile(reports):
    observations=[]
    for label,report in reports:
        rows=report["verifiedScoreIds"]
        if not isinstance(rows,list):raise ValueError("invalid verifiedScoreIds")
        for row in rows:
            league=row["league"]
            p,s=str(row["primaryId"]),str(row["secondaryId"])
            if not isinstance(league,str) or not league or p in ("","None") or s in ("","None"):raise ValueError("invalid fixture identity")
            score=row.get("score")
            if score is not None and (not isinstance(score,list) or len(score)!=2 or any(type(n) is not int or n<0 for n in score)):raise ValueError("invalid score")
            observations.append((label,league,p,s,tuple(score) if score is not None else None,row.get("kickoff")))
    primary=defaultdict(set);secondary=defaultdict(set);groups=defaultdict(list)
    for label,league,p,s,score,kickoff in observations:
        primary[p].add((league,s))
        secondary[s].add((league,p))
        groups[(league,p,s)].append((label,score,kickoff))
    verified=[];conflicts=[]
    for (league,p,s),rows in sorted(groups.items()):
        scores={score for _,score,_ in rows if score is not None}
        stamps={stamp for _,_,stamp in rows if stamp is not None}
        entry=dict(league=league,primaryId=p,secondaryId=s,reports=sorted({label for label,_,_ in rows}))
        reasons=[]
        if len(primary[p])!=1 or len(secondary[s])!=1:reasons.append("identity_conflict")
        if len(scores)>1:reasons.append("score_conflict")
        if len(stamps)>1:reasons.append("kickoff_conflict")
        if reasons:
            conflicts.append(dict(entry,reasons=reasons))
        else:
            verified.append(dict(entry,score=list(next(iter(scores))) if scores else None,kickoff=next(iter(stamps)) if stamps else None))
    from collections import Counter
    quality_by_report={label:report.get("sourceQualityGate","unknown") for label,report in reports}
    passing=[x for x in verified if any(quality_by_report[label]=="success" for label in x["reports"])]
    periods=[]
    for label,report in reports:
        periods.append(dict(report=label,month=report.get("month"),sourceRun=report.get("sourceRun"),sourceQualityGate=quality_by_report[label],observations=len(report["verifiedScoreIds"]),uniqueReconciled=sum(label in x["reports"] for x in verified),scopeCoverage=report.get("scopeCoverage")))
    return dict(mode="research_only",observationCount=len(observations),uniqueVerifiedCount=len(verified),duplicateObservations=len(observations)-len(groups),conflictCount=len(conflicts),passingWindowUniqueCount=len(passing),otherWindowUniqueCount=len(verified)-len(passing),withExplicitScoreCount=sum(x["score"] is not None for x in verified),byLeague=dict(sorted(Counter(x["league"] for x in verified).items())),periods=periods,verified=verified,conflicts=conflicts,productionEnabled=False)

def self_test():
    a=dict(league="en.1",primaryId="p",secondaryId=1,score=[2,1],kickoff="2026-05-01T12:00:00Z")
    b=dict(a,primaryId="q",secondaryId=2)
    def report(*rows):return dict(verifiedScoreIds=list(rows))
    result=reconcile([("one",report(a,b)),("two",report(a))])
    assert result["uniqueVerifiedCount"]==2 and result["duplicateObservations"]==1
    assert reconcile([("one",report(a)),("two",report(dict(a,score=[1,1])))])["uniqueVerifiedCount"]==0
    assert reconcile([("one",report(a)),("two",report(dict(a,secondaryId=2)))])["conflictCount"]==2
    assert reconcile([("one",report(a)),("two",report(dict(a,primaryId="z")))])["conflictCount"]==2
    assert reconcile([("one",report(a)),("two",report(dict(a,kickoff="2026-05-01T13:00:00Z")))])["conflictCount"]==1
    mixed=reconcile([("pass",dict(report(a),sourceQualityGate="success")),("fail",dict(report(a,b),sourceQualityGate="failure"))])
    assert mixed["uniqueVerifiedCount"]==2 and mixed["passingWindowUniqueCount"]==1 and mixed["otherWindowUniqueCount"]==1
    assert mixed["byLeague"]=={"en.1":2} and mixed["withExplicitScoreCount"]==2
    assert mixed["periods"][1]["sourceQualityGate"]=="failure"
    print("Fixture ledger self-tests passed")

if __name__=="__main__":
    if sys.argv[1:]==["--self-test"]:self_test()
    elif len(sys.argv)>1:
        reports=[(str(Path(p)),json.loads(Path(p).read_text())) for p in sys.argv[1:]]
        result=reconcile(reports)
        Path("fixture_evidence_ledger.json").write_text(json.dumps(result,indent=2))
        print(json.dumps({k:v for k,v in result.items() if k not in ("verified","conflicts")}))
    else:raise SystemExit("Supply audit report paths or --self-test")
