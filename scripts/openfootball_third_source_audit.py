"""Read-only third-source adjudication of disputed historical scores."""
import hashlib, json, sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo
from openfootball_score_audit import ROOT, CODES, key, compare, csv_index

LEAGUES={"en.3":("eng.3","Europe/London"),"it.2":("ita.2","Europe/Rome")}

def read(url):
    with urlopen(Request(url,headers={"User-Agent":"OrtakAnaliz historical football research"}),timeout=30) as response:
        raw=response.read(8_000_001)
    if len(raw)>8_000_000:raise ValueError("oversized response")
    return raw

def espn_index(payload,code,tz):
    if not isinstance(payload.get("events"),list):raise ValueError("ESPN schema")
    out=defaultdict(list)
    for event in payload["events"]:
        try:
            comp,=event["competitions"]
            status=comp.get("status",event.get("status",{}))["type"]
            if status.get("completed") is not True or status.get("name")!="STATUS_FULL_TIME":continue
            stamp=datetime.fromisoformat(comp.get("date",event["date"]).replace("Z","+00:00"))
            if stamp.tzinfo is None:continue
            day=stamp.astimezone(ZoneInfo(tz)).date().isoformat()
            teams={x["homeAway"]:x for x in comp["competitors"]}
            if len(comp["competitors"])!=2 or set(teams)!={"home","away"}:continue
            h,a=teams["home"],teams["away"]
            raw=[h["score"],a["score"]]
            if not all(isinstance(x,str) and x.isascii() and x.isdigit() for x in raw):continue
            k=key(day,h["team"]["displayName"],a["team"]["displayName"],code)
            if not all(k) or k[1]==k[2]:continue
            out[k].append(dict(eventId=str(event["id"]),score=[int(x) for x in raw],home=h["team"]["displayName"],away=a["team"]["displayName"]))
        except (ValueError,KeyError,TypeError,AttributeError):continue
    return out

def adjudicate(row,candidates):
    if len(candidates)!=1:return "third_missing" if not candidates else "third_ambiguous"
    s=candidates[0]["score"]
    if s==row["openfootball"]:return "third_supports_openfootball"
    if s==row["independent"]:return "third_supports_csv"
    return "third_disagrees"

def main():
    reports=[]
    for code,division in CODES.items():
        path=ROOT/"research"/"openfootball"/"2025-26"/(code+".json")
        a=json.loads(path.read_text())
        csv_url="https://football-data.co.uk/mmz4281/2526/"+division+".csv"
        raw=read(csv_url)
        rows=compare(a["matches"],csv_index(raw),code)
        unresolved=[r for r in rows if r["status"]!="matched"]
        out=dict(league=code,sourceBlobSha=a["sourceBlobSha"],csvSource=csv_url,csvSha256=hashlib.sha256(raw).hexdigest(),initialCounts=dict(Counter(r["status"] for r in rows)),thirdSources=[],errors=[],rows=[])
        idx=defaultdict(list)
        if unresolved and code in LEAGUES:
            espn,tz=LEAGUES[code]
            for day in sorted({r["date"] for r in unresolved}):
                url=f"https://site.api.espn.com/apis/site/v2/sports/soccer/{espn}/scoreboard?dates="+day.replace("-","")
                try:
                    b=read(url);payload=json.loads(b)
                    part=espn_index(payload,code,tz)
                    for k,v in part.items():
                        if k[0]==day:idx[k].extend(v)
                    out["thirdSources"].append(dict(day=day,url=url,sha256=hashlib.sha256(b).hexdigest(),eventCount=len(payload["events"]),indexedKeys=len(part)))
                except (OSError,ValueError,TypeError,KeyError) as exc:out["errors"].append(dict(day=day,error=str(exc)))
        for row in unresolved:
            k=key(row["date"],row["home"],row["away"],code)
            candidates=idx.get(k,[])
            outcome="third_source_unavailable" if any(e["day"]==row["date"] for e in out["errors"]) else adjudicate(row,candidates) if row["status"]!="ambiguous" else "original_ambiguous"
            detail=dict(row,thirdCandidates=candidates,outcome=outcome)
            out["rows"].append(detail)
            print("REVIEW",json.dumps(dict(league=code,**detail),ensure_ascii=False))
        out["thirdCounts"]=dict(Counter(r["outcome"] for r in out["rows"]))
        reports.append(out)
        print("LEAGUE",json.dumps({k:v for k,v in out.items() if k!="rows"},ensure_ascii=False))
    original=Counter();third=Counter()
    for r in reports:original.update(r["initialCounts"]);third.update(r["thirdCounts"])
    result=dict(mode="historical_source_adjudication",originalCounts=dict(original),thirdCounts=dict(third),leagues=reports,archiveModified=False)
    Path("openfootball_third_source_audit.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    print("TOTAL",json.dumps(dict(original=original,third=third)))
    if sum(original.values())!=860:raise SystemExit("unexpected score count")
    if any(r["errors"] for r in reports):raise SystemExit("third source access incomplete")

def self_test():
    r={"openfootball":[2,1],"independent":[0,1]}
    assert adjudicate(r,[{"score":[2,1]}])=="third_supports_openfootball"
    assert adjudicate(r,[{"score":[0,1]}])=="third_supports_csv"
    assert adjudicate(r,[{"score":[0,0]}])=="third_disagrees"
    assert adjudicate(r,[])=="third_missing"
    assert adjudicate(r,[{"score":[2,1]}]*2)=="third_ambiguous"
    assert espn_index({"events":[]},"en.3","Europe/London")=={}
    print("Third source self-tests passed")

if __name__=="__main__":
    if sys.argv[1:]==["--self-test"]:self_test()
    else:main()
