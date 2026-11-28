"""Read-only source audit for six additional competitions; never writes forecast archives."""
import json,math,random,bisect
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

HYBRID_WEIGHTS=(0.0,0.1,0.25,0.5,0.75,1.0)
MIN_VALIDATION_MATCHES=50

def hybrid_holdout(rows):
    """Select weights on earlier dates; freeze them for later-date evaluation."""
    by_day={}
    for r in verified_rows(rows):
        by_day.setdefault(r["date"],[]).append(r)
    history={}
    samples={k:[] for k in MARKETS}
    for day,group in sorted(by_day.items()):
        group=sorted(group,key=lambda r:(r["league"],r["home"],r["away"]))
        for r in group:
            past=history.get(r["league"],[])
            n=len(past)
            if n<MIN_TRAIN_MATCHES:
                continue
            league=goal_probabilities(sum(x["csv"][0] for x in past)/n,sum(x["csv"][1] for x in past)/n)
            team=goal_probabilities(*team_goal_means(past,r["home"],r["away"]))
            for k,p,q,y in zip(MARKETS,league,team,labels(*r["csv"])):
                samples[k].append((day,min(1,max(0,p)),min(1,max(0,q)),y))
        for r in group:
            history.setdefault(r["league"],[]).append(r)
    days=sorted({r[0] for r in samples[MARKETS[0]]})
    cutoff=days[int(len(days)*0.6)] if len(days)>=2 else None
    metrics={}
    for k,items in samples.items():
        tune=[r for r in items if cutoff and r[0]<cutoff]
        test=[r for r in items if cutoff and r[0]>=cutoff]
        def loss(rows,w):
            return sum(((1-w)*p+w*q-y)**2 for _,p,q,y in rows)/len(rows)
        w=min(HYBRID_WEIGHTS,key=lambda w:loss(tune,w)) if len(tune)>=MIN_VALIDATION_MATCHES else 0.0
        def score(rows,w):
            if not rows:
                return dict(brier=None,accuracyPct=None,meanProbability=None,observedFrequency=None)
            probs=[((1-w)*p+w*q,y) for _,p,q,y in rows]
            return dict(brier=round(loss(rows,w),6),accuracyPct=round(100*sum((p>=0.5)==bool(y) for p,y in probs)/len(rows),2),meanProbability=round(sum(p for p,y in probs)/len(rows),6),observedFrequency=round(sum(y for p,y in probs)/len(rows),6))
        enough=len(tune)>=MIN_VALIDATION_MATCHES and len(test)>=MIN_VALIDATION_MATCHES
        metrics[k]=dict(teamWeight=w,tuneMatches=len(tune),holdoutMatches=len(test),
            hybrid=score(test,w),leagueMean=score(test,0),teamOnly=score(test,1),
            improvementObserved=bool(enough and loss(test,w)<loss(test,0)),enoughForComparison=enough)
    return dict(model="chronological_frozen_weight_hybrid",holdoutStart=cutoff,markets=metrics,weightCandidates=list(HYBRID_WEIGHTS),minimumMatchesPerSplit=MIN_VALIDATION_MATCHES,productionModelValidated=False,externalValidation=False)

DC_RHOS=tuple(i/100 for i in range(-20,21,5))

def dc_tau(h,a,x,y,rho):
    if (x,y)==(0,0): return 1-h*a*rho
    if (x,y)==(0,1): return 1+h*rho
    if (x,y)==(1,0): return 1+a*rho
    if (x,y)==(1,1): return 1-rho
    return 1.0

def fit_dc_rho(past,h,a):
    """Grid likelihood fit conditional on past league goal means."""
    candidates=[rho for rho in DC_RHOS if all(dc_tau(h,a,x,y,rho)>0 for x,y in ((0,0),(0,1),(1,0),(1,1)))]
    return max(candidates,key=lambda rho:(sum(math.log(dc_tau(h,a,*s,rho)) for s in past),-abs(rho)))

def dc_probabilities(h,a,rho):
    if any(dc_tau(h,a,x,y,rho)<=0 for x,y in ((0,0),(0,1),(1,0),(1,1))):
        raise ValueError("invalid Dixon-Coles correction")
    p15,p25,pb=goal_probabilities(h,a)
    delta=math.exp(-h-a)*h*a*rho
    return tuple(min(1,max(0,p)) for p in (p15-delta,p25,pb-delta))

def dixon_coles_backtest(rows):
    """Past-only league-level Dixon-Coles correction, paired with Poisson."""
    by_day={}
    for r in verified_rows(rows):
        by_day.setdefault(r["date"],[]).append(r)
    history={}
    samples={k:[] for k in MARKETS}
    for day,group in sorted(by_day.items()):
        group=sorted(group,key=lambda r:(r["league"],r["home"],r["away"]))
        fitted={}
        for r in group:
            league=r["league"]
            past=history.get(league,[])
            n=len(past)
            if n<MIN_TRAIN_MATCHES:
                continue
            if league not in fitted:
                h=sum(s[0] for s in past)/n
                a=sum(s[1] for s in past)/n
                rho=fit_dc_rho(past,h,a)
                fitted[league]=(goal_probabilities(h,a),dc_probabilities(h,a,rho))
            baseline,dc=fitted[league]
            for k,p,q,y in zip(MARKETS,baseline,dc,labels(*r["csv"])):
                samples[k].append((day,p,q,y))
        for r in group:
            history.setdefault(r["league"],[]).append(r["csv"])
    days=sorted({r[0] for r in samples[MARKETS[0]]})
    cutoff=days[int(len(days)*0.6)] if len(days)>=2 else None
    metrics={}
    for k,items in samples.items():
        test=[r for r in items if cutoff and r[0]>=cutoff]
        n=len(test)
        def score(index):
            if not n: return dict(brier=None,accuracyPct=None)
            return dict(brier=round(sum((r[index]-r[3])**2 for r in test)/n,6),
                accuracyPct=round(100*sum((r[index]>=0.5)==bool(r[3]) for r in test)/n,2))
        metrics[k]=dict(n=n,poisson=score(1),dixonColes=score(2),
            improvementObserved=bool(n>=MIN_VALIDATION_MATCHES and sum((r[2]-r[3])**2-(r[1]-r[3])**2 for r in test)<-1e-10))
    return dict(model="league_mean_dixon_coles",rhoCandidates=list(DC_RHOS),holdoutStart=cutoff,markets=metrics,
        sameDayTraining=False,productionModelValidated=False,externalValidation=False)

