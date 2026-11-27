"""Audit paired match metrics in newly observed competitions; research only."""
import json
from datetime import datetime,timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from scoreboard_snapshot import parse
from live_statistics_pilot import BASE,parse_summary
from results_source_pilot import read,TR
from live_analysis_quality import REQUIRED,pair
CODES=("eng.3","ger.2","esp.2","ita.2","fra.2","bel.1","aut.1","den.1","nor.1","jpn.1","aus.1","ind.1","rsa.1","uefa.europa")
def probe(code,now,reader=read):
    fixtures={};errors=[]
    for i in range(8):
        day=(now.astimezone(TR).date()-timedelta(days=i)).isoformat()
        try:
            rows,invalid=parse(json.loads(reader(BASE+code+"/scoreboard?dates="+day.replace("-",""))),day)
            if invalid:raise ValueError("invalid scoreboard")
            for r in rows:
                if r["state"]=="post" and r["status"]=="STATUS_FULL_TIME":fixtures[r["eventId"]]=r
        except (OSError,ValueError,TypeError,KeyError,AttributeError) as exc:errors.append(type(exc).__name__)
    sample=sorted(fixtures.values(),key=lambda r:r["kickoff"],reverse=True)[:5]
    counts={k:0 for k in REQUIRED};complete=0;responding=0
    for r in sample:
        try:
            obs=parse_summary(json.loads(reader(BASE+code+"/summary?event="+r["eventId"])),r)
            if obs["state"]!="post" or obs["score"]!=r["score"]:raise ValueError("score mismatch")
            responding+=1
            m=obs["metrics"]
            valid={k for k in REQUIRED if pair(m.get(k),k=="possession")}
            if "possession" in valid and abs(sum(m["possession"])-100)>2:valid.remove("possession")
            if {"shots","shotsOnTarget"}<=valid and any(a>b for a,b in zip(m["shotsOnTarget"],m["shots"])):valid.remove("shotsOnTarget")
            for k in valid:counts[k]+=1
            complete+=len(valid)==len(REQUIRED)
        except (OSError,ValueError,TypeError,KeyError,AttributeError) as exc:errors.append(type(exc).__name__)
    return dict(league=code,sampled=len(sample),responding=responding,complete=complete,metrics=counts,errors=errors)
if __name__=="__main__":
    now=datetime.now(TR)
    with ThreadPoolExecutor(max_workers=6) as pool:rows=list(pool.map(lambda c:probe(c,now),CODES))
    Path("global_metric_coverage.json").write_text(json.dumps(dict(version="5.60",mode="research_only",predictionsEnabled=False,rows=rows),indent=2))
    print(json.dumps(rows))
    assert any(r["responding"] for r in rows)
