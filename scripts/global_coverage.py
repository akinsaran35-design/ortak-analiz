"""Read-only global scoreboard coverage probe; no prediction or settlement."""
import json
from datetime import datetime,timedelta
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from scoreboard_snapshot import parse
from results_source_pilot import read,TR

CANDIDATES=("eng.3","eng.4","ger.2","esp.2","ita.2","fra.2","bel.1","sco.1","sui.1","aut.1","den.1","nor.1","swe.1","gre.1","pol.1","usa.1","mex.1","bra.1","arg.1","col.1","chi.1","jpn.1","kor.1","aus.1","chn.1","sau.1","ind.1","rsa.1","egy.1","uefa.champions","uefa.europa","afc.champions","conmebol.libertadores")
BASE="https://site.api.espn.com/apis/site/v2/sports/soccer/"
def probe(code,day,reader=read):
    url=BASE+code+"/scoreboard?dates="+day.replace("-","")
    result=dict(league=code,date=day,source=url,events=0,invalid=0,error=None)
    try:
        payload=json.loads(reader(url))
        rows,invalid=parse(payload,day)
        result.update(events=len(rows),invalid=invalid)
    except (OSError,ValueError,TypeError,KeyError,AttributeError) as exc:
        result["error"]=type(exc).__name__
    return result
def build(now,reader=read):
    days=[(now.astimezone(TR).date()-timedelta(days=i)).isoformat() for i in (0,1,7)]
    with ThreadPoolExecutor(max_workers=8) as pool:
        rows=list(pool.map(lambda pair:probe(*pair,reader=reader),[(c,d) for c in CANDIDATES for d in days]))
    groups=[]
    for code in CANDIDATES:
        items=[r for r in rows if r["league"]==code]
        events=sum(r["events"] for r in items)
        clean=all(r["error"] is None and not r["invalid"] for r in items)
        groups.append(dict(league=code,events=events,status="observed" if clean and events else "empty_unverified" if clean else "source_issue",samples=items))
    return dict(version="5.59",mode="coverage_research_only",groups=groups,predictionsEnabled=False,usedForSettlement=False)
if __name__=="__main__":
    report=build(datetime.now(TR))
    Path("global_coverage.json").write_text(json.dumps(report,indent=2))
    print([(g["league"],g["events"],g["status"]) for g in report["groups"]])
    assert any(g["status"]=="observed" for g in report["groups"])
