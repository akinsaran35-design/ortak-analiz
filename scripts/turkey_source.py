"""Turkey research adapter: historical FT scores + current UK-region odds fixtures.
No provider odds from the historical CSV are imported or published.
"""
import csv, io, json, re, unicodedata
from datetime import datetime, timezone, timedelta, date
from pathlib import Path
from urllib.request import urlopen
from urllib.error import URLError
from concurrent.futures import ThreadPoolExecutor
from collections import Counter

SPORT="soccer_turkey_super_league"
TR=timezone(timedelta(hours=3))
ROOT=Path(__file__).resolve().parent.parent

def team_key(name):
    name=unicodedata.normalize("NFKD",name.casefold().replace("ı","i"))
    key=" ".join(re.findall(r"[a-z0-9]+","".join(c for c in name if not unicodedata.combining(c))))
    aliases={
        "besiktas jk":"besiktas","fenerbahce sk":"fenerbahce","galatasaray sk":"galatasaray",
        "kasimpasa sk":"kasimpasa","kasimpasa as":"kasimpasa","istanbul basaksehir":"basaksehir",
        "istanbul basaksehir fk":"basaksehir","basaksehir fk":"basaksehir","buyuksehir belediye erzurumspor":"erzurumspor",
        "bb erzurumspor":"erzurumspor","erzurumspor fk":"erzurumspor","gaziantep fk":"gaziantep",
        "gaziantep bb":"gaziantep","gazisehir gaziantep":"gaziantep","gazisehir gaziantep fk":"gaziantep",
        "torku konyaspor":"konyaspor","atiker konyaspor":"konyaspor","aytemiz alanyaspor":"alanyaspor",
        "caykur rizespor":"rizespor","goztepe sk":"goztepe","corum fk":"corum",
        "amed sk":"amed","amedspor":"amed","genclerbirligi sk":"genclerbirligi",
        "eyupspor fk":"eyupspor","trabzonspor as":"trabzonspor"
    }
    return aliases.get(key,key)

def parse_results(raw,season):
    year=int(season[:4])
    reader=csv.DictReader(io.StringIO(raw.decode("utf-8-sig",errors="strict")))
    if not {"Date","HomeTeam","AwayTeam","FTHG","FTAG"}.issubset(reader.fieldnames or []):
        raise ValueError("unexpected Turkey CSV schema")
    rows={}
    blocked=set()
    for row in reader:
        try:
            d=None
            for fmt in ("%d/%m/%Y","%d/%m/%y"):
                try: d=datetime.strptime(row["Date"],fmt).date(); break
                except ValueError: pass
            if not d or not date(year,7,1)<=d<date(year+1,7,1): continue
            if not all(re.fullmatch(r"\d+",row.get(k) or "") for k in ("FTHG","FTAG")): continue
            h,a=team_key(row["HomeTeam"]),team_key(row["AwayTeam"])
            if not h or not a or h==a: continue
            key=(d.isoformat(),h,a)
            value=dict(date=key[0],team1=h,team2=a,score={"ft":[int(row["FTHG"]),int(row["FTAG"])]})
            if key in rows and rows[key]!=value: blocked.add(key)
            rows[key]=value
        except (ValueError,TypeError,AttributeError): continue
    result=[v for k,v in rows.items() if k not in blocked]
    if not result: raise ValueError("no valid Turkey results")
    return result

def fixtures(snapshot,now):
    try:
        stamp=datetime.fromisoformat(snapshot["updatedAt"].replace("Z","+00:00"))
        if not timedelta(0)<=now-stamp<=timedelta(minutes=30): return []
        if snapshot.get("source")!="The Odds API" or snapshot.get("region")!="uk": return []
        if snapshot.get("errors") or SPORT not in snapshot.get("queriedLeagues",[]): return []
    except (KeyError,ValueError,TypeError,AttributeError): return []
    rows={}
    for event in snapshot.get("events",[]):
        try:
            if event["league"]!=SPORT: continue
            t=datetime.fromisoformat(event["kickoff"].replace("Z","+00:00"))
            if t<=now: continue
            h,a=team_key(event["home"]),team_key(event["away"])
            if not h or not a or h==a: continue
            d=t.astimezone(TR).date().isoformat()
            rows[(d,h,a)]=dict(date=d,team1=h,team2=a)
        except (KeyError,ValueError,TypeError,AttributeError): continue
    return list(rows.values())

