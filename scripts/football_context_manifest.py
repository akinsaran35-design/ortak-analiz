"""V5.32: bind descriptive context and historical coverage to the daily snapshot."""
import hashlib,json
from datetime import datetime
from pathlib import Path
from league_config import LEAGUES
from results_source_pilot import TR

FILES=("daily.json","football_context_research.json","historical_metric_coverage.json","h2h_history_research.json")
def digest(raw):
    return hashlib.sha256(raw).hexdigest()
def audit(daily,context,coverage,h2h):
    stamp=datetime.fromisoformat(daily["updatedAt"])
    if stamp.tzinfo is None:raise ValueError("daily timezone")
    day=stamp.astimezone(TR).date().isoformat()
    expected={code for _,code,_ in LEAGUES}
    for report,version,mode in ((context,"5.23","descriptive_research"),(coverage,"5.31","historical_metric_coverage_only"),(h2h,"5.28","descriptive_research")):
        if report.get("version")!=version or report.get("mode")!=mode or report.get("predictionsEnabled") is not False or report.get("decision")!="PAS" or report.get("cutoffExclusive")!=day:raise ValueError("report provenance")
        if len(report["groups"])!=len(expected) or {g["league"] for g in report["groups"]}!=expected:raise ValueError("league coverage")
    if context.get("dailyUpdatedAt")!=daily["updatedAt"] or h2h.get("dailyUpdatedAt")!=daily["updatedAt"]:raise ValueError("snapshot mismatch")
    if coverage.get("modelCalibrated") is not False or context.get("modelCalibrated") is not False:raise ValueError("calibration flag")
    for g in coverage["groups"]:
        a=g["aggregate"];n=a["matches"]
        if type(n) is not int or n<0 or sum(s["matches"] for s in g["seasons"])!=n:raise ValueError("season counts")
        for m in a["metrics"].values():
            if type(m["sample"]) is not int or not 0<=m["sample"]<=n or m["missing"]!=n-m["sample"]:raise ValueError("metric counts")
    fixtures={(f["league"],f["date"],f["match"]) for f in daily["upcoming"]}
    labels={code:label for label,code,_ in LEAGUES}
    for report in (context,h2h):
        for g in report["groups"]:
            keys=[(labels[g["league"]],r["date"],r["match"]) for r in g["rows"]]
            if len(set(keys))!=len(keys) or not set(keys)<=fixtures:raise ValueError("fixture identity")
    return dict(version="5.32",mode="descriptive_research_manifest",dailyUpdatedAt=daily["updatedAt"],cutoffExclusive=day,predictionsEnabled=False,decision="PAS",status="PASS",coverageMatches=sum(g["aggregate"]["matches"] for g in coverage["groups"]),contextLeagues=sum(g["error"] is None for g in context["groups"]),h2hFixtures=sum(len(g["rows"]) for g in h2h["groups"]))
def main():
    raw={name:Path(name).read_bytes() for name in FILES}
    result=audit(*(json.loads(raw[name]) for name in FILES))
    result["sha256"]={name:digest(raw[name]) for name in FILES}
    Path("football_context_manifest.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False))
if __name__=="__main__":main()
