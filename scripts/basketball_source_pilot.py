"""NBA public scoreboard research pilot; no odds, forecasts, or settlement."""
import json
from datetime import datetime,timedelta
from pathlib import Path
from scoreboard_snapshot import parse
from results_source_pilot import read,TR

BASE="https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates="
def build(now,reader=read):
    day=now.astimezone(TR).date()
    groups=[]
    for delta in (-1,0,1):
        d=(day+timedelta(days=delta)).isoformat()
        # US scoreboard dates can differ from Turkey dates. Query adjacent dates too.
        rows={};blocked=set();errors=[];invalid=0;sources=[]
        for shift in (-1,0,1):
            query=(day+timedelta(days=delta+shift)).strftime("%Y%m%d")
            url=BASE+query
            sources.append(url)
            try:
                items,bad=parse(json.loads(reader(url)),d)
                invalid+=bad
                for row in items:
                    k=row["eventId"]
                    if k in rows and rows[k]!=row:blocked.add(k)
                    rows[k]=row
            except (OSError,ValueError,KeyError,TypeError,AttributeError) as exc:
                errors.append(type(exc).__name__)
        groups.append(dict(date=d,sources=sources,errors=errors,invalid=invalid+len(blocked),
            complete=not errors and not invalid and not blocked,
            rows=sorted((v for k,v in rows.items() if k not in blocked),key=lambda v:v["kickoff"])))
    return dict(version="5.05",sport="basketball",league="NBA",source="ESPN",
        updatedAt=now.isoformat(),mode="research_only",groups=groups,
        completeDays=sum(g["complete"] for g in groups),
        eventCount=sum(len(g["rows"]) for g in groups),realTime=False,
        modelCalibrated=False,realBettingEnabled=False,decision="PAS")
def main():
    cache={}
    def cached(url):
        if url not in cache:cache[url]=read(url)
        return cache[url]
    report=build(datetime.now(TR),cached)
    Path("basketball_source_pilot.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("NBA source pilot:",report["completeDays"],"/ 3 days complete,",report["eventCount"],"events")
    if not report["completeDays"]:raise SystemExit("No complete source day")
if __name__=="__main__":main()
