"""Verify real non-empty responses on archived and upcoming dates, without publishing them as live."""
import json
from datetime import datetime,timedelta
from pathlib import Path
from scoreboard_snapshot import build,TR
def main():
    now=datetime.now(TR)
    archive=json.loads(Path("prospective_archive.json").read_text(encoding="utf-8"))
    settled=sorted({r["date"] for r in archive.values() if r["result"] is not None and r["date"]<now.date().isoformat()})
    if not settled: raise ValueError("no previously settled dates")
    dates=[settled[-1],(now.date()+timedelta(days=1)).isoformat()]
    reports=[build(now,query_date=d) for d in dates]
    for report in reports:
        print(json.dumps({k:v for k,v in report.items() if k!="groups"},ensure_ascii=False))
        print("States:",{state:sum(r["state"]==state for g in report["groups"] for r in g["rows"]) for state in ("pre","in","post")})
        print("Source errors:",[(g["league"],g["error"],g["invalid"]) for g in report["groups"] if g["error"] or g["invalid"]])
    assert any(r["state"]=="post" and r["score"] is not None for g in reports[0]["groups"] for r in g["rows"]), "no real past score observed"
    Path("scoreboard_source_probe.json").write_text(json.dumps(reports,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
if __name__=="__main__":main()
