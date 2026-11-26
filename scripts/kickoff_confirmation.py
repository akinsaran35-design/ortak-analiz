"""Read-only agreement between ESPN fixture times and international odds event times."""
import json
from collections import defaultdict,Counter
from datetime import datetime,timedelta
from pathlib import Path
from league_config import LEAGUES
from fixture_coverage_audit import ident,TR

SPORTS={sport:code for _,code,sport in LEAGUES}
def stamp(s):
    d=datetime.fromisoformat(s.replace("Z","+00:00"))
    if d.tzinfo is None: raise ValueError("naive time")
    return d
def fresh(r,now):
    try:return timedelta(0)<=now-stamp(r["updatedAt"])<=timedelta(minutes=30)
    except (KeyError,ValueError,TypeError,AttributeError):return False

def build(daily,coverage,odds,now):
    available=(fresh(daily,now) and fresh(coverage,now) and fresh(odds,now)
        and coverage.get("version")=="4.92" and coverage.get("dailyUpdatedAt")==daily.get("updatedAt")
        and coverage.get("archivesModified") is False and coverage.get("mode")=="research_only"
        and odds.get("source")=="The Odds API" and odds.get("region")=="uk" and odds.get("errors")==[])
    rows=[];events=defaultdict(list)
    if available:
        for e in odds["events"]:
            try:
                code=SPORTS[e["league"]]
                if e["league"] not in odds["queriedLeagues"]:continue
                if stamp(e["kickoff"])<=now:continue
                events[ident(code,e["home"],e["away"])].append(e)
            except (KeyError,ValueError,TypeError,AttributeError):continue
        for row in coverage["rows"]:
            if row["status"] not in ("same_date","date_difference","espn_only") or len(row["espn"])!=1:continue
            s=row["espn"][0];code=row["league"]
            k=ident(code,*s["match"].split(" – "))
            candidates=events[k]
            status="unmatched";event=None
            if len(candidates)>1:status="ambiguous"
            elif len(candidates)==1:
                e=candidates[0]
                if stamp(s["kickoff"])>now and stamp(s["kickoff"])==stamp(e["kickoff"]) and stamp(e["kickoff"]).astimezone(TR).date().isoformat()==s["date"]:
                    status="agreed";event=e["id"]
                else:status="time_difference"
            rows.append(dict(league=code,match=s["match"],date=s["date"],kickoff=s["kickoff"],espnEventId=s["eventId"],oddsEventId=event,published=row["published"],status=status))
    return dict(version="4.94",updatedAt=now.isoformat(),dailyUpdatedAt=daily["updatedAt"],coverageUpdatedAt=coverage["updatedAt"],oddsUpdatedAt=odds["updatedAt"],mode="research_only",available=available,counts=dict(Counter(x["status"] for x in rows)),rows=rows,archivesModified=False,decision="PAS")
def main():
    def load(name):return json.loads(Path(name).read_text(encoding="utf-8"))
    r=build(load("daily.json"),load("fixture_coverage_audit.json"),load("odds.json"),datetime.now(TR))
    Path("kickoff_confirmation.json").write_text(json.dumps(r,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in r.items() if k!="rows"},ensure_ascii=False))
if __name__=="__main__":main()