SIMULATION_DRAWS=131072
SIMULATION_METHODS=("monte_carlo","sobol","latin_hypercube")

def poisson_cdf(mean,weight=lambda k:1.0):
    if not math.isfinite(mean) or not 0<=mean<=20:
        raise ValueError("mean outside supported range")
    mass=math.exp(-mean)
    raw=[mass]
    k=0
    while k<100 and (k<mean or 1-math.fsum(raw)>1e-13):
        k+=1
        mass*=mean/k
        raw.append(mass)
    weighted=[p*weight(i) for i,p in enumerate(raw)]
    if any(p<0 for p in weighted):
        raise ValueError("negative score mass")
    total=math.fsum(weighted)
    if total<=0:
        raise ValueError("empty distribution")
    cdf=[]
    running=0.0
    for p in weighted:
        running+=p/total
        cdf.append(min(1.0,running))
    cdf[-1]=1.0
    return cdf

def simulation_points(method,n,seed):
    rng=random.Random(seed)
    if type(n) is not int or not 1<=n<=2**20:
        raise ValueError("unsupported draw count")
    if method=="monte_carlo":
        for _ in range(n):
            yield rng.random(),rng.random()
    elif method=="latin_hypercube":
        order=list(range(n))
        rng.shuffle(order)
        for i,j in enumerate(order):
            yield (i+rng.random())/n,(j+rng.random())/n
    elif method=="sobol":
        if n&(n-1):
            raise ValueError("Sobol draw count must be a power of two")
        # First two Sobol dimensions, with independent digital XOR shifts.
        v1=[1<<(31-j) for j in range(32)]
        v2=[1<<31]
        for _ in range(1,32):
            v2.append(v2[-1]^(v2[-1]>>1))
        x=y=0
        sx,sy=rng.getrandbits(32),rng.getrandbits(32)
        for i in range(n):
            if i:
                bit=(i&-i).bit_length()-1
                x^=v1[bit]
                y^=v2[bit]
            yield ((x^sx)+0.5)/2**32,((y^sy)+0.5)/2**32
    else:
        raise ValueError("unknown simulation method")

def simulate_scores(h,a,rho,method,n=SIMULATION_DRAWS,seed=20261128):
    """Sample a Poisson or Dixon-Coles joint score distribution."""
    exact=dc_probabilities(h,a,rho)
    hc=poisson_cdf(h)
    away=[poisson_cdf(a,lambda y:dc_tau(h,a,x,y,rho)) for x in (0,1,2)]
    counts=[0]*3
    for u,v in simulation_points(method,n,seed):
        x=bisect.bisect_right(hc,u)
        y=bisect.bisect_right(away[min(x,2)],v)
        for i,flag in enumerate(labels(x,y)):
            counts[i]+=flag
    rates=[c/n for c in counts]
    return dict(draws=n,seed=seed,markets={k:dict(simulated=round(p,8),analytic=round(q,8),absoluteError=round(abs(p-q),8)) for k,p,q in zip(MARKETS,rates,exact)})

def simulation_audit(rows,n=SIMULATION_DRAWS):
    """Numerical checks on observed league averages, not forecast performance."""
    history={}
    for r in verified_rows(rows):
        history.setdefault(r["league"],[]).append(r["csv"])
    cases=[]
    for league,past in sorted(history.items()):
        if len(past)<MIN_TRAIN_MATCHES:
            continue
        h=sum(s[0] for s in past)/len(past)
        a=sum(s[1] for s in past)/len(past)
        if max(h,a)>20:
            continue
        rho=fit_dc_rho(past,h,a)
        for model,correction in (("poisson",0.0),("dixon_coles",rho)):
            methods={m:simulate_scores(h,a,correction,m,n) for m in SIMULATION_METHODS}
            cases.append(dict(league=league,model=model,homeMean=h,awayMean=a,rho=correction,methods=methods))
    summary={}
    for method in SIMULATION_METHODS:
        errors=[v["absoluteError"] for c in cases for v in c["methods"][method]["markets"].values()]
        summary[method]=dict(meanAbsoluteError=round(sum(errors)/len(errors),8) if errors else None,maxAbsoluteError=max(errors) if errors else None)
    return dict(mode="numerical_validation_only",drawsPerCasePerMethod=n,cases=cases,summary=summary,productionModelValidated=False)

BAYES_PRIOR_SHAPE=1.0
BAYES_PRIOR_RATE=1.0
BAYES_DRAWS=4096

def gamma_poisson_probabilities(hs,ha,n):
    """Independent Gamma-Poisson posterior predictive; rate parameterization."""
    if type(n) is not int or n<0 or min(hs,ha)<0:
        raise ValueError("invalid sufficient statistics")
    shape_h=BAYES_PRIOR_SHAPE+hs
    shape_a=BAYES_PRIOR_SHAPE+ha
    rate=BAYES_PRIOR_RATE+n
    z=rate/(rate+1)
    ph0=z**shape_h
    pa0=z**shape_a
    shape=shape_h+shape_a
    p0=z**shape
    p1=p0*shape/(rate+1)
    p2=p1*(shape+1)/(2*(rate+1))
    return (max(0,1-p0-p1),max(0,1-p0-p1-p2),(1-ph0)*(1-pa0))

def bayesian_simulation(hs,ha,n,draws=BAYES_DRAWS,seed=20261128):
    """Integrate uncertain goal intensities by posterior sampling."""
    if type(draws) is not int or not 1<=draws<=2**20:
        raise ValueError("invalid draws")
    exact=gamma_poisson_probabilities(hs,ha,n)
    rng=random.Random(seed)
    totals=[0.0]*3
    for _ in range(draws):
        h=rng.gammavariate(BAYES_PRIOR_SHAPE+hs,1/(BAYES_PRIOR_RATE+n))
        a=rng.gammavariate(BAYES_PRIOR_SHAPE+ha,1/(BAYES_PRIOR_RATE+n))
        for i,p in enumerate(goal_probabilities(h,a)):
            totals[i]+=p
    return dict(draws=draws,markets={k:dict(analytic=q,simulated=s/draws,absoluteError=abs(q-s/draws)) for k,q,s in zip(MARKETS,exact,totals)})

