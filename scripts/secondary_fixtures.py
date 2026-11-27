"""Independent fixture feed; never automatically settle or predict."""
import os,json
from datetime import datetime,timedelta,timezone
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError
from pathlib import Path
def parse(payload):
    rows=[];seen=set()
    for m in payload["matches"]:
        ident=m["id"]; c=m["competition"]["id"]; h=m["homeTeam"]; a=m["awayTeam"]
        stamp=datetime.fromisoformat(m["utcDate"].replace("Z","+00:00"))
        if type(ident)!=int or type(c)!=int or ident in seen or stamp.tzinfo is None or type(h["id"])!=int or type(a["id"])!=int or h["id"]==a["id"]:raise ValueError("identity")
        seen.add(ident)
        score=None
        if m["status"]=="FINISHED" and m["score"]["duration"]=="REGULAR":
            f=m["score"]["fullTime"];score=[f["home"],f["away"]]
            if any(type(v)!=int or v<0 for v in score):raise ValueError("score")
        rows.append(dict(eventId=ident,competitionId=c,kickoff=stamp.isoformat(),home=h["name"],away=a["name"],status=m["status"],score=score))
    return rows
def build(token,now):
    out=dict(version="5.67",source="football-data.org",mode="independent_research",rows=[],status="credentials_missing",usedForSettlement=False,predictionsEnabled=False)
    if not token:return out
    day=now.date();url="https://api.football-data.org/v4/matches?dateFrom="+str(day-timedelta(days=1))+"&dateTo="+str(day+timedelta(days=2))
    try:
        with urlopen(Request(url,headers={"X-Auth-Token":token}),timeout=20) as response:out["rows"]=parse(json.load(response))
        out["status"]="observed" if out["rows"] else "empty"
    except HTTPError as e:out["status"]="HTTP_"+str(e.code)
    except (URLError,OSError,ValueError,TypeError,KeyError):out["status"]="source_or_schema_error"
    return out
if __name__=="__main__":
    r=build(os.environ.get("FOOTBALL_DATA_TOKEN"),datetime.now(timezone.utc))
    Path("secondary_fixtures.json").write_text(json.dumps(r,indent=2))
    print(r["status"],len(r["rows"]))
