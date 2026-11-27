"""Verify the two requested fixtures against public results feeds; no archive writes."""
import json, hashlib
from pathlib import Path
from results_source_pilot import read, csv_results, espn_results
from nine_league_results_pilot import result_key
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parent.parent
def main():
    evidence=json.loads((ROOT/"research/nov27-match-review.json").read_text())
    day=evidence["sourceDate"]
    csv_url="https://football-data.co.uk/mmz4281/2627/T1.csv"
    espn_url="https://site.api.espn.com/apis/site/v2/sports/soccer/tur.1/scoreboard?dates="+day.replace("-","")
    identity=lambda d,h,a:(d,result_key(h,"tr.1","soccer_turkey_super_league"),result_key(a,"tr.1","soccer_turkey_super_league"))
    errors=[];sources=[];a={};b={}
    for url,parser,label in [(csv_url,lambda raw:csv_results(raw,identity),"csv"),(espn_url,lambda raw:espn_results(json.loads(raw),day,identity),"espn")]:
        try:
            raw=read(url);parsed=parser(raw)
            sources.append(dict(url=url,sha256=hashlib.sha256(raw).hexdigest()))
            if label=="csv":a=parsed
            else:b=parsed
        except (OSError,ValueError,TypeError,KeyError) as exc:errors.append(dict(source=label,error=str(exc)))
    rows=[]
    for row in evidence["rows"]:
        k=identity(day,row["home"],row["away"]);x,y=a.get(k),b.get(k)
        status="corroborated" if x is not None and x==y else "conflict" if x is not None and y is not None else "incomplete"
        item=dict(row,csvScore=x,espnScore=y,result=x if status=="corroborated" else None,resultStatus=status)
        rows.append(item);print("MATCH_REVIEW",json.dumps(item,ensure_ascii=False))
    report=dict(mode="research_only",sourceCommit=evidence["sourceCommit"],updatedAt=datetime.now(timezone.utc).isoformat(),rows=rows,sources=sources,errors=errors,archivesModified=False)
    Path("nov27_match_review_result.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    print("MATCH_REVIEW_TOTAL",json.dumps(dict(corroborated=sum(r["resultStatus"]=="corroborated" for r in rows),errors=errors)))
if __name__=="__main__":main()