def bayesian_backtest(rows):
    """Strictly prior-date posterior predictive comparison with Poisson."""
    by_day={}
    for r in verified_rows(rows):
        by_day.setdefault(r["date"],[]).append(r)
    history={}
    samples={k:[] for k in MARKETS}
    for day,group in sorted(by_day.items()):
        group=sorted(group,key=lambda r:(r["league"],r["home"],r["away"]))
        for r in group:
            h,a,n=history.get(r["league"],(0,0,0))
            if n<MIN_TRAIN_MATCHES:
                continue
            base=goal_probabilities(h/n,a/n)
            bayes=gamma_poisson_probabilities(h,a,n)
            for k,p,q,y in zip(MARKETS,base,bayes,labels(*r["csv"])):
                samples[k].append((day,p,q,y))
        for r in group:
            h,a,n=history.get(r["league"],(0,0,0))
            x,y=r["csv"]
            history[r["league"]]=(h+x,a+y,n+1)
    days=sorted({s[0] for s in samples[MARKETS[0]]})
    cutoff=days[int(len(days)*0.6)] if len(days)>=2 else None
    metrics={}
    for k,items in samples.items():
        test=[r for r in items if cutoff and r[0]>=cutoff]
        n=len(test)
        def score(i):
            if not n: return dict(brier=None,accuracyPct=None)
            return dict(brier=round(sum((r[i]-r[3])**2 for r in test)/n,6),accuracyPct=round(100*sum((r[i]>=0.5)==bool(r[3]) for r in test)/n,2))
        metrics[k]=dict(n=n,poisson=score(1),bayesian=score(2))
    checks={l:bayesian_simulation(h,a,n) for l,(h,a,n) in sorted(history.items()) if n>=MIN_TRAIN_MATCHES}
    return dict(model="league_gamma_poisson",holdoutStart=cutoff,markets=metrics,numericalChecks=checks,priorShape=BAYES_PRIOR_SHAPE,priorRate=BAYES_PRIOR_RATE,sameDayTraining=False,productionModelValidated=False,externalValidation=False)

BIVARIATE_SHRINKAGE=20

def bivariate_probabilities(h,a,shared):
    """Exact probabilities for X=U+W, Y=V+W, independent Poisson components."""
    if not all(math.isfinite(x) for x in (h,a,shared)) or not 0<=shared<=min(h,a):
        raise ValueError("invalid bivariate intensities")
    if shared==0:
        return goal_probabilities(h,a)
    independent=h+a-2*shared
    p0=math.exp(-h-a+shared)
    p1=p0*independent
    p2=p0*(independent**2/2+shared)
    return tuple(min(1,max(0,p)) for p in (1-p0-p1,1-p0-p1-p2,1-math.exp(-h)-math.exp(-a)+p0))

def fit_shared_intensity(past,h,a):
    """Regularized nonnegative sample covariance; zero fallback."""
    if len(past)<2:
        return 0.0
    covariance=sum((x-h)*(y-a) for x,y in past)/(len(past)-1)
    return max(0,min(h,a,covariance*len(past)/(len(past)+BIVARIATE_SHRINKAGE)))

def bivariate_backtest(rows):
    """Paired prior-date replay, with shared goal intensity fitted before each date."""
    by_day={}
    for r in verified_rows(rows):
        by_day.setdefault(r["date"],[]).append(r)
    history={}
    samples={k:[] for k in MARKETS}
    for day,group in sorted(by_day.items()):
        group=sorted(group,key=lambda r:(r["league"],r["home"],r["away"]))
        fitted={}
        for r in group:
            league=r["league"]
            past=history.get(league,[])
            n=len(past)
            if n<MIN_TRAIN_MATCHES:
                continue
            if league not in fitted:
                h=sum(x[0] for x in past)/n
                a=sum(x[1] for x in past)/n
                shared=fit_shared_intensity(past,h,a)
                fitted[league]=(goal_probabilities(h,a),bivariate_probabilities(h,a,shared),shared)
            base,bivariate,shared=fitted[league]
            for k,p,q,y in zip(MARKETS,base,bivariate,labels(*r["csv"])):
                samples[k].append((day,p,q,y,shared))
        for r in group:
            history.setdefault(r["league"],[]).append(r["csv"])
    days=sorted({s[0] for s in samples[MARKETS[0]]})
    cutoff=days[int(len(days)*0.6)] if len(days)>=2 else None
    metrics={}
    for k,items in samples.items():
        test=[r for r in items if cutoff and r[0]>=cutoff]
        n=len(test)
        def score(i):
            if not n: return dict(brier=None,accuracyPct=None)
            return dict(brier=round(sum((r[i]-r[3])**2 for r in test)/n,6),accuracyPct=round(100*sum((r[i]>=0.5)==bool(r[3]) for r in test)/n,2))
        metrics[k]=dict(n=n,poisson=score(1),bivariate=score(2),
            nonzeroSharedMatches=sum(r[4]>0 for r in test),
            meanSharedIntensity=round(sum(r[4] for r in test)/n,6) if n else None)
    return dict(model="league_bivariate_poisson",holdoutStart=cutoff,markets=metrics,shrinkageMatches=BIVARIATE_SHRINKAGE,
        sameDayTraining=False,productionModelValidated=False,externalValidation=False)

NB_SHRINKAGE=20

def fit_nb_dispersion(scores,mean):
    """Regularized method of moments; variance = mean + alpha * mean**2."""
    n=len(scores)
    if n<2 or mean<=0:
        return 0.0
    variance=sum((x-mean)**2 for x in scores)/(n-1)
    return max(0,(variance-mean)/mean**2)*n/(n+NB_SHRINKAGE)

def nb_low_mass(mean,alpha):
    if not all(math.isfinite(x) and x>=0 for x in (mean,alpha)):
        raise ValueError("invalid negative binomial parameters")
    if alpha==0:
        p0=math.exp(-mean)
        p1=p0*mean
        return p0,p1,p1*mean/2
    p0=math.exp(-math.log1p(alpha*mean)/alpha)
    ratio=mean/(1+alpha*mean)
    p1=p0*ratio
    return p0,p1,p1*ratio*(1+alpha)/2

