"""Read-only per-league prospective model diagnostics; no forecast backfill."""
import json
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from prospective_markets import summarize,MARKETS
from league_config import FIXTURE_CODES

def build(archive,now):
    groups=defaultdict(dict)
    for k,r in archive.items():
        groups[r["league"]][k]=r
    leagues={}
    for code in sorted(set(FIXTURE_CODES.values())|set(groups)):
        rows=groups.get(code,{})
        markets=summarize(rows,now,include_calibration=True)
        for x in markets.values():
            x["sampleAdequate"]=x["tested"]>=500 and x["invalid"]==0
            x["candidateMinusClassic"]=x["scores"]["candidate"]-x["scores"]["old"] if x["tested"] else None
            x["candidateMinusBaseline"]=x["scores"]["candidate"]-x["scores"]["baseline"] if x["tested"] else None
        leagues[code]={"recorded":len(rows),"markets":markets}
    return {"version":"4.88","updatedAt":now.isoformat(),"mode":"research_only","decision":"PAS","realBettingEnabled":False,"recorded":len(archive),"calibrationVersion":"5.03","overallCalibration":{m:x["calibration"] for m,x in summarize(archive,now,include_calibration=True).items()},"leagues":leagues}

def main():
    root=Path(__file__).resolve().parent.parent
    archive=json.loads((root/"prospective_archive.json").read_text(encoding="utf-8"))
    validation=json.loads((root/"prospective_validation.json").read_text(encoding="utf-8"))
    now=datetime.fromisoformat(validation["updatedAt"])
    report=build(archive,now)
    if validation.get("classificationVersion") is None:
        for entry in report["leagues"].values():
            for x in entry["markets"].values():x.pop("classification",None)
    for market in MARKETS:
        expected=validation["marketResearch"][market]
        for k in ("tested","pending","legacyWithoutForecast","invalid"):
            if sum(v["markets"][market][k] for v in report["leagues"].values())!=expected[k]:
                raise ValueError("league reconciliation: "+market+"/"+k)
    (root/"prospective_leagues.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("League research:",len(report["leagues"]),"leagues,",report["recorded"],"records; research only.")
if __name__=="__main__": main()
