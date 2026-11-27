"""V4.69: dual-source settlement input for nine smoke-tested leagues."""
import json
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from results_source_pilot import csv_results, espn_results, read, TR
from nine_league_results_pilot import SOURCES, result_key
from league_config import LEAGUES,FIXTURE_CODES

APPROVED=frozenset(("en.1","en.2","de.1","es.1","it.1","fr.1","nl.1","pt.1","tr.1"))
SPORTS={code:sport for _,code,sport in LEAGUES}
RETRY_DAYS=30

def within_window(day,now):
    return now.date()-timedelta(days=RETRY_DAYS)<=date.fromisoformat(day)<now.date()

def combined_records(prospective,performance):
    # Preserve exact archive names and avoid counting the same fixture twice.
    rows=dict(prospective)
    by_id=defaultdict(list)
    for r in prospective.values():
        by_id[(r['league'],r['date'],r['home'],r['away'])].append(r)
    for key,r in performance.items():
        try:
            code=FIXTURE_CODES[r['league']];h,a=r['match'].split(' – ')
            ident=(code,r['date'],h,a)
            converted=dict(r,league=code,home=h,away=a)
            if ident in by_id:
                existing=by_id[ident]
                # Conflicting archived scores must never become an eligible row.
                if any(x['result'] is not None and r['result'] is not None and x['result']!=r['result'] for x in existing):
                    rows['performance:'+key]=converted
                elif len(existing)==1 and existing[0]['result'] is None and r['result'] is not None:
                    for k,x in rows.items():
                        if x is existing[0]:rows[k]=dict(x,result=r['result']);break
                continue
            rows['performance:'+key]=converted
            by_id[ident].append(converted)
        except (ValueError,KeyError,TypeError,AttributeError):continue
    return rows

def source_urls(code,day):
    d=date.fromisoformat(day)
    y=d.year if d.month>=7 else d.year-1
    csv_code,espn_code=SOURCES[code]
    return (f"https://football-data.co.uk/mmz4281/{y%100:02d}{(y+1)%100:02d}/{csv_code}.csv",
            f"https://site.api.espn.com/apis/site/v2/sports/soccer/{espn_code}/scoreboard?dates={day.replace('-','')}")

def build_report(archive,now,reader=read):
    groups=defaultdict(list)
    for r in archive.values():
        d=date.fromisoformat(r["date"])
        if r["league"] in APPROVED and within_window(r["date"],now):
            groups[(r["league"],r["date"])].append(r)
    reports=[]
    cache={}
    for (code,day),records in sorted(groups.items()):
        urls=source_urls(code,day)
        identify=lambda d,h,a:(d,result_key(h,code,SPORTS[code]),result_key(a,code,SPORTS[code]))
        out={"league":code,"date":day,"sources":list(urls),"errors":[],"rows":[]}
        try:
            if urls[0] not in cache:
                cache[urls[0]]=csv_results(reader(urls[0]),identify)
            primary=cache[urls[0]]
            secondary=espn_results(json.loads(reader(urls[1])),day,identify)
            ids=Counter(identify(day,r["home"],r["away"]) for r in records)
            for r in records:
                k=identify(day,r["home"],r["away"])
                a,b=primary.get(k),secondary.get(k)
                status="corroborated" if a is not None and a==b else "conflict" if a is not None and b is not None else "incomplete"
                if not k[1] or not k[2] or k[1]==k[2] or ids[k]!=1: status="ambiguous"
                if status=="corroborated" and r["result"] is not None and r["result"]!=a: status="archive_conflict"
                out["rows"].append(dict(date=day,home=r["home"],away=r["away"],csv=a,espn=b,status=status))
        except (OSError,ValueError,KeyError,TypeError,AttributeError) as exc:
            out["errors"].append(type(exc).__name__)
        reports.append(out)
    return {"version":"4.69","updatedAt":now.isoformat(),"mode":"research_only","approvedLeagues":sorted(APPROVED),"excludedLeagues":[],"groups":reports}

def verified_rows(report,now):
    try:
        stamp=datetime.fromisoformat(report["updatedAt"])
        if report["version"]!="4.69" or not timedelta(0)<=now-stamp<=timedelta(minutes=30): return []
        out=[]
        for group in report["groups"]:
            code,day=group["league"],group["date"]
            if code not in APPROVED or group["errors"] or not within_window(day,now): continue
            urls=source_urls(code,day)
            if group["sources"]!=list(urls): continue
            for r in group["rows"]:
                result=r["csv"]
                if r["date"]!=day or r["status"]!="corroborated" or result!=r["espn"]: continue
                if not isinstance(result,list) or len(result)!=2 or not all(type(x) is int and x>=0 for x in result): continue
                out.append(dict(date=day,league=code,home=r["home"],away=r["away"],result=result,sources=list(urls)))
        return out
    except (ValueError,TypeError,KeyError,AttributeError): return []

def main():
    now=datetime.now(TR)
    archive=json.loads(Path("prospective_archive.json").read_text())
    legacy=json.loads(Path("prediction_archive.json").read_text())
    report=build_report(combined_records(archive,legacy),now)
    report["retryDays"]=RETRY_DAYS
    report["automaticVerifiedCount"]=len(verified_rows(report,datetime.now(TR)))
    Path("multi_league_results.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    print("V4.69 result audit:",json.dumps({"verified":report["automaticVerifiedCount"],"groups":[{"league":g["league"],"date":g["date"],"counts":dict(Counter(r["status"] for r in g["rows"])),"errors":g["errors"]} for g in report["groups"]]},ensure_ascii=False))

if __name__=="__main__": main()
