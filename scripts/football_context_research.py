"""V5.23 descriptive context: league, venue and historical referee evidence."""
import csv,io,json
from collections import defaultdict,Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from football_statistics_pilot import parse,describe,integer
from nine_league_results_pilot import SOURCES,result_key
from league_config import LEAGUES
from results_source_pilot import read,TR

def mean(values):
    return sum(values)/len(values) if values else None

def league_summary(rows):
    out={}
    for metric in ("goals","corners","yellowCards","redCards","halfTimeGoals"):
        pairs=[r["score"] if metric=="goals" else r["stats"][metric] for r in rows if metric=="goals" or metric in r["stats"]]
        out[metric]=dict(sample=len(pairs),homeAverage=mean([h for h,a in pairs]),awayAverage=mean([a for h,a in pairs]),totalAverage=mean([h+a for h,a in pairs]))
    return out

def half_history(rows):
    counts=Counter();n=0
    for r in rows:
        ht=r["stats"].get("halfTimeGoals")
        if ht is None:continue
        h,a=ht;f,g=r["score"];s,t=f-h,g-a
        if min(s,t)<0:continue
        n+=1
        counts["firstOver05"]+=int(h+a>=1)
        counts["firstOver15"]+=int(h+a>=2)
        counts["firstBtts"]+=int(h>0 and a>0)
        counts["secondBtts"]+=int(s>0 and t>0)
        counts["bothHalvesBtts"]+=int(min(h,a,s,t)>0)
        result=lambda x,y:"1" if x>y else "2" if x<y else "X"
        counts["halfFull:"+result(h,a)+"/"+result(f,g)]+=1
    keys=["firstOver05","firstOver15","firstBtts","secondBtts","bothHalvesBtts"]+["halfFull:"+h+"/"+f for h in ("1","X","2") for f in ("1","X","2")]
    return dict(sample=n,counts={k:counts[k] for k in keys},observedFrequency={k:counts[k]/n if n else None for k in keys})

def referee_summary(raw,rows,code,sport):
    # Exact source labels only. No fuzzy referee identity or upcoming assignment.
    accepted={(r["date"],r["home"],r["away"]):r for r in rows}
    names=defaultdict(set)
    for x in csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))):
        d=None
        for fmt in ("%d/%m/%Y","%d/%m/%y"):
            try:d=datetime.strptime(x["Date"],fmt).date().isoformat();break
            except (ValueError,TypeError,KeyError):pass
        if d is None:continue
        k=(d,result_key(x.get("HomeTeam",""),code,sport),result_key(x.get("AwayTeam",""),code,sport))
        r=accepted.get(k)
        if not r or [integer(x.get("FTHG")),integer(x.get("FTAG"))]!=r["score"]:continue
        name=(x.get("Referee") or "").strip()
        names[k].add(name)
    refs=defaultdict(list);ambiguous=0
    for k,labels in names.items():
        if len(labels)!=1:ambiguous+=1;continue
        label=next(iter(labels))
        if label:refs[label].append(accepted[k])
    return dict(assignedFixtures=sum(map(len,refs.values())),ambiguousFixtures=ambiguous,upcomingAssignmentsVerified=False,identityVerified=False,labels=[dict(label=label,matches=len(rs),yellowCards=league_summary(rs)["yellowCards"],redCards=league_summary(rs)["redCards"]) for label,rs in sorted(refs.items()) if len(rs)>=5])

def venue_context(rows,team,venue):
    subset=[r for r in rows if r[venue]==team]
    recent=sorted(subset,key=lambda r:r["date"],reverse=True)[:10]
    out=describe(recent,team)
    goals=[r["score"] if venue=="home" else list(reversed(r["score"])) for r in recent]
    out["goals"]=dict(sample=len(goals),forAverage=mean([h for h,a in goals]),againstAverage=mean([a for h,a in goals]))
    out["halves"]=half_history(recent)
    return out

def build(daily,now,reader=read):
    cutoff=now.astimezone(TR).date()
    year=cutoff.year-(cutoff.month<7)
    def group(entry):
        label,code,sport=entry
        csv_code,_=SOURCES[code]
        url=f"https://football-data.co.uk/mmz4281/{year%100:02d}{(year+1)%100:02d}/{csv_code}.csv"
        g=dict(league=code,leagueName=label,source=url,error=None,rows=[])
        try:
            raw=reader(url)
            rows,available,invalid=parse(raw,code,sport,cutoff)
            g.update(historicalRows=len(rows),invalid=invalid,latestCompletedDate=max((r["date"] for r in rows),default=None),leagueAverages=league_summary(rows),halves=half_history(rows),referees=referee_summary(raw,rows,code,sport))
            seen=set()
            for f in daily.get("upcoming",[]):
                if f.get("league")!=label or f.get("date","")<cutoff.isoformat():continue
                h,a=f["match"].split(" – ")
                hk,ak=result_key(h,code,sport),result_key(a,code,sport)
                k=(f["date"],hk,ak)
                if not hk or not ak or hk==ak or k in seen:continue
                seen.add(k)
                g["rows"].append(dict(date=f["date"],match=f["match"],homeVenue=venue_context(rows,hk,"home"),awayVenue=venue_context(rows,ak,"away")))
        except (OSError,ValueError,TypeError,KeyError,AttributeError) as exc:
            g.update(error=type(exc).__name__,rows=[])
        return g
    with ThreadPoolExecutor(max_workers=4) as pool:groups=list(pool.map(group,LEAGUES))
    return dict(version="5.23",updatedAt=now.isoformat(),dailyUpdatedAt=daily.get("updatedAt"),cutoffExclusive=cutoff.isoformat(),source="football-data.co.uk",mode="descriptive_research",predictionsEnabled=False,modelCalibrated=False,decision="PAS",groups=groups)

if __name__=="__main__":
    r=build(json.loads(Path("daily.json").read_text(encoding="utf-8")),datetime.now(TR))
    Path("football_context_research.json").write_text(json.dumps(r,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    for g in r["groups"]:
        print(json.dumps(dict(league=g["league"],error=g["error"],historicalRows=g.get("historicalRows",0),latestCompletedDate=g.get("latestCompletedDate"),halfTimeSample=g.get("halves",{}).get("sample",0),refereeLabels=len(g.get("referees",{}).get("labels",[])),refereeFixtures=g.get("referees",{}).get("assignedFixtures",0),fixtures=len(g["rows"])),ensure_ascii=False))
    if not any(g["error"] is None and g["historicalRows"] for g in r["groups"]):raise SystemExit("No historical evidence")
