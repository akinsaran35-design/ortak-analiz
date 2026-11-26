"""Read-only Championship result-source pilot. Never settle archives or make selections."""
import csv, io, json
from datetime import datetime, date, timedelta, timezone
from pathlib import Path
from urllib.request import urlopen, Request
from match_odds import normalize

TR=timezone(timedelta(hours=3))
ALIASES={"bolton":"bolton wanderers","west brom":"west bromwich albion","west bromwich":"west bromwich albion","birmingham":"birmingham city","stoke":"stoke city","blackburn":"blackburn rovers","qpr":"queens park rangers","preston":"preston north end","sheffield utd":"sheffield united","sheff utd":"sheffield united","wolves":"wolverhampton wanderers","swansea":"swansea city","norwich":"norwich city","bristol city":"bristol city","charlton":"charlton athletic","lincoln":"lincoln city","cardiff":"cardiff city","derby":"derby county","west ham":"west ham united"}
def key(name):
    n=normalize(name)
    return ALIASES.get(n,n)
def identity(day,h,a):
    return (day,key(h),key(a))
def score(h,a):
    if not all(isinstance(x,str) and x.isascii() and x.isdigit() for x in (h,a)):
        raise ValueError("invalid score")
    return [int(h),int(a)]
def add(out,blocked,k,s):
    if k in out and out[k]!=s: blocked.add(k)
    out[k]=s
def csv_results(raw):
    reader=csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    if not {"Date","HomeTeam","AwayTeam","FTHG","FTAG"}.issubset(reader.fieldnames or []): raise ValueError("CSV schema")
    out={};blocked=set()
    for row in reader:
        try:
            d=None
            for fmt in ("%d/%m/%Y","%d/%m/%y"):
                try: d=datetime.strptime(row["Date"],fmt).date().isoformat(); break
                except ValueError: pass
            if d is None or not row["HomeTeam"] or not row["AwayTeam"]: continue
            add(out,blocked,identity(d,row["HomeTeam"],row["AwayTeam"]),score(row["FTHG"],row["FTAG"]))
        except (ValueError,TypeError,KeyError): continue
    return {k:v for k,v in out.items() if k not in blocked}
def espn_results(payload,day):
    out={};blocked=set()
    if not isinstance(payload.get("events"),list): raise ValueError("ESPN schema")
    for event in payload["events"]:
        try:
            comp,=event["competitions"]
            status=comp.get("status",event.get("status",{}))["type"]
            if status.get("completed") is not True or status.get("name")!="STATUS_FULL_TIME": continue
            stamp=datetime.fromisoformat(comp.get("date",event["date"]).replace("Z","+00:00"))
            if stamp.astimezone(TR).date().isoformat()!=day: continue
            teams={x["homeAway"]:x for x in comp["competitors"]}
            if len(comp["competitors"])!=2 or set(teams)!={"home","away"}: continue
            h,a=teams["home"],teams["away"]
            add(out,blocked,identity(day,h["team"]["displayName"],a["team"]["displayName"]),score(h["score"],a["score"]))
        except (ValueError,TypeError,KeyError,AttributeError): continue
    return {k:v for k,v in out.items() if k not in blocked}
def compare(records,primary,secondary):
    rows=[]
    for r in records:
        k=identity(r["date"],r["home"],r["away"])
        a,b=primary.get(k),secondary.get(k)
        status="corroborated" if a is not None and a==b else "conflict" if a is not None and b is not None else "incomplete"
        if status=="corroborated" and r["result"] is not None and r["result"]!=a: status="archive_conflict"
        rows.append({"date":r["date"],"home":r["home"],"away":r["away"],"csv":a,"espn":b,"archived":r["result"],"status":status})
    return rows
def read(url):
    with urlopen(Request(url,headers={"User-Agent":"OrtakAnaliz research source check"}),timeout=20) as f:
        return f.read(4_000_000)
def build_report(archive,now):
    records=[r for r in archive.values() if r["league"]=="en.2" and now.date()-timedelta(days=14)<=date.fromisoformat(r["date"])<now.date()]
    y=now.year if now.month>=7 else now.year-1
    url=f"https://football-data.co.uk/mmz4281/{y%100:02d}{(y+1)%100:02d}/E1.csv"
    errors=[];primary={};secondary={};sources=[url]
    try: primary=csv_results(read(url))
    except (OSError,ValueError,TypeError,KeyError) as exc: errors.append("CSV: "+type(exc).__name__)
    for day in sorted({r["date"] for r in records}):
        url="https://site.api.espn.com/apis/site/v2/sports/soccer/eng.2/scoreboard?dates="+day.replace("-","")
        sources.append(url)
        try: secondary.update(espn_results(json.loads(read(url)),day))
        except (OSError,ValueError,TypeError,KeyError) as exc: errors.append(day+": "+type(exc).__name__)
    rows=compare(records,primary,secondary)
    report={"version":"4.63","updatedAt":now.isoformat(),"mode":"research_only","decision":"PAS","records":len(rows),"corroborated":sum(r["status"]=="corroborated" for r in rows),"errors":errors,"sources":sources,"rows":rows}
    return report

def main():
    now=datetime.now(TR)
    archive=json.loads(Path("prospective_archive.json").read_text())
    report=build_report(archive,now)
    Path("results_source_pilot.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps(report,ensure_ascii=False))
if __name__=="__main__": main()
