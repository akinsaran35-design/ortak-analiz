"""Read-only source audit for six additional competitions; never writes forecast archives."""
import json,math
from collections import Counter
from datetime import datetime,timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from results_source_pilot import read,csv_results,espn_results,TR
from match_odds import normalize

# League-specific, evidence-reviewed aliases only; never infer from score agreement.
# Observed in source name evidence, run 46066942435; scoped to competition.
REVIEWED_ALIASES={
    "sco.1": {
        "hearts": "heart of midlothian"
    },
    "bel.1": {
        "oud heverlee leuven": "oh leuven",
        "beveren": "waasland beveren",
        "gent": "kaa gent",
        "kortrijk": "kv kortrijk",
        "st gilloise": "union st gilloise",
        "standard": "standard liege",
        "charleroi": "royal charleroi",
        "st truiden": "sint truidense",
        "genk": "racing genk",
        "mechelen": "kv mechelen",
        "waregem": "zulte waregem",
        "cercle brugge": "cercle brugge ksv",
        "westerlo": "kvc westerlo"
    },
    "ger.2": {
        "cottbus": "energie cottbus",
        "hertha": "hertha berlin",
        "dresden": "dynamo dresden",
        "karlsruhe": "karlsruher",
        "osnabruck": "vfl osnabruck",
        "nurnberg": "1 nurnberg",
        "braunschweig": "tsv eintracht braunschweig",
        "hannover": "hannover 96",
        "greuther furth": "spvgg greuther furth",
        "bochum": "vfl bochum",
        "wolfsburg": "vfl wolfsburg",
        "bielefeld": "arminia bielefeld",
        "magdeburg": "1 magdeburg",
        "darmstadt": "sv darmstadt 98",
        "heidenheim": "1 heidenheim 1846"
    },
    "esp.2": {
        "celta b": "rc celta fortuna",
        "valladolid": "real valladolid",
        "oviedo": "real oviedo",
        "sp gijon": "sporting gijon",
        "sabadell": "cd sabadell",
        "sociedad b": "real sociedad ii"
    },
    "ita.2": {
        "avellino": "us avellino",
        "verona": "hellas verona"
    },
    "fra.2": {
        "laval": "stade laval",
        "reims": "stade de reims",
        "st etienne": "saint etienne",
        "clermont": "clermont foot",
        "nancy": "as nancy lorraine",
        "dijon": "dijon fco",
        "rodez": "rodez aveyron",
        "red star": "red star 93"
    }
}
def team_key(code,name):
    n=normalize(name)
    return REVIEWED_ALIASES.get(code,{}).get(n,n)

def unmatched_names(rows):
    out={}
    for source in ('csv_only','espn_only'):
        subset=[r for r in rows if r['status']==source]
        out[source]=sorted({r[k] for r in subset for k in ('home','away')})
    return out

COMPETITIONS=(("sco.1","SC0"),("bel.1","B1"),("ger.2","D2"),("esp.2","SP2"),("ita.2","I2"),("fra.2","F2"))
HISTORY_WINDOW_DAYS=90
SAMPLE_DATE_LIMIT=90

def audit_league(code,csv_code,now,reader=read):
    first=now.date()-timedelta(days=HISTORY_WINDOW_DAYS)
    last=now.date()-timedelta(days=1)
    season=lambda d:d.year if d.month>=7 else d.year-1
    out=dict(league=code,sourceUrls=[],errors=[],days=[],rows=[])
    # Exact normalized names only: no fuzzy identity guesses.
    identity=lambda d,h,a:(d,team_key(code,h),team_key(code,a))
    primary={}
    for year in range(season(first),season(last)+1):
        csv_url=f"https://football-data.co.uk/mmz4281/{year%100:02d}{(year+1)%100:02d}/{csv_code}.csv"
        out["sourceUrls"].append(csv_url)
        try: primary.update(csv_results(reader(csv_url),identity))
        except (OSError,ValueError,TypeError,KeyError,AttributeError) as exc:
            out["errors"].append(dict(source="csv",season=year,type=type(exc).__name__))
    days=sorted({k[0] for k in primary if (now.date()-timedelta(days=HISTORY_WINDOW_DAYS)).isoformat()<=k[0]<now.date().isoformat()},reverse=True)[:SAMPLE_DATE_LIMIT]
    out["days"]=days
    for day in days:
        url=f"https://site.api.espn.com/apis/site/v2/sports/soccer/{code}/scoreboard?dates={day.replace('-','')}"
        out["sourceUrls"].append(url)
        try: secondary=espn_results(json.loads(reader(url)),day,identity)
        except (OSError,ValueError,TypeError,KeyError,AttributeError) as exc:
            out["errors"].append(dict(source="espn",date=day,type=type(exc).__name__))
            continue
        for k in sorted({k for k in primary if k[0]==day}|{k for k in secondary if k[0]==day}):
            a,b=primary.get(k),secondary.get(k)
            status="corroborated" if a is not None and a==b else "conflict" if a is not None and b is not None else "csv_only" if a is not None else "espn_only"
            if not k[1] or not k[2] or k[1]==k[2]:status="invalid_identity"
            out["rows"].append(dict(date=day,home=k[1],away=k[2],csv=a,espn=b,status=status))
    return out

