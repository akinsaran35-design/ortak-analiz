"""Independent fixture feed; never automatically settle or predict."""
import os,json
from datetime import datetime,timedelta,timezone
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError
from pathlib import Path
def parse(payload):
    rows=[];seen=set(); rejected=0
    counts={}
    for m in payload["matches"]:
        ident=m.get("id")
        counts[ident]=counts.get(ident,0)+1
    for m in payload["matches"]:
        ident=m["id"]; c=m["competition"]["id"]; h=m["homeTeam"]; a=m["awayTeam"]
        stamp=datetime.fromisoformat(m["utcDate"].replace("Z","+00:00"))
        if type(ident)!=int or type(c)!=int or counts.get(ident)!=1 or stamp.tzinfo is None or type(h["id"])!=int or type(a["id"])!=int or h["id"]==a["id"]:
            rejected+=1
            continue
        seen.add(ident)
        score=None
        if m["status"]=="FINISHED" and m["score"]["duration"]=="REGULAR":
            f=m["score"]["fullTime"];score=[f["home"],f["away"]]
            if any(type(v)!=int or v<0 for v in score):
                rejected+=1
                continue
        rows.append(dict(eventId=ident,competitionId=c,kickoff=stamp.isoformat(),home=h["name"],away=a["name"],status=m["status"],score=score))
    return rows,rejected
def build(token,now,date_from=None,date_to=None):
    out=dict(version="5.67",source="football-data.org",mode="independent_research",rows=[],status="credentials_missing",usedForSettlement=False,predictionsEnabled=False)
    if not token:return out
    day=now.date();url="https://api.football-data.org/v4/matches?dateFrom="+str(date_from or day-timedelta(days=1))+"&dateTo="+str(date_to or day+timedelta(days=2))
    try:
        with urlopen(Request(url,headers={"X-Auth-Token":token}),timeout=20) as response:out["rows"],out["rejectedRows"]=parse(json.load(response))
        out["status"]="observed" if out["rows"] else "empty"
    except HTTPError as e:out["status"]="HTTP_"+str(e.code)
    except (URLError,OSError,ValueError,TypeError,KeyError) as exc:
        out["status"]="source_or_schema_error"
        out["errorType"]=type(exc).__name__
        if isinstance(exc,KeyError):out["missingField"]=str(exc)[:80]
        elif isinstance(exc,ValueError):out["validationFailure"]=str(exc) if str(exc) in ("identity","score") else "invalid_value"
        elif isinstance(exc,URLError):out["networkErrorType"]=type(exc.reason).__name__
    return out
if __name__=="__main__":
    r=build(os.environ.get("FOOTBALL_DATA_TOKEN"),datetime.now(timezone.utc))
    Path("secondary_fixtures.json").write_text(json.dumps(r,indent=2))
    print(r["status"],len(r["rows"]),{k:v for k,v in r.items() if k in ("errorType","missingField","validationFailure","networkErrorType","rejectedRows")})
