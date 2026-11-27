"""V5.35: bind descriptive context and historical validation to the daily snapshot."""
import hashlib,json,math
from datetime import datetime
from pathlib import Path
from league_config import LEAGUES
from chronological_statistics_research import EVENTS
from results_source_pilot import TR

FILES=("daily.json","football_context_research.json","historical_metric_coverage.json","h2h_history_research.json","chronological_statistics_research.json")
def digest(raw):
    return hashlib.sha256(raw).hexdigest()
def audit(daily,context,coverage,h2h,validation):
    stamp=datetime.fromisoformat(daily["updatedAt"])
    if stamp.tzinfo is None:raise ValueError("daily timezone")
    day=stamp.astimezone(TR).date().isoformat()
    expected={code for _,code,_ in LEAGUES}
    for report,version,mode in ((context,"5.23","descriptive_research"),(coverage,"5.31","historical_metric_coverage_only"),(h2h,"5.28","descriptive_research"),(validation,"5.34","chronological_research_only")):
        if report.get("version")!=version or report.get("mode")!=mode or report.get("predictionsEnabled") is not False or report.get("decision")!="PAS" or report.get("cutoffExclusive")!=day:raise ValueError("report provenance")
        if len(report["groups"])!=len(expected) or {g["league"] for g in report["groups"]}!=expected:raise ValueError("league coverage")
    if context.get("dailyUpdatedAt")!=daily["updatedAt"] or h2h.get("dailyUpdatedAt")!=daily["updatedAt"]:raise ValueError("snapshot mismatch")
    if coverage.get("modelCalibrated") is not False or context.get("modelCalibrated") is not False:raise ValueError("calibration flag")
    for g in coverage["groups"]:
        a=g["aggregate"];n=a["matches"]
        if type(n) is not int or n<0 or sum(s["matches"] for s in g["seasons"])!=n:raise ValueError("season counts")
        for m in a["metrics"].values():
            if type(m["sample"]) is not int or not 0<=m["sample"]<=n or m["missing"]!=n-m["sample"]:raise ValueError("metric counts")
    if validation.get("modelCalibrated") is not False or validation.get("reliabilityDiagnosticOnly") is not True:raise ValueError("validation flags")
    coverage_by_league={g["league"]:g["aggregate"]["matches"] for g in coverage["groups"]}
    samples={}
    for g in validation["groups"]:
        if g["matches"]!=coverage_by_league[g["league"]] or set(g["metrics"])!=set(EVENTS):raise ValueError("validation coverage")
        for event,m in g["metrics"].items():
            n=m["sample"];k=m["observedEvents"]
            if type(n) is not int or type(k) is not int or not 0<=k<=n<=g["matches"]:raise ValueError("validation counts")
            if sum(v["sample"] for v in m["seasonResults"])!=n or sum(v["observedEvents"] for v in m["seasonResults"])!=k:raise ValueError("validation seasons")
            for name in ("leagueBrier","venueBrier"):
                b=m[name]
                if (n and (type(b) not in (int,float) or not math.isfinite(b) or not 0<=b<=1)) or (not n and b is not None):raise ValueError("validation Brier")
            for method in ("league","venue"):
                v=m["reliability"][method]
                if v["sample"]!=n or len(v["bins"])!=10 or sum(b["sample"] for b in v["bins"])!=n:raise ValueError("validation reliability")
            samples[event]=samples.get(event,0)+n
    fixtures={(f["league"],f["date"],f["match"]) for f in daily["upcoming"]}
    labels={code:label for label,code,_ in LEAGUES}
    for report in (context,h2h):
        for g in report["groups"]:
            keys=[(labels[g["league"]],r["date"],r["match"]) for r in g["rows"]]
            if len(set(keys))!=len(keys) or not set(keys)<=fixtures:raise ValueError("fixture identity")
    return dict(version="5.35",mode="descriptive_research_manifest",dailyUpdatedAt=daily["updatedAt"],cutoffExclusive=day,predictionsEnabled=False,decision="PAS",status="PASS",coverageMatches=sum(g["aggregate"]["matches"] for g in coverage["groups"]),contextLeagues=sum(g["error"] is None for g in context["groups"]),h2hFixtures=sum(len(g["rows"]) for g in h2h["groups"]),validationSamples=samples)
def main():
    raw={name:Path(name).read_bytes() for name in FILES}
    result=audit(*(json.loads(raw[name]) for name in FILES))
    result["sha256"]={name:digest(raw[name]) for name in FILES}
    Path("football_context_manifest.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False))
if __name__=="__main__":main()
