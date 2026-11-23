"""Ortak Analiz V1.5 — reproducible statistical candidates, never unverified bets.
Source: community OpenFootball football.json. No odds or kickoff-time claims.
"""
import json, math, urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

TR = timezone(timedelta(hours=3))
now = datetime.now(TR)
today = now.date()
year = today.year if today.month >= 7 else today.year - 1
season = f"{year}-{str(year+1)[-2:]}"
LEAGUES = {
    "İngiltere Premier Lig":"en.1", "İngiltere Championship":"en.2",
    "Almanya Bundesliga":"de.1", "İspanya La Liga":"es.1",
    "İtalya Serie A":"it.1", "Fransa Ligue 1":"fr.1"
}
BASE="https://raw.githubusercontent.com/openfootball/football.json/master"
def date_of(s):
    try: return datetime.strptime(str(s)[:10],"%Y-%m-%d").date()
    except (ValueError,TypeError): return None
def name(v):
    return v if isinstance(v,str) else (v.get("name","") if isinstance(v,dict) else "")
def flatten(data):
    if isinstance(data,list): return data
    if not isinstance(data,dict): return []
    if isinstance(data.get("matches"),list): return data["matches"]
    return [m for r in data.get("rounds",[]) if isinstance(r,dict)
            for m in r.get("matches",[]) if isinstance(m,dict)]
def goals(m):
    """Only accept explicit full-time goals, never half-time or penalty results."""
    score=m.get("score")
    if isinstance(score,dict):
        ft=score.get("ft") or score.get("fulltime") or score.get("fullTime")
        if isinstance(ft,list) and len(ft)==2 and all(type(x)==int and x>=0 for x in ft):
            return tuple(ft)
        if isinstance(ft,dict):
            h=ft.get("home")
            a=ft.get("away")
            if type(h)==int and type(a)==int and h>=0 and a>=0: return h,a
    # football.json commonly stores score.ft as [home, away].
    return None
def poisson_over(lam,threshold):
    # P(total goals > threshold) with Poisson(lambda)
    return 1-sum(math.exp(-lam)*lam**k/math.factorial(k) for k in range(threshold+1))
def btts(lh,la):
    return (1-math.exp(-lh))*(1-math.exp(-la))
def safe_pct(x): return round(100*max(0,min(1,x)),1)
def summarize(hist,team,home):
    games=[(d,gf,ga) for d,h,a,gh,gaway in hist
           if (h==team if home else a==team)
           for gf,ga in [(gh,gaway) if home else (gaway,gh)]]
    games.sort(key=lambda x:x[0],reverse=True)
    recent=games[:8]
    if len(recent)<5: return None
    return {"n":len(recent),"gf":sum(x[1] for x in recent)/len(recent),
            "ga":sum(x[2] for x in recent)/len(recent)}
report={
 "date":today.isoformat(),"decision":"PAS","picks":[],
 "updatedAt":now.isoformat(timespec="seconds"),
 "version":"1.5","source":"https://github.com/openfootball/football.json",
 "method":"Son 8 iç/dış saha maçından basit Poisson; kalibrasyon ve oran doğrulaması yok.",
 "leaguesChecked":len(LEAGUES),"leaguesLoaded":0,
 "fixturesToday":0,"fixturesNext7Days":0,"leagueDiagnostics":[],
 "upcoming":[],"candidates":[],"candidateCount":0,
 "dataQuality":{"verifiedOdds":False,"verifiedKickoffTimes":False,
                "modelCalibrated":False,"bettingRecommendation":False}
}
for league,code in LEAGUES.items():
    diag={"league":league,"status":"unavailable","today":0,"next7":0,
          "completedMatches":0,"candidates":0}
    try:
        req=urllib.request.Request(f"{BASE}/{season}/{code}.json",
                                  headers={"User-Agent":"OrtakAnaliz/1.5"})
        with urllib.request.urlopen(req,timeout=15) as resp:
            raw=json.loads(resp.read(3_000_000).decode("utf-8"))
        matches=flatten(raw)
        report["leaguesLoaded"]+=1
        diag["status"]="ok" if matches else "empty"
        diag["matchesInFile"]=len(matches)
        history=[]
        upcoming=[]
        for m in matches:
            if not isinstance(m,dict): continue
            d=date_of(m.get("date") or m.get("datetime"))
            h=name(m.get("team1") or m.get("home") or m.get("homeTeam"))
            a=name(m.get("team2") or m.get("away") or m.get("awayTeam"))
            if not d or not h or not a: continue
            result=goals(m)
            if d<today and result is not None:
                history.append((d,h,a,result[0],result[1]))
            if d==today:
                diag["today"]+=1
                report["fixturesToday"]+=1
            if today<=d<=today+timedelta(days=7):
                diag["next7"]+=1
                report["fixturesNext7Days"]+=1
                upcoming.append((d,h,a,result))
        diag["completedMatches"]=len(history)
        for d,h,a,result in upcoming:
            # Do not analyze fixtures already showing final scores.
            if result is not None: continue
            if len(report["upcoming"])<60:
                report["upcoming"].append({"date":d.isoformat(),"league":league,
                                            "match":f"{h} – {a}"})
            hs=summarize(history,h,True)
            aws=summarize(history,a,False)
            if not hs or not aws: continue
            # Simple home/away means. These are uncalibrated illustrative estimates.
            lh=max(.15,min(4,(hs["gf"]+aws["ga"])/2))
            la=max(.15,min(4,(aws["gf"]+hs["ga"])/2))
            probs={"1.5 Üst":safe_pct(poisson_over(lh+la,1)),
                   "2.5 Üst":safe_pct(poisson_over(lh+la,2)),
                   "KG Var":safe_pct(btts(lh,la))}
            report["candidates"].append({
                "date":d.isoformat(),"league":league,"match":f"{h} – {a}",
                "markets":probs,"sample":{"home":hs["n"],"away":aws["n"]},
                "expectedGoals":{"home":round(lh,2),"away":round(la,2)},
                "status":"İstatistiksel ön eleme; bahis önerisi değil",
                "odds":None,"edge":None})
            diag["candidates"]+=1
    except Exception as exc:
        diag["error"]=f"{type(exc).__name__}: {str(exc)[:100]}"
    report["leagueDiagnostics"].append(diag)
report["upcoming"].sort(key=lambda x:(x["date"],x["league"],x["match"]))
report["candidates"].sort(key=lambda x:(x["date"],-x["markets"]["1.5 Üst"],x["match"]))
report["candidateCount"]=len(report["candidates"])
report["candidates"]=report["candidates"][:20]
report["reason"]=(
 f"PAS — {report['leaguesLoaded']}/{report['leaguesChecked']} lig okundu; "
 f"bugün {report['fixturesToday']}, 7 günde {report['fixturesNext7Days']} fikstür; "
 f"{report['candidateCount']} istatistiksel aday. "
 "Yüzdeler kalibre edilmemiş model tahminidir; güncel uluslararası oranlar, "
 "başlama saatleri ve model başarısı doğrulanmadığı için bahis seçimi yapılmadı."
)
Path("daily.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(report["reason"])
for d in report["leagueDiagnostics"]: print(d)
