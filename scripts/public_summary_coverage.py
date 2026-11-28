"""Bounded public match-summary field availability; not a forecast input."""
import json
from datetime import datetime,timedelta
from collections import Counter
from results_source_pilot import TR,read
from referee_team_name_evidence import public_fixtures
from nine_league_results_pilot import SOURCES

# Three-league pilot, at most one pre and one completed event per league.
PILOT=("en.1","de.1","nl.1")
def presence(value):
    if value is None:return "missing"
    if not isinstance(value,list):return "unexpected_shape"
    return "nonempty" if value else "empty"

def inspect(doc,event):
    if not isinstance(doc,dict):raise ValueError("summary schema")
    header=doc["header"]
    if str(header["id"])!=event["eventId"]:raise ValueError("event identity")
    comp,=header["competitions"]
    if str(comp["id"])!=event["eventId"]:raise ValueError("competition identity")
    teams=comp["competitors"]
    names={x["homeAway"]:x["team"]["displayName"] for x in teams}
    if len(teams)!=2 or names!={"home":event["home"],"away":event["away"]}:raise ValueError("team identity")
    if datetime.fromisoformat(comp["date"].replace("Z","+00:00"))!=datetime.fromisoformat(event["kickoff"]):raise ValueError("kickoff")
    box=doc.get("boxscore")
    stats=box.get("teams") if isinstance(box,dict) else None
    xg=0
    if isinstance(stats,list):
        for team in stats:
            if not isinstance(team,dict):continue
            items=team.get("statistics")
            if isinstance(items,list) and any(isinstance(v,dict) and v.get("name") in ("expectedGoals","expectedGoalsFor","xG") for v in items):xg+=1
    return dict(rosters=presence(doc.get("rosters")),injuries=presence(doc.get("injuries")),
                teamStatistics=presence(stats),explicitXgFieldTeams=xg)

def probe(now,reader=read,fixture_reader=public_fixtures):
    output=dict(version="7.22",mode="public_summary_schema_probe",requestsAttempted=0,groups=[],
                predictionsEnabled=False,decision="PAS")
    today=now.astimezone(TR).date()
    for offset,state in ((0,"pre"),(-1,"post")):
        day=(today+timedelta(days=offset)).isoformat()
        groups=fixture_reader(day,reader=reader,codes=PILOT)
        for code in PILOT:
            result=dict(league=code,day=day,state=state,status="no_eligible_fixture")
            group=next((g for g in groups if g["league"]==code),None)
            if not group or group.get("error"):result["status"]="source_unavailable"
            else:
                rows=[r for r in group["rows"] if r["state"]==state and r["eventId"].isascii() and r["eventId"].isdigit() and r["status"]==("STATUS_SCHEDULED" if state=="pre" else "STATUS_FULL_TIME")]
                if rows:
                    event=sorted(rows,key=lambda r:(r["kickoff"],r["eventId"]))[0]
                    source=SOURCES[code][1] if code in SOURCES else code
                    output["requestsAttempted"]+=1
                    try:
                        doc=json.loads(reader(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{source}/summary?event={event['eventId']}"))
                        result.update(status="checked",**inspect(doc,event))
                    except (OSError,ValueError,TypeError,KeyError,AttributeError) as exc:
                        result.update(status="unverified",error=type(exc).__name__)
            output["groups"].append(result)
    return output
if __name__=="__main__":
    print(json.dumps(probe(datetime.now(TR)),ensure_ascii=False))