def nb_probabilities(h,a,alpha_h,alpha_a):
    """Independent overdispersed goal margins; exact low-score convolution."""
    h0,h1,h2=nb_low_mass(h,alpha_h)
    a0,a1,a2=nb_low_mass(a,alpha_a)
    if alpha_h==alpha_a==0:
        return goal_probabilities(h,a)
    p0=h0*a0
    p1=h1*a0+h0*a1
    p2=h2*a0+h1*a1+h0*a2
    return tuple(min(1,max(0,p)) for p in (1-p0-p1,1-p0-p1-p2,(1-h0)*(1-a0)))

def negative_binomial_backtest(rows):
    """Fit dispersion on earlier league dates, then compare on matched samples."""
    by_day={}
    for r in verified_rows(rows):
        by_day.setdefault(r["date"],[]).append(r)
    history={}
    samples={k:[] for k in MARKETS}
    for day,group in sorted(by_day.items()):
        group=sorted(group,key=lambda r:(r["league"],r["home"],r["away"]))
        fitted={}
        for r in group:
            league=r["league"]
            past=history.get(league,[])
            n=len(past)
            if n<MIN_TRAIN_MATCHES:
                continue
            if league not in fitted:
                hs,aw=zip(*past)
                h=sum(hs)/n
                a=sum(aw)/n
                ah,aa=fit_nb_dispersion(hs,h),fit_nb_dispersion(aw,a)
                fitted[league]=(goal_probabilities(h,a),nb_probabilities(h,a,ah,aa),ah,aa)
            base,nb,ah,aa=fitted[league]
            for k,p,q,y in zip(MARKETS,base,nb,labels(*r["csv"])):
                samples[k].append((day,p,q,y,ah,aa))
        for r in group:
            history.setdefault(r["league"],[]).append(r["csv"])
    days=sorted({s[0] for s in samples[MARKETS[0]]})
    cutoff=days[int(len(days)*0.6)] if len(days)>=2 else None
    metrics={}
    for k,items in samples.items():
        test=[r for r in items if cutoff and r[0]>=cutoff]
        n=len(test)
        def score(i):
            if not n: return dict(brier=None,accuracyPct=None)
            return dict(brier=round(sum((r[i]-r[3])**2 for r in test)/n,6),
                accuracyPct=round(100*sum((r[i]>=0.5)==bool(r[3]) for r in test)/n,2))
        metrics[k]=dict(n=n,poisson=score(1),negativeBinomial=score(2),
            overdispersedMatches=sum(r[4]>0 or r[5]>0 for r in test),
            meanHomeDispersion=round(sum(r[4] for r in test)/n,6) if n else None,
            meanAwayDispersion=round(sum(r[5] for r in test)/n,6) if n else None)
    return dict(model="league_negative_binomial",holdoutStart=cutoff,markets=metrics,
        shrinkageMatches=NB_SHRINKAGE,sameDayTraining=False,productionModelValidated=False,externalValidation=False)

BOOTSTRAP_DRAWS=4096
BOOTSTRAP_MIN_DATES=8

def paired_date_bootstrap(by_day,draws=BOOTSTRAP_DRAWS,seed=20261128):
    """Resample whole dates; positive loss difference favors candidate.
    Descriptive percentile intervals, not independent confirmation.
    """
    if type(draws) is not int or not 1<=draws<=2**20:
        raise ValueError("invalid bootstrap draws")
    blocks=[(sum(v),len(v)) for _,v in sorted(by_day.items()) if v]
    n=sum(c for _,c in blocks)
    k=len(blocks)
    point=sum(s for s,_ in blocks)/n if n else None
    result=dict(matches=n,dateBlocks=k,meanImprovement=point,interval95=None,draws=draws)
    if k<BOOTSTRAP_MIN_DATES:
        return result
    rng=random.Random(seed)
    estimates=[]
    for _ in range(draws):
        chosen=rng.choices(blocks,k=k)
        estimates.append(sum(s for s,_ in chosen)/sum(c for _,c in chosen))
    estimates.sort()
    lo=estimates[int(0.025*(draws-1))]
    hi=estimates[math.ceil(0.975*(draws-1))]
    result["interval95"]=[lo,hi]
    return result

def bootstrap_model_comparison(rows,draws=BOOTSTRAP_DRAWS):
    """Paired date-cluster Brier differences on the common late-date sample."""
    by_day={}
    for r in verified_rows(rows):
        by_day.setdefault(r["date"],[]).append(r)
    history={}
    candidates=("dixonColes","bayesian","bivariate","negativeBinomial")
    samples={m:{c:{} for c in candidates} for m in MARKETS}
    for day,group in sorted(by_day.items()):
        group=sorted(group,key=lambda r:(r["league"],r["home"],r["away"]))
        fitted={}
        for r in group:
            league=r["league"]
            past=history.get(league,[])
            n=len(past)
            if n<MIN_TRAIN_MATCHES:
                continue
            if league not in fitted:
                hs,aw=zip(*past)
                h,a=sum(hs)/n,sum(aw)/n
                fitted[league]=(goal_probabilities(h,a),(
                    dc_probabilities(h,a,fit_dc_rho(past,h,a)),
                    gamma_poisson_probabilities(sum(hs),sum(aw),n),
                    bivariate_probabilities(h,a,fit_shared_intensity(past,h,a)),
                    nb_probabilities(h,a,fit_nb_dispersion(hs,h),fit_nb_dispersion(aw,a))))
            base,models=fitted[league]
            for i,(m,y) in enumerate(zip(MARKETS,labels(*r["csv"]))):
                for name,probs in zip(candidates,models):
                    samples[m][name].setdefault(day,[]).append((base[i]-y)**2-(probs[i]-y)**2)
        for r in group:
            history.setdefault(r["league"],[]).append(r["csv"])
    days=sorted(samples[MARKETS[0]][candidates[0]])
    cutoff=days[int(len(days)*0.6)] if len(days)>=2 else None
    metrics={m:{c:paired_date_bootstrap({d:v for d,v in values.items() if cutoff and d>=cutoff},draws)
                for c,values in models.items()} for m,models in samples.items()}
    return dict(mode="descriptive_paired_date_bootstrap",holdoutStart=cutoff,markets=metrics,
        minimumDateBlocks=BOOTSTRAP_MIN_DATES,reference="poisson",sameDayTraining=False,
        repeatedHoldout=True,adjustedForMultipleComparisons=False,crossDateDependenceAccountedFor=False,
        productionModelValidated=False,externalValidation=False)