def verified_rows(rows):
    """Exclude every duplicated identity and non-corroborated result."""
    grouped={}
    for r in rows:
        k=(r["league"],r["date"],r["home"],r["away"])
        grouped.setdefault(k,[]).append(r)
    for records in grouped.values():
        if len(records)!=1:
            continue
        r=records[0]
        s=r.get("csv")
        if r.get("status")!="corroborated" or s!=r.get("espn") or not isinstance(s,list) or len(s)!=2 or any(type(x) is not int or x<0 for x in s):
            continue
        yield r

def outcome_baseline(rows):
    """Descriptive outcome frequencies, not forecast accuracy."""
    counts=Counter()
    for r in verified_rows(rows):
        h,a=r["csv"]
        counts["matches"]+=1
        counts["over15"]+=int(h+a>=2)
        counts["over25"]+=int(h+a>=3)
        counts["btts"]+=int(h>0 and a>0)
    n=counts["matches"]
    return dict(matches=n,excludedRows=len(rows)-n,markets={k:dict(occurred=counts[k],ratePct=round(100*counts[k]/n,2) if n else None) for k in ("over15","over25","btts")},metric="observed_outcome_frequency",predictionAccuracy=None)

MARKETS=("over15","over25","btts")
MIN_TRAIN_MATCHES=20

def labels(h,a):
    return (int(h+a>=2),int(h+a>=3),int(h>0 and a>0))

def chronological_backtest(rows):
    """Research-only league-mean Poisson benchmark; no same-day training."""
    by_day={}
    for r in verified_rows(rows):
        by_day.setdefault(r["date"],[]).append(r)
    history={}
    predictions={k:[] for k in MARKETS}
    evaluated=0
    for day,group in sorted(by_day.items()):
        for r in group:
            past=history.get(r["league"],[])
            if len(past)<MIN_TRAIN_MATCHES:
                continue
            n=len(past)
            h=sum(x[0] for x in past)/n
            a=sum(x[1] for x in past)/n
            total=h+a
            p=(1-math.exp(-total)*(1+total),1-math.exp(-total)*(1+total+total*total/2),(1-math.exp(-h))*(1-math.exp(-a)))
            y=labels(*r["csv"])
            previous=[labels(*s) for s in past]
            for i,k in enumerate(MARKETS):
                empirical=(sum(v[i] for v in previous)+1)/(n+2)
                predictions[k].append((min(1,max(0,p[i])),y[i],empirical))
            evaluated+=1
        for r in group:
            history.setdefault(r["league"],[]).append(r["csv"])
    metrics={}
    for k,items in predictions.items():
        n=len(items)
        bins=[]
        for j in range(5):
            subset=[(p,y) for p,y,_ in items if min(4,int(p*5))==j]
            if subset:
                bins.append(dict(lower=j/5,upper=(j+1)/5,n=len(subset),meanProbability=round(sum(p for p,y in subset)/len(subset),6),observedFrequency=round(sum(y for p,y in subset)/len(subset),6)))
        metrics[k]=dict(n=n,accuracyPct=round(100*sum((p>=0.5)==bool(y) for p,y,_ in items)/n,2) if n else None,
            brier=round(sum((p-y)**2 for p,y,_ in items)/n,6) if n else None,
            empiricalBrier=round(sum((q-y)**2 for p,y,q in items)/n,6) if n else None,calibrationBins=bins)
    return dict(model="league_mean_independent_poisson_benchmark",mode="historical_replay_only",minTrainingMatches=MIN_TRAIN_MATCHES,evaluatedMatches=evaluated,
        warmupMatches=sum(len(g) for g in by_day.values())-evaluated,markets=metrics,sameDayTraining=False,productionModelValidated=False)

TEAM_PRIOR_MATCHES=5
RECENT_MATCHES=5

def team_goal_means(past,home,away):
    """Venue-specific attack/defence with league shrinkage and recent form."""
    n=len(past)
    lh=sum(r["csv"][0] for r in past)/n
    la=sum(r["csv"][1] for r in past)/n
    def mean_for(team,venue,index,prior):
        games=[r["csv"][index] for r in past if r[venue]==team]
        recent=games[-RECENT_MATCHES:]
        return (sum(games)+sum(recent)+TEAM_PRIOR_MATCHES*prior)/(len(games)+len(recent)+TEAM_PRIOR_MATCHES)
    ha=mean_for(home,"home",0,lh)
    ad=mean_for(away,"away",0,lh)
    aa=mean_for(away,"away",1,la)
    hd=mean_for(home,"home",1,la)
    return ((ha*ad/lh if lh else 0),(aa*hd/la if la else 0))

