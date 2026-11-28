"""Bounded private API-Football referee availability diagnostic."""
import json,os
from datetime import datetime,timedelta
from collections import Counter
from api_football_access_probe import request
from results_source_pilot import TR

def inspect(doc,day):
    if doc.get("errors") not in ({},[]):raise ValueError("provider_error")
    rows=doc["response"]
    paging=doc["paging"]
    if not isinstance(rows,list) or doc.get("results")!=len(rows) or paging.get("current")!=1 or paging.get("total")!=1:raise ValueError("incomplete_page")
    counts={};seen=set()
    for row in rows:
        f=row["fixture"];league=row["league"];i=f["id"];lid=league["id"]
        t=datetime.fromisoformat(f["date"])
        if type(i) is not int or type(lid) is not int or i<=0 or lid<=0 or i in seen or t.tzinfo is None or t.astimezone(TR).date().isoformat()!=day:raise ValueError("fixture_identity")
        seen.add(i)
        status=f["status"]["short"]
        if status not in ("NS","FT","AET","PEN"):continue
        key=(lid,status=="NS")
        c=counts.setdefault(key,Counter())
        c["fixtures"]+=1
        ref=f.get("referee")
        if isinstance(ref,str) and ref.strip().casefold() not in ("","unknown","n/a","na","-","tbd"):c["withReferee"]+=1
    return [{"providerLeagueId":k[0],"scheduled":k[1],"fixtures":v["fixtures"],"withReferee":v["withReferee"]} for k,v in sorted(counts.items())]

def probe(key,now,reader=request,fixture_reader=None):
    out=dict(version="7.20",decision="PAS",mode="private_coverage_probe",status="missing_secret",requestsAttempted=0,days=[],predictionsEnabled=False)
    if not key:return out
    try:
        status=reader(key,"status")
        if status.get("errors") not in ({},[]):raise ValueError("status_error")
        s=status["response"];used=s["requests"]["current"];limit=s["requests"]["limit_day"]
        if type(used) is not int or type(limit) is not int or not 0<=used<=limit:raise ValueError("quota")
        out["remainingBefore"]=limit-used
        if s["subscription"].get("active") is not True or s["subscription"].get("plan")!="Free" or limit-used<22:
            out["status"]="quota_or_plan_guard";return out
        out["status"]="checked"
        for offset in (-1,0):
            day=(now.astimezone(TR).date()+timedelta(days=offset)).isoformat()
            out["requestsAttempted"]+=1
            try:
                doc=reader(key,"fixtures?date="+day+"&timezone=Europe%2FIstanbul")
                groups=inspect(doc,day)
                entry=dict(date=day,groups=groups)
                if offset==0 and fixture_reader is not None:
                    try:
                        from referee_fixture_identity import match
                        fixtures=fixture_reader(day)
                        result=match(doc,fixtures)
                        entry["fixtureJoin"]={k:result[k] for k in ("eligibleIdentities","matched","withReferee","diagnostics","aliasShadow","sourceNameShadow")}
                        entry["fixtureJoin"]["status"]="checked"
                    except Exception as exc:
                        entry["fixtureJoin"]=dict(status="unverified",error=type(exc).__name__)
                out["days"].append(entry)
            except Exception as exc:
                out["status"]="incomplete"
                out["days"].append(dict(date=day,error=type(exc).__name__))
                break
    except Exception as exc:
        out.update(status="unverified",error=type(exc).__name__)
    return out

def public_fixtures(day):
    from referee_team_name_evidence import public_fixtures as load
    return load(day)

if __name__=="__main__":
    r=probe(os.environ.get("API_FOOTBALL_KEY","").strip(),datetime.now(TR),fixture_reader=public_fixtures)
    print(json.dumps(r,ensure_ascii=False))
    if r["status"]!="checked":raise SystemExit(1)