MARKOV_MINUTES=90
MARKOV_SCORE_CAP=3

def markov_transition(mean):
    """One-minute Poisson increment, with an absorbing 3+ goal bucket."""
    p0=math.exp(-mean)
    p1=p0*mean
    p2=p1*mean/2
    mass=(p0,p1,p2)
    matrix=[]
    for start in range(MARKOV_SCORE_CAP+1):
        room=MARKOV_SCORE_CAP-start
        row=[0.0]*start+list(mass[:room])
        row.append(max(0,1-math.fsum(row)))
        matrix.append(row)
    return matrix

def markov_score_probabilities(h,a,elapsed=0,home_score=0,away_score=0):
    """Fixed-rate score-state propagation; not a fitted live-match model."""
    if not all(math.isfinite(x) and 0<=x<=20 for x in (h,a)):
        raise ValueError("invalid goal intensity")
    if type(elapsed) is not int or not 0<=elapsed<=MARKOV_MINUTES:
        raise ValueError("invalid elapsed minutes")
    if any(type(s) is not int or s<0 for s in (home_score,away_score)):
        raise ValueError("invalid score")
    ht,at=markov_transition(h/MARKOV_MINUTES),markov_transition(a/MARKOV_MINUTES)
    states=[[0.0]*4 for _ in range(4)]
    states[min(home_score,3)][min(away_score,3)]=1.0
    for _ in range(MARKOV_MINUTES-elapsed):
        nxt=[[0.0]*4 for _ in range(4)]
        for x in range(4):
            for y in range(4):
                if not states[x][y]:
                    continue
                for u in range(x,4):
                    for v in range(y,4):
                        nxt[u][v]+=states[x][y]*ht[x][u]*at[y][v]
        states=nxt
    total=math.fsum(p for row in states for p in row)
    probs=[0.0]*3
    for x in range(4):
        for y in range(4):
            for i,flag in enumerate(labels(x,y)):
                probs[i]+=states[x][y]*flag
    return dict(markets=dict(zip(MARKETS,(min(1,max(0,p/total)) for p in probs))),massError=abs(total-1))

def markov_numerical_audit(rows):
    """Full-time score data supports numerical checks, not live validation."""
    history={}
    for r in verified_rows(rows):
        history.setdefault(r["league"],[]).append(r["csv"])
    cases=[]
    for league,past in sorted(history.items()):
        n=len(past)
        if n<MIN_TRAIN_MATCHES:
            continue
        h=sum(x[0] for x in past)/n
        a=sum(x[1] for x in past)/n
        if max(h,a)>20:
            continue
        exact=goal_probabilities(h,a)
        start=markov_score_probabilities(h,a)
        error=max(abs(start["markets"][k]-p) for k,p in zip(MARKETS,exact))
        cases.append(dict(league=league,observedMatches=n,homeMean=h,awayMean=a,
            maxPrematchError=error,massError=start["massError"],
            illustrativeStates=[dict(elapsed=m,homeScore=x,awayScore=y,**markov_score_probabilities(h,a,m,x,y))
                for m,x,y in ((45,0,0),(60,1,0),(75,1,1),(90,2,1))]))
    return dict(mode="fixed_rate_markov_numerical_only",minutes=MARKOV_MINUTES,scoreCap=MARKOV_SCORE_CAP,
        cases=cases,maxPrematchError=max((c["maxPrematchError"] for c in cases),default=None),
        maxMassError=max((c["massError"] for c in cases),default=None),
        verifiedEventTimelines=0,stateDependentRatesFitted=False,liveValidation=False,
        stoppageTimeModeled=False,productionModelValidated=False)

ELO_INITIAL=1500.0
ELO_K=20.0
ELO_HOME_ADVANTAGE=60.0
ELO_SCALES=(0.0,0.25,0.5,1.0)

def elo_expected(home,away,advantage=ELO_HOME_ADVANTAGE):
    """Expected result points, not the probability of an outright win."""
    return 1/(1+10**(-max(-3000,min(3000,home-away+advantage))/400))

def elo_delta(home,away,hg,ag):
    actual=1.0 if hg>ag else 0.0 if hg<ag else 0.5
    return ELO_K*(actual-elo_expected(home,away))

def elo_goal_means(h,a,home_rating,away_rating,scale):
    """Redistribute league goal total by relative strength; venue already in means."""
    if not all(math.isfinite(v) for v in (h,a,home_rating,away_rating,scale)) or min(h,a,scale)<0:
        raise ValueError("invalid Elo goal inputs")
    if not h or not a or not scale or home_rating==away_rating:
        return h,a
    multiplier=10**max(-6,min(6,scale*(home_rating-away_rating)/400))
    total=h+a
    home=total*(h*multiplier)/(h*multiplier+a)
    return home,total-home

