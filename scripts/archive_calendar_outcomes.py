"""Persist corroborated corrected-date research outcomes without settling forecast archives."""
import json,math
from collections import defaultdict,Counter
from datetime import datetime,date,timedelta
from pathlib import Path
from archive_calendar_audit import stamp,TR
from multi_league_results import APPROVED,source_urls
from league_config import FIXTURE_CODES

FIELDS=("archive","league","home","away","archivedDate","recordedAt")
def identity(row): return tuple(row[x] for x in FIELDS)
def score_valid(x): return isinstance(x,list) and len(x)==2 and all(type(v) is int and v>=0 for v in x)
def probability(x): return type(x) in (int,float) and math.isfinite(x) and 0<=x<=1

def collect(ledger,replay,archives,now):
    if not isinstance(ledger,dict): raise ValueError("invalid outcome ledger")
    out=dict(ledger)
    index=defaultdict(list)
    dates=Counter()
    for kind,archive in archives.items():
        for rec in archive.values():
            if kind=="performance":
                h,a=rec["match"].split(" – ");code=FIXTURE_CODES[rec["league"]]
            else: h,a,code=rec["home"],rec["away"],rec["league"]
            index[(kind,code,h,a,rec["date"],rec["recordedAt"])].append(rec)
            dates[(kind,code,h,a,rec["date"])]+=1
    try:
        fresh=replay["version"]=="4.72" and replay["mode"]=="research_only" and timedelta(0)<=now-stamp(replay["updatedAt"])<=timedelta(minutes=30)
    except (KeyError,ValueError,TypeError,AttributeError): fresh=False
    if fresh:
        for row in replay["rows"]:
            try:
                if row["status"]!="research_score_verified": continue
                ident=identity(row);kind,code,h,a,old,recorded=ident
                new=row["corroboratedDate"];kick=stamp(row["kickoff"])
                if code not in APPROVED or row["sources"]!=list(source_urls(code,new)): continue
                if not score_valid(row["csv"]) or row["csv"]!=row["espn"]: continue
                if not row["eventId"] or old==new or abs((date.fromisoformat(new)-date.fromisoformat(old)).days)>2: continue
                if kick.astimezone(TR).date()!=date.fromisoformat(new) or not stamp(recorded)<kick<now: continue
                if date.fromisoformat(new)>=now.astimezone(TR).date(): continue
                if len(index[ident])!=1 or dates[ident[:4]+(new,)]: continue
                rec=index[ident][0]
                if rec["result"] is not None: continue
                key=json.dumps(list(ident)+[row["eventId"],new,row["kickoff"],row["csv"]],ensure_ascii=False)
                if key not in out:
                    out[key]={**{k:row[k] for k in FIELDS},"eventId":row["eventId"],"corroboratedDate":new,"kickoff":row["kickoff"],"result":list(row["csv"]),"sources":list(row["sources"]),"observedAt":now.isoformat(),"replayUpdatedAt":replay["updatedAt"]}
            except (KeyError,TypeError,ValueError,AttributeError): continue
    groups=defaultdict(list)
    for e in out.values(): groups[identity(e)].append(e)
    status=Counter(); pairs=defaultdict(list); eligible_events=set()
    for ident,items in groups.items():
        variants={(x["eventId"],x["corroboratedDate"],x["kickoff"],tuple(x["result"])) for x in items}
        if len(variants)!=1: status["conflicting_observations"]+=1;continue
        e=items[0];kind=ident[0];rec=index.get(ident,[])
        if len(rec)!=1 or dates[ident[:4]+(e["corroboratedDate"],)] or rec[0]["result"] is not None:
            status["excluded_archive_state"]+=1;continue
        rec=rec[0];h,a=e["result"]
        if kind=="prospective":
            p={k:rec.get(k) for k in ("old","candidate","baseline")}
            actual={k:int(h+a>=3) for k in p}
        else:
            labels={"1.5 Üst":int(h+a>=2),"2.5 Üst":int(h+a>=3),"KG Var":int(h>0 and a>0)}
            p={k:rec["markets"].get(k) for k in labels}
            p={k:v/100 if type(v) in (int,float) else None for k,v in p.items()}
            actual=labels
        if not all(probability(x) for x in p.values()): status["invalid_probability"]+=1;continue
        status["eligible_research"]+=1
        eligible_events.add(e["eventId"])
        for market,v in p.items(): pairs[(kind,market)].append((v,actual[market]))
    metrics={kind:{} for kind in archives}
    for (kind,market),rows in pairs.items():
        metrics[kind][market]={"tested":len(rows),"brier":sum((p-y)**2 for p,y in rows)/len(rows)}
    return out,{"version":"4.82","updatedAt":now.isoformat(),"mode":"research_only","observations":len(out),"newObservations":len(out)-len(ledger),"archiveIdentities":len(groups),"uniqueEligibleEvents":len(eligible_events),"counts":dict(status),"metrics":metrics,"decision":"PAS","includedInMainValidation":False}

def main():
    def load(name): return json.loads(Path(name).read_text(encoding="utf-8"))
    path=Path("archive_calendar_outcomes.json")
    ledger,report=collect(load(path) if path.exists() else {},load("archive_calendar_result_replay.json"),{"prospective":load("prospective_archive.json"),"performance":load("prediction_archive.json")},datetime.now(TR))
    path.write_text(json.dumps(ledger,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    Path("archive_calendar_outcome_status.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False))
if __name__=="__main__": main()
