"""Compare published fixtures against ESPN, without rewriting forecasts or dates."""
import json
from collections import defaultdict,Counter
from datetime import datetime,timedelta
from pathlib import Path
from scoreboard_snapshot import build,TR
from league_config import LEAGUES
from nine_league_results_pilot import result_key

CODES={name:(code,sport) for name,code,sport in LEAGUES}
SPORTS={code:sport for _,code,sport in LEAGUES}
def ident(code,h,a):
    sport=SPORTS[code]
    return (code,result_key(h,code,sport),result_key(a,code,sport))

def compare(daily,boards,now):
    days={b["date"] for b in boards}
    primary=defaultdict(list);secondary=defaultdict(list);coverage={}
    for b in boards:
        for g in b["groups"]:
            code=g["league"]
            coverage[(code,b["date"])]=g["error"] is None and g["invalid"]==0
            if not coverage[(code,b["date"])]:continue
            for row in g["rows"]:
                if row["state"]!="pre" or row["status"]!="STATUS_SCHEDULED":continue
                k=ident(code,row["home"],row["away"])
                secondary[k].append(dict(date=b["date"],eventId=row["eventId"],kickoff=row["kickoff"],match=row["home"]+" – "+row["away"]))
    for row in daily["upcoming"]:
        if row["date"] not in days or row["league"] not in CODES:continue
        code,_=CODES[row["league"]]
        h,a=row["match"].split(" – ")
        primary[ident(code,h,a)].append(row)
    out=[]
    for k in sorted(set(primary)|set(secondary)):
        p,s=primary[k],secondary[k]
        code=k[0]
        if not k[1] or not k[2] or k[1]==k[2] or len(p)>1 or len(s)>1: status="ambiguous"
        elif not all(coverage.get((code,d),False) for d in days):status="source_incomplete"
        elif p and s: status="same_date" if p[0]["date"]==s[0]["date"] else "date_difference"
        elif p:status="published_only"
        else:status="espn_only"
        out.append(dict(league=code,published=p,espn=s,status=status))
    return dict(version="4.92",updatedAt=now.isoformat(),dailyUpdatedAt=daily["updatedAt"],mode="research_only",dates=sorted(days),source="ESPN",sourceGroups=len(coverage),healthyGroups=sum(coverage.values()),counts=dict(Counter(x["status"] for x in out)),rows=out,decision="PAS",archivesModified=False)
def main():
    now=datetime.now(TR)
    daily=json.loads(Path("daily.json").read_text(encoding="utf-8"))
    boards=[build(now,query_date=(now.date()+timedelta(days=i)).isoformat()) for i in (1,2,3)]
    report=compare(daily,boards,now)
    Path("fixture_coverage_audit.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k!="rows"},ensure_ascii=False))
if __name__=="__main__":main()