def elo_backtest(rows):
    """Fit strength using past dates only; select goal-share scale before holdout."""
    by_day={}
    for r in verified_rows(rows):
        by_day.setdefault(r["date"],[]).append(r)
    history={}
    ratings={}
    games=Counter()
    samples=[]
    for day,group in sorted(by_day.items()):
        group=sorted(group,key=lambda r:(r["league"],r["home"],r["away"]))
        changes=Counter()
        for r in group:
            l=r["league"]
            hk,ak=(l,r["home"]),(l,r["away"])
            rh,ra=ratings.get(hk,ELO_INITIAL),ratings.get(ak,ELO_INITIAL)
            x,y=r["csv"]
            d=elo_delta(rh,ra,x,y)
            changes[hk]+=d
            changes[ak]-=d
            hs,as_,n=history.get(l,(0,0,0))
            if n<MIN_TRAIN_MATCHES:
                continue
            h,a=hs/n,as_/n
            probs=[goal_probabilities(*elo_goal_means(h,a,rh,ra,s)) for s in ELO_SCALES]
            samples.append((day,probs,labels(x,y),min(games[hk],games[ak])))
        for team,d in changes.items():
            ratings[team]=ratings.get(team,ELO_INITIAL)+d
        for r in group:
            l=r["league"]
            games[(l,r["home"])]+=1
            games[(l,r["away"])]+=1
            h,a,n=history.get(l,(0,0,0))
            x,y=r["csv"]
            history[l]=(h+x,a+y,n+1)
    days=sorted({r[0] for r in samples})
    cutoff=days[int(len(days)*0.6)] if len(days)>=2 else None
    tune=[r for r in samples if cutoff and r[0]<cutoff]
    test=[r for r in samples if cutoff and r[0]>=cutoff]
    def loss(items,j):
        return sum((r[1][j][2]-r[2][2])**2 for r in items)/len(items)
    selected=min(range(len(ELO_SCALES)),key=lambda j:loss(tune,j)) if len(tune)>=MIN_VALIDATION_MATCHES else 0
    metrics={}
    for i,k in enumerate(MARKETS):
        def score(j):
            if not test:
                return dict(brier=None,accuracyPct=None)
            return dict(brier=round(sum((r[1][j][i]-r[2][i])**2 for r in test)/len(test),6),
                accuracyPct=round(100*sum((r[1][j][i]>=0.5)==bool(r[2][i]) for r in test)/len(test),2))
        metrics[k]=dict(n=len(test),poisson=score(0),elo=score(selected))
    return dict(model="elo_goal_share",holdoutStart=cutoff,tuneMatches=len(tune),holdoutMatches=len(test),
        ratingCount=len(ratings),initialRating=ELO_INITIAL,kFactor=ELO_K,homeAdvantage=ELO_HOME_ADVANTAGE,
        candidateScales=list(ELO_SCALES),selectedScale=ELO_SCALES[selected],selectionMarket="btts",
        bothTeamsFivePriorMatches=sum(r[3]>=5 for r in test),markets=metrics,
        preservesExpectedTotal=True,sameDayTraining=False,repeatedHoldout=True,
        productionModelValidated=False,externalValidation=False)

GLICKO_SCALE=173.7178
GLICKO_INITIAL=(1500.0,350.0,0.06)
GLICKO_TAU=0.5

def glicko_g(phi):
    return 1/math.sqrt(1+3*phi*phi/math.pi**2)

def glicko_inactive(state,periods):
    rating,rd,sigma=state
    return rating,min(350.0,GLICKO_SCALE*math.hypot(rd/GLICKO_SCALE,sigma*math.sqrt(periods))),sigma

def glicko_update(state,opponents):
    """Glicko-2 rating-period update; offsets are rating-point venue adjustments."""
    rating,rd,sigma=state
    if not opponents:
        return glicko_inactive(state,1)
    mu=(rating-1500)/GLICKO_SCALE
    phi=rd/GLICKO_SCALE
    terms=[]
    for other,other_rd,score,offset in opponents:
        g=glicko_g(other_rd/GLICKO_SCALE)
        z=g*(mu-(other-1500)/GLICKO_SCALE+offset/GLICKO_SCALE)
        e=1/(1+math.exp(-max(-30,min(30,z))))
        terms.append((g,e,score))
    v=1/sum(g*g*e*(1-e) for g,e,s in terms)
    residual=sum(g*(s-e) for g,e,s in terms)
    delta=v*residual
    alpha=math.log(sigma*sigma)
    def f(x):
        ex=math.exp(x)
        return ex*(delta*delta-phi*phi-v-ex)/(2*(phi*phi+v+ex)**2)-(x-alpha)/GLICKO_TAU**2
    lo=alpha
    if delta*delta>phi*phi+v:
        hi=math.log(delta*delta-phi*phi-v)
    else:
        k=1
        while f(alpha-k*GLICKO_TAU)<0 and k<100:
            k+=1
        hi=alpha-k*GLICKO_TAU
    # Bracketed bisection is deterministic and avoids unstable secant steps.
    lo,hi=sorted((lo,hi))
    flo=f(lo)
    for _ in range(100):
        mid=(lo+hi)/2
        fm=f(mid)
        if abs(hi-lo)<1e-10:
            break
        if flo*fm<=0:
            hi=mid
        else:
            lo=mid
            flo=fm
    new_sigma=math.exp((lo+hi)/4)
    phi_star=math.hypot(phi,new_sigma)
    new_phi=1/math.sqrt(1/(phi_star*phi_star)+1/v)
    new_mu=mu+new_phi*new_phi*residual
    return 1500+GLICKO_SCALE*new_mu,min(350.0,GLICKO_SCALE*new_phi),new_sigma

def glicko_goal_means(h,a,home,away,scale):
    """Attenuate goal-share strength by joint rating uncertainty."""
    attenuation=glicko_g(math.hypot(home[1],away[1])/GLICKO_SCALE)
    return elo_goal_means(h,a,home[0],away[0],scale*attenuation)

