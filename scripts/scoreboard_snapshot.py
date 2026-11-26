"""Public scoreboard observations only, never used to settle or predict matches."""
import json
from datetime import datetime,date,timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from results_source_pilot import read,TR
from nine_league_results_pilot import SOURCES
from league_config import LEAGUES

def parse(payload,day):
    if not isinstance(payload.get("events"),list): raise ValueError("events schema")
    rows={};blocked=set();invalid=0
    for e in payload["events"]:
        try:
            comp,=e["competitions"]
            kickoff=datetime.fromisoformat(comp.get("date",e["date"]).replace("Z","+00:00"))
            if kickoff.tzinfo is None: raise ValueError("timezone")
            if kickoff.astimezone(TR).date().isoformat()!=day: continue
            teams={x["homeAway"]:x for x in comp["competitors"]}
            if len(comp["competitors"])!=2 or set(teams)!={"home","away"}: raise ValueError("teams")
            h,a=teams["home"],teams["away"]
            status=comp.get("status",e.get("status",{}))
            kind=status["type"]
            state=kind["state"]
            if state not in ("pre","in","post"): raise ValueError("state")
            names=[x["team"]["displayName"] for x in (h,a)]
            if not all(isinstance(x,str) and x.strip() for x in names) or names[0]==names[1]: raise ValueError("names")
            ident=str(e["id"])
            if not ident.isdigit(): raise ValueError("id")
            score=None
            if state=="in" or (state=="post" and kind.get("completed") is True):
                values=[str(x.get("score","")) for x in (h,a)]
                if not all(x.isascii() and x.isdigit() for x in values): raise ValueError("score")
                score=[int(x) for x in values]
            row=dict(eventId=ident,home=names[0],away=names[1],kickoff=kickoff.isoformat(),state=state,status=str(kind.get("name","")),clock=str(status.get("displayClock") or ""),score=score)
            if ident in rows and rows[ident]!=row: blocked.add(ident)
            rows[ident]=row
        except (KeyError,ValueError,TypeError,AttributeError): invalid+=1
    return [v for k,v in rows.items() if k not in blocked],invalid+len(blocked)

def build(now,reader=read,query_date=None):
    day=query_date or now.astimezone(TR).date().isoformat()
    date.fromisoformat(day)
    def group(item):
        name,code,_=item
        url="https://site.api.espn.com/apis/site/v2/sports/soccer/"+SOURCES[code][1]+"/scoreboard?dates="+day.replace("-","")
        result=dict(league=code,leagueName=name,source=url,rows=[],invalid=0,error=None)
        try:
            result["rows"],result["invalid"]=parse(json.loads(reader(url)),day)
        except (OSError,ValueError,KeyError,TypeError,AttributeError) as exc: result["error"]=type(exc).__name__
        return result
    with ThreadPoolExecutor(max_workers=4) as pool:
        groups=list(pool.map(group,LEAGUES))
    return dict(version="4.90",updatedAt=now.isoformat(),date=day,mode="scoreboard_snapshot" if query_date is None else "source_probe",source="ESPN",groups=groups,loadedLeagues=sum(g["error"] is None for g in groups),eventCount=sum(len(g["rows"]) for g in groups),inProgress=sum(r["state"]=="in" for g in groups for r in g["rows"]),realTime=False,usedForSettlement=False,usedForPredictions=False)

def main():
    report=build(datetime.now(TR))
    Path("scoreboard_snapshot.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k!="groups"},ensure_ascii=False))
    print("League errors:",[{"league":g["league"],"error":g["error"],"invalid":g["invalid"]} for g in report["groups"] if g["error"] or g["invalid"]])
if __name__=="__main__":main()
