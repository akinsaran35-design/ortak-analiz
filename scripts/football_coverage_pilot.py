"""Public fixture discovery beyond the nine model leagues. No forecasts or odds."""
import json
from datetime import datetime,timedelta
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from scoreboard_snapshot import parse
from results_source_pilot import read,TR

COMPETITIONS=(
("UEFA Şampiyonlar Ligi","uefa.champions"),
("UEFA Avrupa Ligi","uefa.europa"),
("UEFA Konferans Ligi","uefa.europa.conf"),
("İskoçya Premiership","sco.1"),
("Belçika Pro League","bel.1"),
("Avusturya Bundesliga","aut.1"),
("İsviçre Süper Lig","sui.1"),
("Danimarka Superliga","den.1"),
("Norveç Eliteserien","nor.1"),
("İsveç Allsvenskan","swe.1"),
("Brezilya Serie A","bra.1"),
("Arjantin Primera División","arg.1"),
("ABD MLS","usa.1"),
("Meksika Liga MX","mex.1"),
("Suudi Arabistan Pro League","ksa.1"),
("Japonya J1 League","jpn.1"),
("Güney Kore K League 1","kor.1"),
("Avustralya A-League","aus.1"),
)
BASE="https://site.api.espn.com/apis/site/v2/sports/soccer/"
def build(now,reader=read):
    start=now.astimezone(TR).date()
    days=[(start+timedelta(days=i)).isoformat() for i in range(4)]
    # Query a range, including adjacent source dates around the Turkey window.
    window=(start-timedelta(days=1)).strftime("%Y%m%d")+"-"+(start+timedelta(days=4)).strftime("%Y%m%d")
    def group(entry):
        name,code=entry
        url=BASE+code+"/scoreboard?dates="+window+"&limit=200"
        g=dict(league=code,leagueName=name,source=url,rows=[],error=None,invalid=0,truncated=False)
        try:
            payload=json.loads(reader(url))
            if not isinstance(payload.get("events"),list):raise ValueError("schema")
            # Never imply complete coverage if response may have hit the limit.
            g["truncated"]=len(payload["events"])>=200
            for day in days:
                rows,bad=parse(payload,day)
                g["invalid"]+=bad
                for row in rows:
                    g["rows"].append(dict(row,date=day))
            seen=set();dupes=set()
            for row in g["rows"]:
                if row["eventId"] in seen:dupes.add(row["eventId"])
                seen.add(row["eventId"])
            g["rows"]=[r for r in g["rows"] if r["eventId"] not in dupes]
            g["invalid"]+=len(dupes)
        except (OSError,ValueError,TypeError,KeyError,AttributeError) as exc:
            g["error"]=type(exc).__name__;g["rows"]=[]
        return g
    with ThreadPoolExecutor(max_workers=4) as pool:
        groups=list(pool.map(group,COMPETITIONS))
    return dict(version="5.08",updatedAt=now.isoformat(),mode="fixture_discovery_only",
        source="ESPN",dates=days,groups=groups,configuredCompetitions=len(COMPETITIONS),
        respondingCompetitions=sum(g["error"] is None for g in groups),
        eventCount=sum(len(g["rows"]) for g in groups),coverageComplete=False,
        predictionsEnabled=False,realBettingEnabled=False,decision="PAS")
def main():
    r=build(datetime.now(TR))
    Path("football_coverage_pilot.json").write_text(json.dumps(r,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Football discovery:",r["respondingCompetitions"],"/",r["configuredCompetitions"],"responding;",r["eventCount"],"events")
    if not r["respondingCompetitions"]:raise SystemExit("No source response")
if __name__=="__main__":main()
