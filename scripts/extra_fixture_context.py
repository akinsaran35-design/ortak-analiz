"""Join upcoming extra-league fixtures to descriptive historical team records.
Exact league-scoped names only; unresolved identities remain visibly unmatched.
"""
import json
from datetime import datetime,timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
from extra_historical_metric_coverage import LEAGUES
from nine_league_results_pilot import result_key
from scoreboard_snapshot import parse
from results_source_pilot import TR,read

def build(history,now,reader=read):
    cutoff=now.astimezone(TR).date().isoformat()
    stamp=datetime.fromisoformat(history["updatedAt"])
    if (history["version"]!="7.09" or history["cutoffExclusive"]!=cutoff
        or stamp.tzinfo is None or not timedelta(0)<=now-stamp<=timedelta(hours=6)
        or history["source"]!="football-data.co.uk" or history["predictionsEnabled"] is not False):
        raise ValueError("historical snapshot not eligible")
    days=[(now.astimezone(TR).date()+timedelta(days=i)).isoformat() for i in range(4)]
    def group(entry):
        label,code,sport,_=entry
        records=[g for g in history["groups"] if g["league"]==code]
        if len(records)!=1:raise ValueError("history group mismatch")
        hist=records[0]["teamStatistics"]
        if hist["cutoffExclusive"]!=cutoff:raise ValueError("team cutoff mismatch")
        index={}
        for team in hist["teams"]:
            index.setdefault(team["team"],[]).append(team)
        rows=[];errors=[];invalid=0
        for day in days:
            url=f"https://site.api.espn.com/apis/site/v2/sports/soccer/{code}/scoreboard?dates={day.replace('-','')}"
            try:
                events,bad=parse(json.loads(reader(url)),day)
                invalid+=bad
            except (OSError,ValueError,KeyError,TypeError,AttributeError) as exc:
                errors.append(dict(date=day,type=type(exc).__name__))
                continue
            for row in events:
                if row["state"]!="pre" or row["status"]!="STATUS_SCHEDULED" or datetime.fromisoformat(row["kickoff"])<=now:continue
                keys=[result_key(row[s],code,sport) for s in ("home","away")]
                matches=[index.get(k,[]) for k in keys]
                ok=keys[0]!=keys[1] and all(len(m)==1 and m[0]["recent"]["sample"]>0 for m in matches)
                rows.append(dict(eventId=row["eventId"],kickoff=row["kickoff"],home=row["home"],away=row["away"],
                    status="matched" if ok else "unresolved_team_identity_or_history",
                    homeStatistics=matches[0][0] if ok else None,awayStatistics=matches[1][0] if ok else None))
        ids=Counter(r["eventId"] for r in rows)
        rows=[r for r in rows if ids[r["eventId"]]==1]
        return dict(league=code,leagueName=label,errors=errors,invalid=invalid+sum(n-1 for n in ids.values()),
            rows=rows,matched=sum(r["status"]=="matched" for r in rows),unmatched=sum(r["status"]!="matched" for r in rows))
    with ThreadPoolExecutor(max_workers=4) as pool:groups=list(pool.map(group,LEAGUES))
    return dict(version="7.10",updatedAt=now.isoformat(),historyUpdatedAt=history["updatedAt"],cutoffExclusive=cutoff,
        mode="descriptive_fixture_context",sources=["ESPN","football-data.co.uk"],decision="PAS",predictionsEnabled=False,
        fixtureCount=sum(len(g["rows"]) for g in groups),matchedCount=sum(g["matched"] for g in groups),
        unmatchedCount=sum(g["unmatched"] for g in groups),groups=groups)

if __name__=="__main__":
    report=build(json.loads(Path("extra_historical_metric_coverage.json").read_text()),datetime.now(TR))
    Path("extra_fixture_context.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    for g in report["groups"]:
        print(json.dumps({k:v for k,v in g.items() if k!="rows"},ensure_ascii=False))
    print(json.dumps({k:v for k,v in report.items() if k!="groups"},ensure_ascii=False))