def espn_fixtures(payload,day,now):
    """Scheduled future Turkey fixtures only; never substitute odds or scores."""
    if not isinstance(payload,dict) or not isinstance(payload.get("events"),list):
        raise ValueError("invalid ESPN fixtures")
    rows=[]
    for e in payload["events"]:
        try:
            comp,=e["competitions"]
            status=comp.get("status",e.get("status",{}))["type"]
            if status.get("name")!="STATUS_SCHEDULED" or status.get("completed") is not False:continue
            kickoff=datetime.fromisoformat((comp.get("date") or e["date"]).replace("Z","+00:00"))
            if kickoff.tzinfo is None or kickoff<=now or kickoff.astimezone(TR).date()!=day:continue
            competitors=comp["competitors"]
            teams={c["homeAway"]:c["team"]["displayName"] for c in competitors}
            if len(competitors)!=2 or set(teams)!={"home","away"}:continue
            h,a=team_key(teams["home"]),team_key(teams["away"])
            eid=str(e["id"])
            if not h or not a or h==a or not eid.isascii() or not eid.isdigit():continue
            rows.append((eid,dict(date=day.isoformat(),team1=h,team2=a,fixtureSource="ESPN",fixtureKickoff=kickoff.isoformat())))
        except (KeyError,ValueError,TypeError,AttributeError,OverflowError):continue
    return rows

def read_espn(day):
    url=f"https://site.api.espn.com/apis/site/v2/sports/soccer/tur.1/scoreboard?dates={day:%Y%m%d}"
    with urlopen(url,timeout=8) as response:
        return json.loads(response.read(2_000_000))

def fallback_fixtures(now,reader=None):
    reader=reader or read_espn
    days=[now.astimezone(TR).date()+timedelta(days=i) for i in range(8)]
    def load(day):
        try:return espn_fixtures(reader(day),day,now)
        except (OSError,ValueError,TypeError,KeyError,AttributeError):return []
    with ThreadPoolExecutor(max_workers=4) as pool:
        rows=[r for batch in pool.map(load,days) for r in batch]
    ids=Counter(eid for eid,_ in rows)
    keys=Counter((r["date"],r["team1"],r["team2"]) for _,r in rows)
    return [r for eid,r in rows if ids[eid]==1 and keys[(r["date"],r["team1"],r["team2"])]==1]

def fetch(season, include_fixtures=True):
    if not re.fullmatch(r"\d{4}-\d{2}",season): raise ValueError("invalid season")
    y=int(season[:4])
    code=f"{y%100:02d}{(y+1)%100:02d}"
    with urlopen(f"https://football-data.co.uk/mmz4281/{code}/T1.csv",timeout=20) as response:
        rows=parse_results(response.read(2000000),season)
    now=datetime.now(timezone.utc)
    today=now.astimezone(TR).date()
    current=today.year if today.month>=7 else today.year-1
    if include_fixtures and y==current:
        try: snapshot=json.loads((ROOT/"odds.json").read_text())
        except (OSError,ValueError): snapshot={}
        known={(r["date"],r["team1"],r["team2"]) for r in rows}
        scheduled=fixtures(snapshot,now)
        if scheduled:
            scheduled=[dict(r,fixtureSource="The Odds API") for r in scheduled]
        else:
            scheduled=fallback_fixtures(now)
        rows.extend(r for r in scheduled if (r["date"],r["team1"],r["team2"]) not in known)
    return rows

if __name__=="__main__":
    today=datetime.now(TR).date()
    year=today.year if today.month>=7 else today.year-1
    for y in (year-1,year):
        season=f"{y}-{(y+1)%100:02d}"
        rows=fetch(season,include_fixtures=False)
        print("Turkey results",season,len(rows),"latest",max(r["date"] for r in rows))
        assert len(rows)>=30
        if y==year:
            assert date.fromisoformat(max(r["date"] for r in rows))>=today-timedelta(days=28)
