"""Bounded current-round evidence only. OpenLigaDB data under ODbL 1.0."""
import json
from datetime import datetime,timedelta,timezone
from urllib.request import Request,urlopen
from results_source_pilot import TR
BASE="https://api.openligadb.de/getmatchdata/"
CODES=("bl1","bl2","bl3")
ATTRIBUTION="Data from OpenLigaDB (www.openligadb.de), licensed under ODbL 1.0"
def read(url):
    req=Request(url,headers={"User-Agent":"OrtakAnaliz/7.29 (+https://ortak-analiz.vercel.app)","Accept":"application/json"})
    with urlopen(req,timeout=12) as response:
        return json.loads(response.read(2_000_001))
def inspect(rows,now):
    if not isinstance(rows,list) or len(rows)>100:raise ValueError("schema")
    seen=set();duplicates=set();candidates={}
    for m in rows:
        try:
            ident=m["matchID"]
            if type(ident) is not int or ident<=0:continue
            if ident in seen:duplicates.add(ident)
            seen.add(ident)
            kickoff=datetime.fromisoformat(m["matchDateTimeUTC"].replace("Z","+00:00"))
            if kickoff.tzinfo is None or not timedelta(0)<=now-kickoff<=timedelta(hours=3):continue
            if m["matchIsFinished"] is not False:continue
            ids=[m[s]["teamId"] for s in ("team1","team2")]
            if any(type(v) is not int or v<=0 for v in ids) or ids[0]==ids[1]:continue
            goals=m.get("goals")
            if not isinstance(goals,list):goals=None
            # A not-finished fixture is not proof it actually started.
            candidates[ident]={"goalEntries":len(goals) if goals is not None else None}
        except (TypeError,KeyError,ValueError,AttributeError):continue
    valid=[v for k,v in candidates.items() if k not in duplicates]
    return dict(roundFixtures=len(rows),unfinishedKickoffWindow=len(valid),
                candidatesWithGoalEntries=sum((v["goalEntries"] or 0)>0 for v in valid),
                duplicateIds=len(duplicates),actualLiveStatusVerified=False,
                liveScoreVerified=False,clockAvailable=False,xgAvailable=False)
def probe(now,reader=read):
    groups=[]
    for code in CODES:
        try:groups.append(dict(league=code,status="checked",**inspect(reader(BASE+code),now)))
        except (OSError,ValueError,TypeError,KeyError,AttributeError) as exc:
            groups.append(dict(league=code,status="unverified",error=type(exc).__name__))
    return dict(version="7.29",mode="current_round_coverage_only",source="OpenLigaDB",
                license="ODbL-1.0",attribution=ATTRIBUTION,updatedAt=now.isoformat(),
                groups=groups,requestsAttempted=len(CODES),predictionsEnabled=False,decision="PAS")
if __name__=="__main__":print(json.dumps(probe(datetime.now(TR)),ensure_ascii=False))
