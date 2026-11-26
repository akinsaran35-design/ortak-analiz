"""Research-only calendar reconciliation; no archive or decision mutation."""
import csv
import io
import json
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.request import urlopen
from zoneinfo import ZoneInfo
from match_odds import canonical, LEAGUES, build_report

BASE="https://raw.githubusercontent.com/oladeeayo/open-matchday/master/"
FOLDERS={"soccer_epl":"ENG_1_premier-league","soccer_spain_la_liga":"ESP_1_la-liga","soccer_italy_serie_a":"ITA_1_serie-a"}
ALIASES={
    "soccer_epl":{"nott m forest":"nottingham forest","leeds":"leeds united","coventry":"coventry city","man utd":"manchester united","ipswich":"ipswich town","brighton":"brighton and hove albion","newcastle":"newcastle united","spurs":"tottenham hotspur","man city":"manchester city","hull":"hull city"},
    "soccer_spain_la_liga":{"r racing club":"real racing club de santander","atletico de madrid":"atletico madrid","rc deportivo":"deportivo la coruna","celta":"celta vigo","deportivo alaves":"alaves"},
    "soccer_italy_serie_a":{"internazionale":"inter milan","roma":"as roma","atalanta":"atalanta bc","milan":"ac milan"}
}
TR=ZoneInfo("Europe/Istanbul")

def key(name,league):
    n=canonical(name,league)
    return ALIASES.get(league,{}).get(n,n)

def parse_csv(raw):
    rows=csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    if not {"date","home","away"}.issubset(rows.fieldnames or []):
        raise ValueError("fixture schema")
    return [dict(date=date.fromisoformat(r["date"]).isoformat(),home=r["home"],away=r["away"]) for r in rows if r["home"] and r["away"]]

def read(path):
    with urlopen(BASE+path,timeout=15) as f:
        return f.read(4000000)

def load_calendar(now):
    meta=json.loads(read("build_summary.json"))
    stamp=datetime.fromisoformat(meta["generated_utc"].replace("Z","+00:00"))
    if not timedelta(0)<=now-stamp<=timedelta(hours=36):
        raise ValueError("calendar snapshot stale")
    season=meta["season"]
    if not isinstance(season,str) or len(season)!=4 or not season.isdigit():
        raise ValueError("season")
    out={}
    for league,folder in FOLDERS.items():
        out[league]=parse_csv(read("data/"+folder+"/fixtures_"+season+".csv"))
    return out,stamp.isoformat()

def reconcile(daily,odds,calendar,now,source_stamp):
    stamp=datetime.fromisoformat(odds["updatedAt"].replace("Z","+00:00"))
    fresh=(timedelta(0)<=now-stamp<=timedelta(minutes=30) and odds.get("source")=="The Odds API" and odds.get("region")=="uk" and not odds.get("errors"))
    source_time=datetime.fromisoformat(source_stamp.replace("Z","+00:00"))
    fresh=fresh and timedelta(0)<=now-source_time<=timedelta(hours=36)
    original=build_report(daily,odds,now)
    corrected=[]
    proposals=[]
    for candidate in daily.get("candidates",[]):
        row=dict(candidate)
        league=LEAGUES.get(row.get("league"))
        names=row.get("match","").split(" – ")
        if fresh and league in calendar and league in odds.get("queriedLeagues",[]) and len(names)==2:
            h,a=map(lambda n:key(n,league),names)
            day=date.fromisoformat(row["date"])
            events=[]
            for ev in odds.get("events",[]):
                if ev.get("league")!=league or (key(ev["home"],league),key(ev["away"],league))!=(h,a):
                    continue
                kickoff=datetime.fromisoformat(ev["kickoff"].replace("Z","+00:00"))
                new=kickoff.astimezone(TR).date()
                if kickoff>now and abs((new-day).days)<=2:
                    events.append((ev,new))
            dates=[date.fromisoformat(x["date"]) for x in calendar[league] if (key(x["home"],league),key(x["away"],league))==(h,a) and abs((date.fromisoformat(x["date"])-day).days)<=2]
            if len(events)==1 and len(dates)==1 and dates[0]==events[0][1] and dates[0]!=day:
                row["date"]=dates[0].isoformat()
                proposals.append({"league":row["league"],"match":row["match"],"originalDate":day.isoformat(),"corroboratedDate":row["date"],"eventId":events[0][0]["id"]})
        corrected.append(row)
    identities=Counter((r["league"],r["date"],r["match"]) for r in corrected)
    if any(n>1 for n in identities.values()):
        corrected=daily["candidates"]
        proposals=[]
    replay=build_report(dict(daily,candidates=corrected),odds,now)
    return {"version":"4.59","updatedAt":now.isoformat(),"source":"https://github.com/oladeeayo/open-matchday","sourceUpdatedAt":source_stamp,"oddsUpdatedAt":odds["updatedAt"],"dailyUpdatedAt":daily.get("updatedAt"),"oddsFresh":fresh,"status":"research_only","decision":"PAS","realBettingEnabled":False,"originalMatched":original["matchedCount"],"reconciledMatched":replay["matchedCount"],"proposedCorrections":proposals,"unresolved":replay["unmatched"],"candidateCountsByDate":dict(Counter(r["date"] for r in corrected))}

def main():
    now=datetime.now(timezone.utc)
    daily=json.loads(Path("daily.json").read_text())
    odds=json.loads(Path("odds.json").read_text())
    try:
        calendar,stamp=load_calendar(now)
        report=reconcile(daily,odds,calendar,now,stamp)
    except (OSError,ValueError,KeyError,TypeError) as exc:
        report={"version":"4.59","updatedAt":now.isoformat(),"status":"unavailable","decision":"PAS","realBettingEnabled":False,"error":type(exc).__name__,"proposedCorrections":[]}
    Path("fixture_reconciliation.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps(report,ensure_ascii=False))

if __name__=="__main__":
    main()