def glicko_backtest(rows):
    """Daily rating periods, league-scoped states, frozen earlier-date scale."""
    by_day={}
    for r in verified_rows(rows):
        by_day.setdefault(r["date"],[]).append(r)
    ratings={}
    last={}
    history={}
    samples=[]
    for day,group in sorted(by_day.items()):
        group=sorted(group,key=lambda r:(r["league"],r["home"],r["away"]))
        current=datetime.fromisoformat(day).date()
        prior={}
        updates={}
        def state(key):
            if key not in prior:
                prior[key]=glicko_inactive(ratings.get(key,GLICKO_INITIAL),max(0,(current-last.get(key,current)).days-1))
            return prior[key]
        for r in group:
            l=r["league"]
            hk,ak=(l,r["home"]),(l,r["away"])
            home,away=state(hk),state(ak)
            x,y=r["csv"]
            score=1.0 if x>y else 0.0 if x<y else 0.5
            updates.setdefault(hk,[]).append((away[0],away[1],score,ELO_HOME_ADVANTAGE))
            updates.setdefault(ak,[]).append((home[0],home[1],1-score,-ELO_HOME_ADVANTAGE))
            hs,as_,n=history.get(l,(0,0,0))
            if n>=MIN_TRAIN_MATCHES:
                probs=[goal_probabilities(*glicko_goal_means(hs/n,as_/n,home,away,s)) for s in ELO_SCALES]
                samples.append((day,probs,labels(x,y),(home[1]+away[1])/2))
        for key,opponents in updates.items():
            ratings[key]=glicko_update(prior[key],opponents)
            last[key]=current
        for r in group:
            l=r["league"]
            h,a,n=history.get(l,(0,0,0))
            x,y=r["csv"]
            history[l]=(h+x,a+y,n+1)
    days=sorted({r[0] for r in samples})
    cutoff=days[int(len(days)*0.6)] if len(days)>=2 else None
    tune=[r for r in samples if cutoff and r[0]<cutoff]
    test=[r for r in samples if cutoff and r[0]>=cutoff]
    selected=min(range(len(ELO_SCALES)),key=lambda j:sum((r[1][j][2]-r[2][2])**2 for r in tune)) if len(tune)>=MIN_VALIDATION_MATCHES else 0
    metrics={}
    for i,k in enumerate(MARKETS):
        def score(j):
            if not test:
                return dict(brier=None,accuracyPct=None)
            return dict(brier=round(sum((r[1][j][i]-r[2][i])**2 for r in test)/len(test),6),
                accuracyPct=round(100*sum((r[1][j][i]>=0.5)==bool(r[2][i]) for r in test)/len(test),2))
        metrics[k]=dict(n=len(test),poisson=score(0),glicko2=score(selected))
    return dict(model="glicko2_uncertainty_goal_share",holdoutStart=cutoff,tuneMatches=len(tune),holdoutMatches=len(test),
        ratingCount=len(ratings),initialRating=GLICKO_INITIAL[0],initialRD=GLICKO_INITIAL[1],initialVolatility=GLICKO_INITIAL[2],
        tau=GLICKO_TAU,ratingPeriod="day",candidateScales=list(ELO_SCALES),selectedScale=ELO_SCALES[selected],
        meanHoldoutRD=round(sum(r[3] for r in test)/len(test),3) if test else None,selectionMarket="btts",markets=metrics,
        preservesExpectedTotal=True,sameDayTraining=False,repeatedHoldout=True,
        productionModelValidated=False,externalValidation=False)

ENSEMBLE_MODELS=("poisson","dixonColes","bayesian","bivariate","negativeBinomial","teamForm","elo","glicko2")
ENSEMBLE_STEPS=10

def ensemble_samples(rows):
    """Common past-only forecasts for all candidates, including rating histories."""
    by_day={}
    for r in verified_rows(rows):
        by_day.setdefault(r["date"],[]).append(r)
    history={}
    elo={}
    glicko={}
    last={}
    samples=[]
    for day,group in sorted(by_day.items()):
        current=datetime.fromisoformat(day).date()
        group=sorted(group,key=lambda r:(r["league"],r["home"],r["away"]))
        changes=Counter()
        prior={}
        updates={}
        fitted={}
        def state(key):
            if key not in prior:
                prior[key]=glicko_inactive(glicko.get(key,GLICKO_INITIAL),max(0,(current-last.get(key,current)).days-1))
            return prior[key]
        for r in group:
            l=r["league"]
            hk,ak=(l,r["home"]),(l,r["away"])
            rh,ra=elo.get(hk,ELO_INITIAL),elo.get(ak,ELO_INITIAL)
            gh,ga=state(hk),state(ak)
            x,y=r["csv"]
            d=elo_delta(rh,ra,x,y)
            changes[hk]+=d
            changes[ak]-=d
            score=1.0 if x>y else 0.0 if x<y else 0.5
            updates.setdefault(hk,[]).append((ga[0],ga[1],score,ELO_HOME_ADVANTAGE))
            updates.setdefault(ak,[]).append((gh[0],gh[1],1-score,-ELO_HOME_ADVANTAGE))
            past=history.get(l,[])
            n=len(past)
            if n<MIN_TRAIN_MATCHES:
                continue
            if l not in fitted:
                scores=[v["csv"] for v in past]
                hs,aw=zip(*scores)
                h,a=sum(hs)/n,sum(aw)/n
                fitted[l]=(h,a,(
                    goal_probabilities(h,a),
                    dc_probabilities(h,a,fit_dc_rho(scores,h,a)),
                    gamma_poisson_probabilities(sum(hs),sum(aw),n),
                    bivariate_probabilities(h,a,fit_shared_intensity(scores,h,a)),
                    nb_probabilities(h,a,fit_nb_dispersion(hs,h),fit_nb_dispersion(aw,a))))
            h,a,base=fitted[l]
            models=base+(goal_probabilities(*team_goal_means(past,r["home"],r["away"])),
                goal_probabilities(*elo_goal_means(h,a,rh,ra,0.5)),
                goal_probabilities(*glicko_goal_means(h,a,gh,ga,0.5)))
            samples.append((day,tuple(tuple(min(1,max(0,p)) for p in model) for model in models),labels(x,y)))
        for key,d in changes.items():
            elo[key]=elo.get(key,ELO_INITIAL)+d
        for key,opponents in updates.items():
            glicko[key]=glicko_update(prior[key],opponents)
            last[key]=current
        for r in group:
            history.setdefault(r["league"],[]).append(r)
    return samples

def ensemble_prediction(models,weights):
    return tuple(sum(w*p[i] for w,p in zip(weights,models)) for i in range(len(MARKETS)))

def fit_ensemble_weights(tune):
    """Simplex coordinate search on tuning dates; one weight vector for all markets."""
    m=len(ENSEMBLE_MODELS)
    units=[ENSEMBLE_STEPS]+[0]*(m-1)
    if len(tune)<MIN_VALIDATION_MATCHES:
        return tuple(v/ENSEMBLE_STEPS for v in units)
    def loss(u):
        w=[v/ENSEMBLE_STEPS for v in u]
        return sum((p-y)**2 for _,models,ys in tune for p,y in zip(ensemble_prediction(models,w),ys))/len(tune)/len(MARKETS)
    best=loss(units)
    for _ in range(30):
        chosen=None
        for i in range(m):
            if not units[i]:
                continue
            for j in range(m):
                if j==i:
                    continue
                trial=units.copy()
                trial[i]-=1
                trial[j]+=1
                value=loss(trial)
                if value<best-1e-12:
                    chosen,best=trial,value
        if chosen is None:
            break
        units=chosen
    return tuple(v/ENSEMBLE_STEPS for v in units)

