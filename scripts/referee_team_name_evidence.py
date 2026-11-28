"""Public ESPN name evidence for private referee research only."""
import json
from concurrent.futures import ThreadPoolExecutor
from scoreboard_snapshot import parse
from results_source_pilot import read
from nine_league_results_pilot import SOURCES
from league_config import LEAGUES
from extra_historical_metric_coverage import LEAGUES as EXTRA

def attach_names(payload,day):
    rows,bad=parse(payload,day)
    names={}
    duplicates=set()
    for e in payload["events"]:
        try:
            ident=str(e["id"])
            comp,=e["competitions"]
            teams={x["homeAway"]:x["team"] for x in comp["competitors"]}
            if len(comp["competitors"])!=2 or set(teams)!={"home","away"}:continue
            info={}
            for side,team in teams.items():
                values=[team.get("displayName"),team.get("shortDisplayName")]
                info[side]=sorted({x.strip() for x in values if isinstance(x,str) and x.strip()})
            if ident in names and names[ident]!=info:duplicates.add(ident)
            names[ident]=info
        except (ValueError,TypeError,KeyError,AttributeError):continue
    for r in rows:
        info=names.get(r["eventId"])
        if info and r["eventId"] not in duplicates and all(r[s] in info[s] for s in ("home","away")):
            r["sourceTeamNames"]=info
    return rows,bad

def public_fixtures(day,reader=read):
    def group(entry):
        label,code,sport=entry[:3]
        source_code=SOURCES[code][1] if code in SOURCES else code
        url=f"https://site.api.espn.com/apis/site/v2/sports/soccer/{source_code}/scoreboard?dates={day.replace('-','')}"
        result=dict(league=code,leagueName=label,rows=[],error=None)
        try:
            result["rows"],result["invalid"]=attach_names(json.loads(reader(url)),day)
        except (OSError,ValueError,TypeError,KeyError,AttributeError) as exc:
            result["error"]=type(exc).__name__
        return result
    with ThreadPoolExecutor(max_workers=4) as pool:return list(pool.map(group,(*LEAGUES,*EXTRA)))
