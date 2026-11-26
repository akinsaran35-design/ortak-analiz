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
    # Use the same single-day endpoint shape as the existing nine-league integration.
    def group(entry):
        name,code=entry
        g=dict(league=code,leagueName=name,sources=[],rows=[],error=None,errors=[],invalid=0,truncated=False,respondedDays=0)
        for day in days:
            url=BASE+code+"/scoreboard?dates="+day.replace("-","")
            g["sources"].append(url)
            try:
                payload=json.loads(reader(url))
                if not isinstance(payload.get("events"),list):raise ValueError("schema")
                rows,bad=parse(payload,day)
                g["respondedDays"]+=1
                g["invalid"]+=bad
                g["rows"].extend(dict(row,date=day) for row in rows)
            except (OSError,ValueError,TypeError,KeyError,AttributeError) as exc:
                g["errors"].append(dict(date=day,type=type(exc).__name__,httpStatus=getattr(exc,"code",None)))
        seen=set();dupes=set()
        for row in g["rows"]:
            if row["eventId"] in seen:dupes.add(row["eventId"])
            seen.add(row["eventId"])
        g["rows"]=[r for r in g["rows"] if r["eventId"] not in dupes]
        g["invalid"]+=len(dupes)
        g["error"]="incomplete_source" if g["errors"] else None
        return g
    with ThreadPoolExecutor(max_workers=4) as pool:
        groups=list(pool.map(group,COMPETITIONS))
    return dict(version="5.08",updatedAt=now.isoformat(),mode="fixture_discovery_only",
        source="ESPN",dates=days,groups=groups,configuredCompetitions=len(COMPETITIONS),
        respondingCompetitions=sum(g["error"] is None for g in groups),
        eventCount=sum(len(g["rows"]) for g in groups),coverageComplete=False,
        predictionsEnabled=False,realBettingEnabled=False,decision="PAS")
def audit_report(r):
    try:
        stamp=datetime.fromisoformat(r["updatedAt"])
        if stamp.tzinfo is None:return False
        days=[(stamp.astimezone(TR).date()+timedelta(days=i)).isoformat() for i in range(4)]
        if r["dates"]!=days or r["version"]!="5.08" or r["source"]!="ESPN" or r["mode"]!="fixture_discovery_only" or r["coverageComplete"] is not False or r["predictionsEnabled"] is not False or r["realBettingEnabled"] is not False or r["decision"]!="PAS":return False
        groups=r["groups"]
        if len(groups)!=len(COMPETITIONS) or {(g["leagueName"],g["league"]) for g in groups}!=set(COMPETITIONS):return False
        for g in groups:
            if g["sources"]!=[BASE+g["league"]+"/scoreboard?dates="+d.replace("-","") for d in days]:return False
            if not 0<=g["respondedDays"]<=4 or len(g["errors"])!=4-g["respondedDays"]:return False
            if (g["error"] is None)!=(g["respondedDays"]==4):return False
            ids=set()
            for row in g["rows"]:
                t=datetime.fromisoformat(row["kickoff"])
                if t.tzinfo is None or row["date"] not in days or t.astimezone(TR).date().isoformat()!=row["date"] or row["eventId"] in ids:return False
                ids.add(row["eventId"])
        return r["configuredCompetitions"]==len(groups) and r["respondingCompetitions"]==sum(g["error"] is None for g in groups) and r["eventCount"]==sum(len(g["rows"]) for g in groups)
    except (KeyError,TypeError,ValueError,AttributeError):return False
def main():
    r=build(datetime.now(TR))
    Path("football_coverage_pilot.json").write_text(json.dumps(r,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Source diagnostics:",json.dumps([{k:v for k,v in g.items() if k in ("league","respondedDays","errors","invalid")} for g in r["groups"]],ensure_ascii=False))
    print("Football discovery:",r["respondingCompetitions"],"/",r["configuredCompetitions"],"responding;",r["eventCount"],"events")
    if not r["respondingCompetitions"] and "--allow-empty" not in __import__("sys").argv:raise SystemExit("No source response")
if __name__=="__main__":main()
