"""V4.79 read-only score provenance audit; never change archived outcomes."""
import json
from collections import Counter,defaultdict
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from multi_league_results import verified_rows,TR
from league_config import FIXTURE_CODES

def valid_score(x):
    return isinstance(x,list) and len(x)==2 and all(type(v) is int and v>=0 for v in x)

def audit(archives,report,now):
    verified=defaultdict(set)
    for r in verified_rows(report,now):
        verified[(r["league"],r["date"],r["home"],r["away"])].add(tuple(r["result"]))
    rows=[]
    group=defaultdict(list)
    counts={}
    for kind,archive in archives.items():
        local=[]
        for r in archive.values():
            if r["result"] is None: continue
            if kind=="performance":
                h,a=r["match"].split(" – ");league=FIXTURE_CODES[r["league"]]
            else: h,a,league=r["home"],r["away"],r["league"]
            ident=(league,r["date"],h,a)
            score=r["result"]
            sources=r.get("resultSources",[])
            domains={urlparse(s).hostname for s in sources if isinstance(s,str) and s.startswith("https://") and urlparse(s).hostname} if isinstance(sources,list) else set()
            comparison=verified.get(ident,set())
            status="invalid_score" if not valid_score(score) else "source_conflict" if comparison and comparison!={tuple(score)} else "currently_corroborated" if comparison else "multiple_recorded_domains" if len(domains)>=2 else "single_recorded_domain" if domains else "provenance_missing"
            row=dict(archive=kind,league=league,date=r["date"],home=h,away=a,result=score,status=status,recordedSourceDomains=sorted(domains))
            local.append(row);group[ident].append(row)
        rows.extend(local)
        counts[kind]=dict(Counter(x["status"] for x in local))
    cross=[]
    for ident,items in sorted(group.items()):
        if len({tuple(x["result"]) for x in items if valid_score(x["result"])})>1:
            cross.append(dict(league=ident[0],date=ident[1],home=ident[2],away=ident[3],results=[dict(archive=x["archive"],result=x["result"]) for x in items]))
    return dict(version="4.79",updatedAt=now.isoformat(),mode="research_only",uniqueSettledMatches=len(group),settledArchiveRecords=len(rows),counts=counts,crossArchiveConflicts=cross,rows=rows,decision="PAS")

def main():
    def load(name): return json.loads(Path(name+".json").read_text(encoding="utf-8"))
    result=audit({"prospective":load("prospective_archive"),"performance":load("prediction_archive")},load("multi_league_results"),datetime.now(TR))
    Path("score_provenance.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:result[k] for k in ("uniqueSettledMatches","settledArchiveRecords","counts","crossArchiveConflicts")},ensure_ascii=False))
if __name__=="__main__": main()
