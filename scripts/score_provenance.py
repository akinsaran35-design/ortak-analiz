"""V4.79 read-only score provenance audit; never change archived outcomes."""
import json
from collections import Counter,defaultdict
from datetime import datetime,date,timedelta
from pathlib import Path
from urllib.parse import urlparse
from multi_league_results import APPROVED,source_urls,TR
from league_config import FIXTURE_CODES

def valid_score(x):
    return isinstance(x,list) and len(x)==2 and all(type(v) is int and v>=0 for v in x)

def comparisons(report,now):
    """Inspect even archive_conflict rows; settlement eligibility is not audit eligibility."""
    agreed=defaultdict(set)
    disagreements=set()
    try:
        age=now-datetime.fromisoformat(report["updatedAt"])
        if report["version"]!="4.69" or not timedelta(0)<=age<=timedelta(minutes=30):
            return agreed,disagreements
        for g in report["groups"]:
            code,day=g["league"],g["date"]
            if code not in APPROVED or g["errors"] or g["sources"]!=list(source_urls(code,day)):
                continue
            if not now.date()-timedelta(days=14)<=date.fromisoformat(day)<now.date(): continue
            for r in g["rows"]:
                if r["date"]!=day or not r["home"] or not r["away"] or r["home"]==r["away"]: continue
                if r["status"] not in ("corroborated","archive_conflict","conflict"): continue
                a,b=r["csv"],r["espn"]
                if not valid_score(a) or not valid_score(b): continue
                ident=(code,day,r["home"],r["away"])
                if a!=b: disagreements.add(ident)
                else: agreed[ident].add(tuple(a))
    except (KeyError,ValueError,TypeError,AttributeError):
        return defaultdict(set),set()
    return agreed,disagreements

def audit(archives,report,now):
    verified,disagreements=comparisons(report,now)
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
            status="invalid_score" if not valid_score(score) else "feed_disagreement" if ident in disagreements else "source_conflict" if comparison and comparison!={tuple(score)} else "currently_corroborated" if comparison else "multiple_recorded_domains" if len(domains)>=2 else "single_recorded_domain" if domains else "provenance_missing"
            row=dict(archive=kind,league=league,date=r["date"],home=h,away=a,result=score,status=status,recordedSourceDomains=sorted(domains))
            local.append(row);group[ident].append(row)
        rows.extend(local)
        counts[kind]=dict(Counter(x["status"] for x in local))
    cross=[]
    for ident,items in sorted(group.items()):
        if len({tuple(x["result"]) for x in items if valid_score(x["result"])})>1:
            cross.append(dict(league=ident[0],date=ident[1],home=ident[2],away=ident[3],results=[dict(archive=x["archive"],result=x["result"]) for x in items]))
    return dict(version="4.80",updatedAt=now.isoformat(),mode="research_only",uniqueSettledMatches=len(group),settledArchiveRecords=len(rows),counts=counts,crossArchiveConflicts=cross,feedDisagreements=len(disagreements),rows=rows,decision="PAS")

def main():
    def load(name): return json.loads(Path(name+".json").read_text(encoding="utf-8"))
    result=audit({"prospective":load("prospective_archive"),"performance":load("prediction_archive")},load("multi_league_results"),datetime.now(TR))
    Path("score_provenance.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:result[k] for k in ("uniqueSettledMatches","settledArchiveRecords","counts","crossArchiveConflicts","feedDisagreements")},ensure_ascii=False))
if __name__=="__main__": main()
