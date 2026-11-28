"""Bounded public match-summary field availability; not a forecast input."""
import json,math
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

def lineup_quality(rosters,competitors):
    """Count explicitly flagged starters only, never infer lineup from squad size."""
    empty=dict(status="unverified",teamsMatched=0,teamsWithEleven=0,starterCounts=[])
    if not isinstance(rosters,list) or len(rosters)!=2:return empty
    try:
        expected={str(c["team"]["id"]):c["homeAway"] for c in competitors}
        if len(expected)!=2 or set(expected.values())!={"home","away"}:return empty
        seen=set();counts={};matched=0
        for roster in rosters:
            tid=str(roster["team"]["id"])
            if tid not in expected or tid in seen:return empty
            seen.add(tid);matched+=1
            players=roster.get("roster")
            if not isinstance(players,list) or not players:continue
            ids=set();starters=0;valid=True
            for player in players:
                pid=str(player["athlete"]["id"])
                if not pid.isascii() or not pid.isdigit() or pid in ids or type(player.get("starter")) is not bool:
                    valid=False;break
                ids.add(pid)
                starters+=int(player["starter"])
            if valid:counts[expected[tid]]=starters
        eleven=sum(v==11 for v in counts.values())
        return dict(status="source_reported_eleven" if eleven==2 else "incomplete_or_unverified",
                    teamsMatched=matched,teamsWithEleven=eleven,
                    starterCounts=[counts.get(side) for side in ("home","away")])
    except (KeyError,ValueError,TypeError,AttributeError):return empty

STAT_FIELDS=("totalShots","shotsOnTarget","wonCorners","foulsCommitted","yellowCards","redCards","offsides","saves","possessionPct","expectedGoals","expectedGoalsFor","xG")

def statistic_quality(stats,competitors,comp,event):
    """Count valid completed-match statistic fields, never treat pre-match placeholders as observations."""
    empty=dict(status="unverified",teamsMatched=0,fieldsWithTwoTeams=[],fieldCounts={})
    if event.get("state")!="post" or event.get("status")!="STATUS_FULL_TIME":
        return dict(empty,status="not_completed")
    kind=comp.get("status",{}).get("type",{})
    if kind.get("state")!="post" or kind.get("completed") is not True or kind.get("name")!="STATUS_FULL_TIME":
        return empty
    if not isinstance(stats,list) or len(stats)!=2:return empty
    try:
        expected={str(c["team"]["id"]) for c in competitors}
        if len(expected)!=2:return empty
        seen=set(); counts=Counter()
        for row in stats:
            tid=str(row["team"]["id"])
            if tid not in expected or tid in seen:return empty
            seen.add(tid)
            items=row.get("statistics")
            if not isinstance(items,list):continue
            names=Counter(x.get("name") for x in items if isinstance(x,dict) and isinstance(x.get("name"),str))
            for x in items:
                if not isinstance(x,dict):continue
                name=x.get("name")
                if not isinstance(name,str) or name not in STAT_FIELDS or names[name]!=1:continue
                raw=x.get("displayValue")
                if isinstance(raw,bool) or not isinstance(raw,(str,int,float)):continue
                try:
                    value=float(str(raw).strip().rstrip("%") if name=="possessionPct" else raw)
                except (ValueError,TypeError,OverflowError):continue
                if not math.isfinite(value) or value<0:continue
                if name=="possessionPct" and value>100:continue
                if name not in ("possessionPct","expectedGoals","expectedGoalsFor","xG") and not value.is_integer():continue
                counts[name]+=1
        return dict(status="source_observed" if counts else "no_valid_fields",teamsMatched=len(seen),
                    fieldsWithTwoTeams=sorted(k for k,v in counts.items() if v==2),
                    fieldCounts=dict(sorted(counts.items())))
    except (KeyError,ValueError,TypeError,AttributeError):return empty

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
                teamStatistics=presence(stats),explicitXgFieldTeams=xg,
                lineupQuality=lineup_quality(doc.get("rosters"),teams),
                statisticQuality=statistic_quality(stats,teams,comp,event))

def probe(now,reader=read,fixture_reader=public_fixtures):
    output=dict(version="7.24",mode="public_summary_schema_probe",requestsAttempted=0,groups=[],
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
