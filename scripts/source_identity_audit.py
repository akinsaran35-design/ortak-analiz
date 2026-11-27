"""V5.38: inspect source team labels and unresolved fixture identities without fuzzy merging."""
import csv,io,json
from collections import Counter,defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from nine_league_results_pilot import SOURCES,result_key
from football_statistics_pilot import parse
from league_config import LEAGUES
from results_source_pilot import read,TR

def inspect(raw,fixtures,code,sport,cutoff):
    history,_,invalid=parse(raw,code,sport,cutoff)
    counts=Counter(t for r in history for t in (r["home"],r["away"]))
    labels=defaultdict(set)
    for row in csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))):
        for field in ("HomeTeam","AwayTeam"):
            name=row.get(field)
            if name and name.strip():
                key=result_key(name,code,sport)
                if key in counts:labels[key].add(name.strip())
    teams=sorted({name for f in fixtures for name in f["match"].split(" – ")})
    resolved=[];unresolved=[]
    for name in teams:
        k=result_key(name,code,sport)
        row=dict(fixtureName=name,canonicalKey=k,completedMatches=counts[k],sourceLabels=sorted(labels[k]))
        (resolved if counts[k] else unresolved).append(row)
    return dict(completedMatches=len(history),invalid=invalid,resolved=resolved,unresolved=unresolved,sourceTeams=[dict(canonicalKey=k,labels=sorted(labels[k]),completedMatches=n) for k,n in sorted(counts.items())])

def build(daily,reader=read):
    stamp=datetime.fromisoformat(daily["updatedAt"])
    if stamp.tzinfo is None:raise ValueError("timezone")
    cutoff=stamp.astimezone(TR).date();year=cutoff.year-(cutoff.month<7)
    def group(entry):
        label,code,sport=entry
        url=f"https://football-data.co.uk/mmz4281/{year%100:02d}{(year+1)%100:02d}/{SOURCES[code][0]}.csv"
        fixtures=[f for f in daily["upcoming"] if f["league"]==label]
        try:return dict(league=code,source=url,error=None,**inspect(reader(url),fixtures,code,sport,cutoff))
        except (OSError,ValueError,TypeError,KeyError,AttributeError) as exc:return dict(league=code,source=url,error=type(exc).__name__,resolved=[],unresolved=[],sourceTeams=[])
    with ThreadPoolExecutor(max_workers=6) as pool:groups=list(pool.map(group,LEAGUES))
    return dict(version="5.38",mode="source_identity_audit_only",dailyUpdatedAt=daily["updatedAt"],cutoffExclusive=cutoff.isoformat(),automaticAliasChanges=False,predictionsEnabled=False,decision="PAS",groups=groups)

if __name__=="__main__":
    r=build(json.loads(Path("daily.json").read_text(encoding="utf-8")))
    Path("source_identity_audit.json").write_text(json.dumps(r,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    for g in r["groups"]:print(json.dumps(g,ensure_ascii=False))
    if not any(g["sourceTeams"] for g in r["groups"]):raise SystemExit("No source labels")
