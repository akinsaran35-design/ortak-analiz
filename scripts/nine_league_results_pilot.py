"""V4.65 read-only nine-league score feed smoke test; no archive updates."""
import json
from collections import Counter
from datetime import datetime,date,timedelta
from pathlib import Path
from results_source_pilot import csv_results,espn_results,read,TR,key
from match_odds import canonical
from league_config import LEAGUES

SOURCES={"en.1":("E0","eng.1"),"en.2":("E1","eng.2"),"de.1":("D1","ger.1"),"es.1":("SP1","esp.1"),"it.1":("I1","ita.1"),"fr.1":("F1","fra.1"),"nl.1":("N1","ned.1"),"pt.1":("P1","por.1"),"tr.1":("T1","tur.1")}

# Explicit aliases observed in V4.65 artifact 15127106869, scoped to score feeds.
RESULT_ALIASES={
    "en.1":{"hull":"hull city","brighton":"brighton and hove albion","man united":"manchester united"},
    "de.1":{"hamburg":"hamburg sv","leverkusen":"bayer leverkusen","paderborn":"paderborn 07","m gladbach":"borussia monchengladbach","dortmund":"borussia dortmund","ein frankfurt":"eintracht frankfurt","hoffenheim":"tsg hoffenheim","elversberg":"sv elversberg","stuttgart":"vfb stuttgart"},
    "es.1":{"ath madrid":"atletico madrid","santander":"racing santander","sociedad":"real sociedad"},
    "it.1":{"milan":"ac milan","inter":"inter milan","internazionale":"inter milan"},
    "fr.1":{"stade rennais":"rennes","as monaco":"monaco","paris sg":"paris saint germain"},
    "nl.1":{"ajax amsterdam":"ajax","den haag":"ado den haag","for sittard":"fortuna sittard","nijmegen":"nec nijmegen"},
    "tr.1":{"buyuksehyr":"basaksehir","erzurum bb":"erzurumspor","goztep":"goztepe"},
}

def result_key(name,code,sport):
    n=key(name) if code=="en.2" else canonical(name,sport)
    return RESULT_ALIASES.get(code,{}).get(n,n)

def compare_day(primary,secondary,day):
    keys={k for k in primary if k[0]==day}|{k for k in secondary if k[0]==day}
    rows=[]
    for k in sorted(keys):
        a,b=primary.get(k),secondary.get(k)
        status="corroborated" if a is not None and a==b else "conflict" if a is not None and b is not None else "csv_only" if a is not None else "espn_only"
        rows.append({"date":day,"home":k[1],"away":k[2],"csv":a,"espn":b,"status":status})
    return rows

def probe(code,sport,now,reader=read):
    csv_code,espn_code=SOURCES[code]
    identity=lambda d,h,a:(d,result_key(h,code,sport),result_key(a,code,sport))
    y=now.year if now.month>=7 else now.year-1
    url=f"https://football-data.co.uk/mmz4281/{y%100:02d}{(y+1)%100:02d}/{csv_code}.csv"
    report={"league":code,"sources":[url],"errors":[],"rows":[]}
    try: primary=csv_results(reader(url),identity)
    except (OSError,ValueError,TypeError,KeyError) as exc:
        report["errors"].append("CSV: "+type(exc).__name__);return report
    days=sorted({k[0] for k in primary if now.date()-timedelta(days=28)<=date.fromisoformat(k[0])<now.date()},reverse=True)[:2]
    report["sampleDates"]=days
    if not days: report["errors"].append("No recent completed CSV scores")
    for day in days:
        url=f"https://site.api.espn.com/apis/site/v2/sports/soccer/{espn_code}/scoreboard?dates="+day.replace("-","")
        report["sources"].append(url)
        try: secondary=espn_results(json.loads(reader(url)),day,identity)
        except (OSError,ValueError,TypeError,KeyError) as exc:
            report["errors"].append(day+": "+type(exc).__name__);continue
        report["rows"].extend(compare_day(primary,secondary,day))
    return report

def main():
    now=datetime.now(TR)
    leagues=[]
    for label,code,sport in LEAGUES:
        report=probe(code,sport,now)
        report["label"]=label
        report["counts"]=dict(Counter(r["status"] for r in report["rows"]))
        leagues.append(report)
        print(json.dumps({"league":code,"counts":report["counts"],"errors":report["errors"],"sampleDates":report.get("sampleDates",[])},ensure_ascii=False))
    report={"version":"4.66","updatedAt":now.isoformat(),"mode":"research_only","leagues":leagues,"decision":"PAS","realBettingEnabled":False}
    Path("nine_league_results_pilot.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
if __name__=="__main__": main()