def ensemble_backtest(rows):
    samples=ensemble_samples(rows)
    days=sorted({r[0] for r in samples})
    cutoff=days[int(len(days)*0.6)] if len(days)>=2 else None
    tune=[r for r in samples if cutoff and r[0]<cutoff]
    test=[r for r in samples if cutoff and r[0]>=cutoff]
    weights=fit_ensemble_weights(tune)
    metrics={}
    for i,k in enumerate(MARKETS):
        def score(values):
            if not values:
                return dict(brier=None,logLoss=None,accuracyPct=None)
            n=len(values)
            return dict(brier=round(sum((p-y)**2 for p,y in values)/n,6),
                logLoss=round(-sum(y*math.log(max(1e-12,p))+(1-y)*math.log(max(1e-12,1-p)) for p,y in values)/n,6),
                accuracyPct=round(100*sum((p>=0.5)==bool(y) for p,y in values)/n,2))
        metrics[k]=dict(n=len(test),poisson=score([(models[0][i],ys[i]) for _,models,ys in test]),
            ensemble=score([(ensemble_prediction(models,weights)[i],ys[i]) for _,models,ys in test]),
            candidates={name:score([(models[j][i],ys[i]) for _,models,ys in test]) for j,name in enumerate(ENSEMBLE_MODELS)})
    return dict(model="convex_weighted_ensemble",holdoutStart=cutoff,tuneMatches=len(tune),holdoutMatches=len(test),
        weights=dict(zip(ENSEMBLE_MODELS,weights)),weightGrid=1/ENSEMBLE_STEPS,sharedAcrossMarkets=True,
        ratingCandidateScale=0.5,selectionMetric="mean_brier",sameDayTraining=False,repeatedHoldout=True,
        productionModelValidated=False,externalValidation=False,markets=metrics)

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
    hybrid=hybrid_holdout([dict(r,league=g["league"]) for g in leagues for r in g["rows"]])
    dc=dixon_coles_backtest([dict(r,league=g["league"]) for g in leagues for r in g["rows"]])
    simulation=simulation_audit([dict(r,league=g["league"]) for g in leagues for r in g["rows"]])
    bayes=bayesian_backtest([dict(r,league=g["league"]) for g in leagues for r in g["rows"]])
    bivariate=bivariate_backtest([dict(r,league=g["league"]) for g in leagues for r in g["rows"]])
    nb=negative_binomial_backtest([dict(r,league=g["league"]) for g in leagues for r in g["rows"]])
    bootstrap=bootstrap_model_comparison([dict(r,league=g["league"]) for g in leagues for r in g["rows"]])
    markov=markov_numerical_audit([dict(r,league=g["league"]) for g in leagues for r in g["rows"]])
    elo=elo_backtest([dict(r,league=g["league"]) for g in leagues for r in g["rows"]])
    glicko=glicko_backtest([dict(r,league=g["league"]) for g in leagues for r in g["rows"]])
    ensemble=ensemble_backtest([dict(r,league=g["league"]) for g in leagues for r in g["rows"]])
    return dict(version="6.42",ensembleBacktest=ensemble,glickoBacktest=glicko,eloBacktest=elo,markovAudit=markov,bootstrapComparison=bootstrap,negativeBinomialBacktest=nb,bivariateBacktest=bivariate,bayesianBacktest=bayes,simulationAudit=simulation,dixonColesBacktest=dc,hybridHoldout=hybrid,teamFormBacktest=team_replay,chronologicalBacktest=replay,outcomeBaseline=baseline,historyWindowDays=HISTORY_WINDOW_DAYS,sampleDateLimit=SAMPLE_DATE_LIMIT,mode="source_audit_only",updatedAt=now.isoformat(),leagues=leagues,
        configured=len(COMPETITIONS),responding=sum(bool(g["days"]) and not g["errors"] for g in leagues),
        corroborated=sum(g["counts"].get("corroborated",0) for g in leagues),
        archivesModified=False,predictionsEnabled=False,realBettingEnabled=False,decision="PAS")

if __name__=="__main__":
    report=build(datetime.now(TR))
    Path("extra_league_score_audit.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    for g in report["leagues"]:
        print("LEAGUE_AUDIT",json.dumps({k:g[k] for k in ("league","days","counts","errors")},ensure_ascii=False))
        print("NAME_EVIDENCE",json.dumps({"league":g["league"],"names":g["unmatchedNames"],"rows":[r for r in g["rows"] if r["status"] in ("csv_only","espn_only")]},ensure_ascii=False))
    print("ENSEMBLE_BACKTEST",json.dumps(report["ensembleBacktest"]))
    print("GLICKO_BACKTEST",json.dumps(report["glickoBacktest"]))
    print("ELO_BACKTEST",json.dumps(report["eloBacktest"]))
    print("MARKOV_AUDIT",json.dumps({k:v for k,v in report["markovAudit"].items() if k!="cases"}))
    print("BOOTSTRAP_COMPARISON",json.dumps(report["bootstrapComparison"]))
    print("NEGATIVE_BINOMIAL_BACKTEST",json.dumps(report["negativeBinomialBacktest"]))
    print("BIVARIATE_BACKTEST",json.dumps(report["bivariateBacktest"]))
    print("BAYESIAN_BACKTEST",json.dumps(report["bayesianBacktest"]))
    print("SIMULATION_AUDIT",json.dumps({k:report["simulationAudit"][k] for k in ("mode","drawsPerCasePerMethod","summary")}))
    print("DIXON_COLES_BACKTEST",json.dumps(report["dixonColesBacktest"]))
    print("HYBRID_HOLDOUT",json.dumps(report["hybridHoldout"]))
    print("TEAM_FORM_BACKTEST",json.dumps(report["teamFormBacktest"]))
    print("CHRONOLOGICAL_BACKTEST",json.dumps(report["chronologicalBacktest"]))
    print("OUTCOME_BASELINE",json.dumps(report["outcomeBaseline"]))
    print("AUDIT_TOTAL",json.dumps({k:report[k] for k in ("configured","responding","corroborated","archivesModified")}))
