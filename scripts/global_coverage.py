"""Read-only global scoreboard coverage probe; no prediction or settlement."""
import json
from collections import Counter
from urllib.error import HTTPError,URLError
from datetime import datetime,timedelta
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from scoreboard_snapshot import parse
from results_source_pilot import read,TR

CANDIDATES=("eng.3","eng.4","ger.2","esp.2","ita.2","fra.2","bel.1","sco.1","sui.1","aut.1","den.1","nor.1","swe.1","gre.1","pol.1","usa.1","mex.1","bra.1","arg.1","col.1","chi.1","jpn.1","kor.1","aus.1","chn.1","sau.1","ind.1","rsa.1","egy.1","uefa.champions","uefa.europa","afc.champions","conmebol.libertadores")
CANDIDATES=tuple(dict.fromkeys((*CANDIDATES,"eng.fa","eng.league_cup","eng.5","ned.2","por.2","tur.2","bel.2","sco.2","ger.3","fra.3","esp.copa_del_rey","ita.coppa_italia","ger.dfb_pokal","uefa.europa.conf","bra.2","arg.2","mex.2","usa.usl.1","jpn.2","kor.2","chn.2","idn.1","tha.1","mys.1","sgp.1","isr.1","rou.1","cze.1","cro.1","srb.1","ukr.1","hun.1","fin.1","isl.1","irl.1","chi.2","per.1","ecu.1","uru.1","par.1","bol.1","ven.1")))
BASE="https://site.api.espn.com/apis/site/v2/sports/soccer/"
def probe(code,day,reader=read):
    url=BASE+code+"/scoreboard?dates="+day.replace("-","")
    result=dict(league=code,date=day,source=url,events=0,invalid=0,error=None)
    try:
        payload=json.loads(reader(url))
        rows,invalid=parse(payload,day)
        result.update(events=len(rows),invalid=invalid,providerLeagues=[dict(id=x.get("id"),slug=x.get("slug"),name=x.get("name")) for x in payload.get("leagues",[]) if isinstance(x,dict)])
    except HTTPError as exc:
        result["error"]="HTTP_"+str(exc.code)
    except URLError as exc:
        result["error"]="network_"+type(exc.reason).__name__
    except (OSError,ValueError,TypeError,KeyError,AttributeError) as exc:
        result["error"]=type(exc).__name__
        result["detail"]=str(exc)[:160]
    return result
# Candidate aliases must be confirmed against provider metadata before activation.
ALIASES={"pol.1":("pol.1","pol.ekstraklasa"),"kor.1":("kor.1","kor.kleague.1"),"sau.1":("sau.1","ksa.1"),"egy.1":("egy.1","egy.premier"),"por.2":("por.2","por.liga.2"),"ger.3":("ger.3","ger.3.liga")}
def recover(code,days,reader):
    attempts=[]
    for alias in ALIASES.get(code,(code,)):
        samples=[probe(alias,d,reader) for d in days]
        attempts.append(dict(alias=alias,samples=samples,events=sum(x["events"] for x in samples),metadata=[m for x in samples for m in x.get("providerLeagues",[])]))
    return dict(league=code,attempts=attempts,requiresIdentityReview=True,activated=False)

def build(now,reader=read):
    days=[(now.astimezone(TR).date()-timedelta(days=i)).isoformat() for i in (0,1,2,3,4,5,6,7)]
    with ThreadPoolExecutor(max_workers=8) as pool:
        rows=list(pool.map(lambda pair:probe(*pair,reader=reader),[(c,d) for c in CANDIDATES for d in days]))
    groups=[]
    for code in CANDIDATES:
        items=[r for r in rows if r["league"]==code]
        events=sum(r["events"] for r in items)
        clean=all(r["error"] is None and not r["invalid"] for r in items)
        groups.append(dict(league=code,events=events,status="observed" if clean and events else "empty_unverified" if clean else "source_issue",errorCounts=dict(Counter(r["error"] for r in items if r["error"])),invalidRows=sum(r["invalid"] for r in items),samples=items))
    return dict(version="5.65",mode="coverage_research_only",recovery=[recover(c,days,reader) for c in ALIASES],candidateCount=len(CANDIDATES),queryCount=len(rows),groups=groups,predictionsEnabled=False,usedForSettlement=False)
if __name__=="__main__":
    report=build(datetime.now(TR))
    Path("global_coverage.json").write_text(json.dumps(report,indent=2))
    print([(g["league"],g["events"],g["status"],g["errorCounts"],g["invalidRows"]) for g in report["groups"]])
    print("Alias recovery:",[(r["league"],[(a["alias"],a["events"]) for a in r["attempts"]]) for r in report["recovery"]])
    assert any(g["status"]=="observed" for g in report["groups"])