def goal_probabilities(h,a):
    total=h+a
    return (1-math.exp(-total)*(1+total),1-math.exp(-total)*(1+total+total*total/2),(1-math.exp(-h))*(1-math.exp(-a)))

def team_form_backtest(rows):
    """Paired chronological comparison, not a production model approval."""
    by_day={}
    for r in verified_rows(rows):
        by_day.setdefault(r["date"],[]).append(r)
    history={}
    samples={k:[] for k in MARKETS}
    evaluated=0
    for day,group in sorted(by_day.items()):
        group=sorted(group,key=lambda r:(r["league"],r["home"],r["away"]))
        for r in group:
            past=history.get(r["league"],[])
            n=len(past)
            if n<MIN_TRAIN_MATCHES:
                continue
            baseline=goal_probabilities(sum(x["csv"][0] for x in past)/n,sum(x["csv"][1] for x in past)/n)
            team=goal_probabilities(*team_goal_means(past,r["home"],r["away"]))
            for k,p,q,y in zip(MARKETS,team,baseline,labels(*r["csv"])):
                samples[k].append((min(1,max(0,p)),min(1,max(0,q)),y))
            evaluated+=1
        for r in group:
            history.setdefault(r["league"],[]).append(r)
    metrics={}
    for k,items in samples.items():
        n=len(items)
        def score(index):
            if not n:
                return dict(accuracyPct=None,brier=None)
            return dict(accuracyPct=round(100*sum((r[index]>=0.5)==bool(r[2]) for r in items)/n,2),brier=round(sum((r[index]-r[2])**2 for r in items)/n,6))
        metrics[k]=dict(n=n,team=score(0),leagueMean=score(1))
    return dict(model="venue_team_shrunk_poisson",evaluatedMatches=evaluated,markets=metrics,priorMatches=TEAM_PRIOR_MATCHES,recentVenueMatches=RECENT_MATCHES,sameDayTraining=False,productionModelValidated=False)

def build(now,reader=read):
    now=now.astimezone(TR)
    with ThreadPoolExecutor(max_workers=3) as pool:
        leagues=list(pool.map(lambda x:audit_league(*x,now,reader),COMPETITIONS))
    for g in leagues:
        g["counts"]=dict(Counter(x["status"] for x in g["rows"]))
        g["unmatchedNames"]=unmatched_names(g["rows"])
    for g in leagues:
        g["outcomeBaseline"]=outcome_baseline([dict(r,league=g["league"]) for r in g["rows"]])
    baseline=outcome_baseline([dict(r,league=g["league"]) for g in leagues for r in g["rows"]])
    replay=chronological_backtest([dict(r,league=g["league"]) for g in leagues for r in g["rows"]])
    team_replay=team_form_backtest([dict(r,league=g["league"]) for g in leagues for r in g["rows"]])
    return dict(version="6.31",teamFormBacktest=team_replay,chronologicalBacktest=replay,outcomeBaseline=baseline,historyWindowDays=HISTORY_WINDOW_DAYS,sampleDateLimit=SAMPLE_DATE_LIMIT,mode="source_audit_only",updatedAt=now.isoformat(),leagues=leagues,
        configured=len(COMPETITIONS),responding=sum(bool(g["days"]) and not g["errors"] for g in leagues),
        corroborated=sum(g["counts"].get("corroborated",0) for g in leagues),
        archivesModified=False,predictionsEnabled=False,realBettingEnabled=False,decision="PAS")

if __name__=="__main__":
    report=build(datetime.now(TR))
    Path("extra_league_score_audit.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    for g in report["leagues"]:
        print("LEAGUE_AUDIT",json.dumps({k:g[k] for k in ("league","days","counts","errors")},ensure_ascii=False))
        print("NAME_EVIDENCE",json.dumps({"league":g["league"],"names":g["unmatchedNames"],"rows":[r for r in g["rows"] if r["status"] in ("csv_only","espn_only")]},ensure_ascii=False))
    print("TEAM_FORM_BACKTEST",json.dumps(report["teamFormBacktest"]))
    print("CHRONOLOGICAL_BACKTEST",json.dumps(report["chronologicalBacktest"]))
    print("OUTCOME_BASELINE",json.dumps(report["outcomeBaseline"]))
    print("AUDIT_TOTAL",json.dumps({k:report[k] for k in ("configured","responding","corroborated","archivesModified")}))
