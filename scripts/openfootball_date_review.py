"""Inspect date discrepancies in the 51 unresolved historical fixtures, without changing source rows."""
import json, sys, hashlib
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from openfootball_score_audit import ROOT, CODES, key, csv_index
from openfootball_third_source_audit import LEAGUES, read, espn_index

def same_pair(index, k):
    return sorted((day, scores) for (day,h,a),scores in index.items() if (h,a)==k[1:])

def inspect(row, csv, espn):
    code=row["league"]
    k=key(row["date"],row["home"],row["away"],code)
    pairs=same_pair(csv,k)
    candidates=[]
    for day,scores in pairs:
        events=espn.get((day,*k[1:]),[])
        agreed=len(scores)==1 and len(events)==1 and scores[0]==events[0]["score"]
        candidates.append(dict(date=day,deltaDays=(date.fromisoformat(day)-date.fromisoformat(row["date"])).days,csvScores=scores,espnEvents=events,twoSourceAgreement=agreed))
    if len(candidates)==1 and candidates[0]["twoSourceAgreement"]:
        status="alternative_date_corroborated" if candidates[0]["deltaDays"] else "same_date_corroborated"
    elif not candidates:status="pair_not_found"
    elif len(candidates)>1:status="multiple_date_candidates"
    else:status="independent_agreement_missing"
    return dict(row,candidates=candidates,reviewStatus=status)

def main():
    evidence=json.loads((ROOT/"research/openfootball/third-source-evidence-2026-11-27.json").read_text())
    pending=evidence["unresolved"]
    assert len(pending)==51
    allrows=[];sources=[];errors=[]
    for code in sorted({r["league"] for r in pending}):
        subset=[r for r in pending if r["league"]==code]
        csv_url="https://football-data.co.uk/mmz4281/2526/"+CODES[code]+".csv"
        raw=read(csv_url);csv=csv_index(raw)
        sources.append(dict(league=code,url=csv_url,sha256=hashlib.sha256(raw).hexdigest()))
        days=set()
        for row in subset:
            k=key(row["date"],row["home"],row["away"],code)
            days.add(k[0])
            days.update(d for d,_ in same_pair(csv,k))
        espn=defaultdict(list)
        league,tz=LEAGUES[code]
        for day in sorted(days):
            url=f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league}/scoreboard?dates="+day.replace("-","")
            try:
                b=read(url);part=espn_index(json.loads(b),code,tz)
                for k,items in part.items():
                    if k[0]==day:espn[k].extend(items)
                sources.append(dict(league=code,day=day,url=url,sha256=hashlib.sha256(b).hexdigest(),indexed=len(part)))
            except (OSError,ValueError,KeyError,TypeError) as exc:
                errors.append(dict(league=code,day=day,error=str(exc)))
        for row in subset:
            result=inspect(row,csv,espn)
            allrows.append(result)
            print("DATE_REVIEW",json.dumps(result,ensure_ascii=False))
    counts=dict(Counter(r["reviewStatus"] for r in allrows))
    report=dict(mode="date_discrepancy_review",archiveModified=False,automaticCorrections=False,counts=counts,rows=allrows,sources=sources,errors=errors)
    Path("openfootball_date_review.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    print("DATE_TOTAL",json.dumps(dict(counts=counts,errors=errors)))
    assert len(allrows)==51
    if errors:raise SystemExit("source errors remain")

def self_test():
    row=dict(league="en.3",date="2025-11-15",home="Luton Town",away="AFC Wimbledon",openfootball=[2,0])
    k=("2025-11-16","luton","afc wimbledon")
    csv={k:[[1,0]]};espn={k:[{"eventId":"1","score":[1,0]}]}
    assert inspect(row,csv,espn)["reviewStatus"]=="alternative_date_corroborated"
    assert inspect(row,csv,{})["reviewStatus"]=="independent_agreement_missing"
    assert inspect(row,{},espn)["reviewStatus"]=="pair_not_found"
    assert inspect(row,{**csv,("2025-11-17",*k[1:]):[[2,0]]},espn)["reviewStatus"]=="multiple_date_candidates"
    print("Date review self-tests passed")

if __name__=="__main__":
    if sys.argv[1:]==["--self-test"]:self_test()
    else:main()
