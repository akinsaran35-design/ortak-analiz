"""Research-only replay of pre-kickoff date evidence against two score feeds."""
import json
from collections import Counter,defaultdict
from datetime import datetime,date,timedelta
from pathlib import Path
from archive_calendar_audit import stamp
from multi_league_results import build_report,APPROVED,SPORTS,TR,read
from nine_league_results_pilot import result_key
from league_config import FIXTURE_CODES

def replay(ledger,archives,now,reader=read):
    indexes={}
    for kind,archive in archives.items():
        idx=defaultdict(list)
        for r in archive.values():
            if kind=="performance":
                h,a=r["match"].split(" – ");code=FIXTURE_CODES[r["league"]]
            else: h,a,code=r["home"],r["away"],r["league"]
            if code not in APPROVED: continue
            idx[(code,result_key(h,code,SPORTS[code]),result_key(a,code,SPORTS[code]),r["date"])].append(r)
        indexes[kind]=idx
    grouped=defaultdict(list)
    for e in ledger.values():
        grouped[(e["archive"],e["league"],e["home"],e["away"],e["archivedDate"],e["recordedAt"])].append(e)
    rows=[]; query={}; pending=defaultdict(list)
    for ident,observations in sorted(grouped.items()):
        kind,code,h,a,old,recorded=ident
        row=dict(archive=kind,league=code,home=h,away=a,archivedDate=old,recordedAt=recorded,status="invalid_evidence")
        rows.append(row)
        try:
            if code not in APPROVED or kind not in indexes: continue
            variants={(e["eventId"],e["corroboratedDate"],e["kickoff"]) for e in observations}
            if len(variants)!=1: row["status"]="schedule_conflict";continue
            event,new,kickoff=next(iter(variants)); k=stamp(kickoff)
            row.update(eventId=event,corroboratedDate=new,kickoff=kickoff)
            d=date.fromisoformat(new)
            if old==new or abs((d-date.fromisoformat(old)).days)>2 or k.astimezone(TR).date()!=d: continue
            if stamp(recorded).astimezone(TR).date()>=d: continue
            if not all(e["status"]=="review_pending" and stamp(recorded)<=stamp(e["observedAt"])<k and stamp(e["observedAt"])<=now for e in observations): continue
            hk,ak=result_key(h,code,SPORTS[code]),result_key(a,code,SPORTS[code])
            idx=indexes[kind]; originals=idx[(code,hk,ak,old)]
            if len(originals)!=1 or idx.get((code,hk,ak,new)): row["status"]="duplicate_risk";continue
            rec=originals[0]
            if rec["recordedAt"]!=recorded: continue
            if rec["result"] is not None: row["status"]="already_settled";continue
            if d>=now.astimezone(TR).date() or k>=now: row["status"]="awaiting_match";continue
            if d<now.astimezone(TR).date()-timedelta(days=14): row["status"]="outside_window";continue
            q=(code,new,hk,ak)
            query.setdefault(q,dict(league=code,date=new,home=h,away=a,result=None))
            pending[q].append(row);row["status"]="awaiting_sources"
        except (KeyError,ValueError,TypeError,AttributeError): continue
    feed=build_report(query,now.astimezone(TR),reader)
    for g in feed["groups"]:
        code=g["league"]
        for r in g["rows"]:
            q=(code,r["date"],result_key(r["home"],code,SPORTS[code]),result_key(r["away"],code,SPORTS[code]))
            for row in pending.get(q,[]):
                row["status"]="research_score_verified" if r["status"]=="corroborated" and not g["errors"] else r["status"]
                row.update(csv=r["csv"],espn=r["espn"],sources=g["sources"])
    return {"version":"4.72","updatedAt":now.isoformat(),"mode":"research_only","counts":dict(Counter(r["status"] for r in rows)),"rows":rows,"sourceErrors":[{"league":g["league"],"date":g["date"],"errors":g["errors"]} for g in feed["groups"] if g["errors"]],"decision":"PAS"}

def main():
    def load(p): return json.loads(Path(p).read_text())
    p=Path("archive_calendar_evidence.json")
    report=replay(load(p) if p.exists() else {},{"prospective":load("prospective_archive.json"),"performance":load("prediction_archive.json")},datetime.now(TR))
    Path("archive_calendar_result_replay.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({"counts":report["counts"],"sourceErrors":report["sourceErrors"]},ensure_ascii=False))
if __name__=="__main__": main()
