"""V5.51 compare available same-division and lower-division history without changing forecasts."""
import json
from datetime import datetime,date
from pathlib import Path
from h2h_history_research import collect,EXTRA_DIVISIONS
from nine_league_results_pilot import result_key,SOURCES
from league_config import LEAGUES
from results_source_pilot import TR,read

TARGETS={"en.1":("Hull City AFC",),"de.1":("SV 07 Elversberg","SC Paderborn 07","FC Schalke 04"),"fr.1":("ES Troyes AC",)}
def coverage(rows,key,cutoff):
    unique={};conflicts=set()
    year=cutoff.year-(cutoff.month<7)
    for r in rows:
        d=date.fromisoformat(r["date"])
        if not date(year-1,7,1)<=d<cutoff or key not in (r["home"],r["away"]):continue
        k=(r["date"],r["home"],r["away"])
        score=tuple(r["score"])
        if k in unique and unique[k]!=score:conflicts.add(k)
        unique[k]=score
    valid=[k for k in unique if k not in conflicts]
    return dict(sample=len(valid),latest=max((k[0] for k in valid),default=None),conflicts=len(conflicts))
def build(now,reader=read):
    cutoff=now.astimezone(TR).date();groups=[]
    for _,code,sport in LEAGUES:
        if code not in TARGETS:continue
        primary,ps,pe,pi=collect(code,sport,cutoff,reader)
        extra,es,ee,ei=collect(code,sport,cutoff,reader,EXTRA_DIVISIONS[code])
        teams=[]
        for label in TARGETS[code]:
            key=result_key(label,code,sport)
            teams.append(dict(team=label,canonical=key,sameDivision=coverage(primary,key,cutoff),otherDivision=coverage(extra,key,cutoff)))
        groups.append(dict(league=code,primary=SOURCES[code][0],extra=EXTRA_DIVISIONS[code],sourceErrors=pe+ee,invalidRows=pi+ei,teams=teams))
    return dict(version="5.51",mode="history_coverage_diagnostic_only",updatedAt=now.isoformat(),cutoffExclusive=cutoff.isoformat(),groups=groups,archivesModified=False,predictionsEnabled=False,decision="PAS")
if __name__=="__main__":
    r=build(datetime.now(TR))
    Path("prospective_history_coverage.json").write_text(json.dumps(r,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(r,ensure_ascii=False))
    if any(g["sourceErrors"] for g in r["groups"]):raise SystemExit("Incomplete source history")
