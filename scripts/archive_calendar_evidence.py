"""Preserve pre-kickoff calendar evidence, without editing forecast records."""
import json
from collections import Counter,defaultdict
from datetime import datetime,timedelta,timezone
from pathlib import Path
from archive_calendar_audit import audit,stamp

def capture(ledger,archives,calendar,daily,odds,now):
    if not isinstance(ledger,dict) or any(not isinstance(x,dict) for x in ledger.values()):
        raise ValueError("invalid calendar ledger")
    out=dict(ledger)
    counts={}
    for kind,archive in archives.items():
        report=audit(archive,calendar,daily,odds,now,kind=="performance")
        counts[kind]=report["counts"]
        if report["status"]!="research_only": continue
        for row in report["rows"]:
            if row["status"]!="review_pending": continue
            kickoff=stamp(row["kickoff"])
            if not stamp(row["recordedAt"])<=now<kickoff: continue
            ident=[kind,row["league"],row["home"],row["away"],row["archivedDate"],row["recordedAt"]]
            key=json.dumps(ident+[row["eventId"],row["corroboratedDate"],row["kickoff"]],ensure_ascii=False)
            if key in out: continue
            out[key]=dict(row,archive=kind,observedAt=now.isoformat(),dailyUpdatedAt=daily["updatedAt"],oddsUpdatedAt=odds["updatedAt"],calendarUpdatedAt=calendar["updatedAt"],calendarSource=calendar.get("source"),calendarSourceUpdatedAt=calendar.get("sourceUpdatedAt"))
    variants=defaultdict(set)
    for r in out.values():
        k=(r["archive"],r["league"],r["home"],r["away"],r["archivedDate"],r["recordedAt"])
        variants[k].add((r["eventId"],r["corroboratedDate"],r["kickoff"]))
    return out,{"version":"4.71","updatedAt":now.isoformat(),"mode":"research_only","observations":len(out),"archiveIdentities":len(variants),"multipleScheduleObservations":sum(len(v)>1 for v in variants.values()),"newObservations":len(out)-len(ledger),"auditCounts":counts,"decision":"PAS"}

def main():
    now=datetime.now(timezone.utc)
    def read(name): return json.loads(Path(name).read_text(encoding="utf-8"))
    path=Path("archive_calendar_evidence.json")
    ledger=read(path) if path.exists() else {}
    archives={"prospective":read("prospective_archive.json"),"performance":read("prediction_archive.json")}
    out,report=capture(ledger,archives,read("fixture_reconciliation.json"),read("daily.json"),read("odds.json"),now)
    path.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    Path("archive_calendar_evidence_status.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False))
if __name__=="__main__": main()
