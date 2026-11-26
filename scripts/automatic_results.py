"""Guarded automatic dual-source Championship settlement input."""
import json
from datetime import datetime,timedelta
from pathlib import Path
from results_source_pilot import build_report,TR

def verified_rows(report,now):
    try:
        stamp=datetime.fromisoformat(report["updatedAt"])
        if not timedelta(0)<=now-stamp<=timedelta(minutes=30) or report["errors"]: return []
        sources=report["sources"]
        csv=[s for s in sources if s.startswith("https://football-data.co.uk/mmz4281/") and s.endswith("/E1.csv")]
        if len(csv)!=1: return []
        out=[]
        for row in report["rows"]:
            day=row["date"]
            espn="https://site.api.espn.com/apis/site/v2/sports/soccer/eng.2/scoreboard?dates="+day.replace("-","")
            result=row["csv"]
            if row["status"]!="corroborated" or result!=row["espn"] or espn not in sources: continue
            if not isinstance(result,list) or len(result)!=2 or not all(type(x) is int and x>=0 for x in result): continue
            out.append(dict(date=day,league="en.2",home=row["home"],away=row["away"],result=result,sources=[csv[0],espn]))
        return out
    except (ValueError,TypeError,KeyError,AttributeError): return []

def main():
    now=datetime.now(TR)
    archive=json.loads(Path("prospective_archive.json").read_text())
    report=build_report(archive,now)
    rows=verified_rows(report,datetime.now(TR))
    report["automaticVerifiedCount"]=len(rows)
    Path("results_source_pilot.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    print("Dual-source results:",len(rows),"of",report["records"],"errors:",report["errors"])

if __name__=="__main__": main()
