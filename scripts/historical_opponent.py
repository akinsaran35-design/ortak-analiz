"""Past-only opponent-adjusted venue model and paired research backtest."""
from collections import defaultdict
from datetime import date, timedelta
from itertools import groupby
from historical_split import split
from historical_baseline import market_metrics
from historical_strength import rates as venue_rates
from dixon_coles import markets

def clip(x, low=.15, high=4.0):
    return max(low, min(high, x))

class Strength:
    """Store observed goals relative to pre-match opponent and league exposure."""
    def __init__(self):
        self.history = defaultdict(list)
        self.totals = defaultdict(lambda: [0, 0, 0])

    def means(self, league):
        h, a, n = self.totals[league]
        return (h+15)/(n+10), (a+12)/(n+10)

    def factors(self, league, team, venue):
        rows = self.history[(league, team)]
        def ratio(g, e):
            return clip((5+g)/(5+e), .25, 4)
        recent = [r for r in rows[-30:] if r[0] == venue]
        return (ratio(sum(r[1] for r in recent), sum(r[3] for r in recent)),
                ratio(sum(r[2] for r in recent), sum(r[4] for r in recent)))

    def expected(self, row):
        l, h, a = row["league"], row["home"], row["away"]
        mh, ma = self.means(l)
        ha, hd = self.factors(l, h, "home")
        aa, ad = self.factors(l, a, "away")
        return (clip(mh*ha*ad), clip(ma*aa*hd))

    def exposure(self, row):
        l, h, a = row["league"], row["home"], row["away"]
        mh, ma = self.means(l)
        ha, hd = self.factors(l, h, "home")
        aa, ad = self.factors(l, a, "away")
        return mh*ad, ma*aa, ma*hd, mh*ha

    def update(self, row, exposure):
        l, h, a = row["league"], row["home"], row["away"]
        x, y = row["ft"]
        eh, dh, ea, da = exposure
        self.history[(l,h)].append(("home",x,y,eh,dh))
        self.history[(l,a)].append(("away",y,x,ea,da))
        totals = self.totals[l]
        totals[0] += x
        totals[1] += y
        totals[2] += 1

def compare(rows, as_of, phase="test"):
    if phase not in ("validation","test"):
        raise ValueError("invalid evaluation phase")
    groups, meta = split(rows, as_of)
    model = Strength()
    history = defaultdict(list)
    scores = defaultdict(lambda: [[], [], [], []])
    league_scores = defaultdict(lambda: defaultdict(lambda: [[], [], [], []]))
    skipped = 0
    for day, batch in groupby(sorted(sum(groups.values(), []), key=lambda r: (r["date"],str(r["matchID"]))), key=lambda r:r["date"]):
        batch = list(batch)
        pending = [(r, model.exposure(r)) for r in batch]
        for r, _ in pending:
            l, h, a = r["league"], r["home"], r["away"]
            hh, ah = history[(l,h)], history[(l,a)]
            if day < meta["validationStart" if phase=="validation" else "testStart"]:
                continue
            if phase=="validation" and day>=meta["testStart"]:
                continue
            if min(len(hh), len(ah)) < 5:
                skipped += 1
                continue
            h10, a10 = hh[-10:], ah[-10:]
            avg = lambda z,i: sum(t[i] for t in z)/len(z)
            base = (clip((avg(h10,0)+avg(a10,1))/2), clip((avg(a10,0)+avg(h10,1))/2))
            venue = venue_rates(hh, ah, *model.means(l))
            if venue is None:
                venue = base
            forecasts = [markets(*p) for p in (base, venue, model.expected(r), tuple(clip(x) for x in model.means(l)))]
            x,y = r["ft"]
            for k,o in (("over15",x+y>=2),("over25",x+y>=3),("btts",x>0 and y>0)):
                for i,p in enumerate(forecasts):
                    value = (p[k],int(o))
                    scores[k][i].append(value)
                    league_scores[l][k][i].append(value)
        # Freeze every exposure before recording any same-day result.
        for r, e in pending:
            model.update(r,e)
            l,h,a = r["league"],r["home"],r["away"]
            x,y = r["ft"]
            history[(l,h)].append((x,y,"home"))
            history[(l,a)].append((y,x,"away"))
    def summarize(values):
        return {k:{name:market_metrics(v) for name,v in zip(("baseline","venue","opponent","leagueReference"),series)} for k,series in values.items()}
    return dict(skipped=skipped, metrics=summarize(scores), leagueMetrics={l:summarize(v) for l,v in sorted(league_scores.items())})

def multiyear(rows, today):
    windows = []
    for offset in range(0,1096,61):
        end = today-timedelta(days=offset)
        test=compare(rows,end)
        validation=compare(rows,end,phase="validation")
        selection={}
        for k, models in test["metrics"].items():
            prior=validation["metrics"].get(k,{})
            candidates={name:m for name,m in prior.items() if m["n"]>=100}
            chosen=min(candidates,key=lambda name:(candidates[name]["brier"],name)) if candidates else "leagueReference"
            selection[k]=dict(model=chosen,validationN=prior.get(chosen,{}).get("n",0),test=models[chosen])
        windows.append(dict(asOf=end.isoformat(), validationSelection=selection, **test))
    aggregate = {}
    for k in ("over15","over25","btts"):
        aggregate[k] = {}
        for name in ("baseline","venue","opponent","leagueReference"):
            ms = [w["metrics"][k][name] for w in windows if k in w["metrics"]]
            n = sum(m["n"] for m in ms)
            s = sum(m["selected"] for m in ms)
            h = sum(m["hits"] for m in ms)
            aggregate[k][name] = dict(n=n,selected=s,hits=h,hitRate=h/s if s else None,brier=sum(m["n"]*m["brier"] for m in ms)/n if n else None)
        a = aggregate[k]
        a["referenceImprovement"] = a["leagueReference"]["brier"]-a["opponent"]["brier"] if a["leagueReference"]["n"] else None
        a["brierImprovement"] = a["baseline"]["brier"]-a["opponent"]["brier"] if a["baseline"]["n"] else None
    league_aggregate = {}
    leagues = sorted({l for w in windows for l in w["leagueMetrics"]})
    for league in leagues:
        league_aggregate[league] = {}
        for k in ("over15","over25","btts"):
            reports = [w["leagueMetrics"][league][k] for w in windows if k in w["leagueMetrics"].get(league,{})]
            models = {}
            for name in ("baseline","venue","opponent","leagueReference"):
                ms = [v[name] for v in reports]
                n = sum(m["n"] for m in ms)
                s = sum(m["selected"] for m in ms)
                h = sum(m["hits"] for m in ms)
                models[name] = dict(n=n,selected=s,hits=h,hitRate=h/s if s else None,brier=sum(m["n"]*m["brier"] for m in ms)/n if n else None)
            n = models["opponent"]["n"]
            league_aggregate[league][k] = dict(models=models,windows=len(reports),sampleAdequateForDescription=n>=100 and len(reports)>=3,referenceImprovement=models["leagueReference"]["brier"]-models["opponent"]["brier"] if n else None)
    selected_aggregate={}
    for k in ("over15","over25","btts"):
        chosen=[w["validationSelection"][k] for w in windows if k in w["validationSelection"]]
        ms=[x["test"] for x in chosen]
        n=sum(m["n"] for m in ms)
        s=sum(m["selected"] for m in ms)
        h=sum(m["hits"] for m in ms)
        selected_aggregate[k]=dict(n=n,selected=s,hits=h,hitRate=h/s if s else None,brier=sum(m["n"]*m["brier"] for m in ms)/n if n else None,modelWindowCounts={name:sum(x["model"]==name for x in chosen) for name in ("baseline","venue","opponent","leagueReference")})
    return dict(status="research_only",realBettingEnabled=False,independentHoldout=False,matchCount=len(rows),aggregate=aggregate,validationSelectedAggregate=selected_aggregate,validationSelectionRule=dict(minMatches=100,fallback="leagueReference",metric="brier",descriptiveOnly=True),leagueAggregate=league_aggregate,leagueSampleRule=dict(minMatches=100,minWindows=3,descriptiveOnly=True),windows=windows)

if __name__ == "__main__":
    import json
    from pathlib import Path
    archive = json.loads(Path("openliga_archive.json").read_text())
    result = multiyear(archive["matches"],date.fromisoformat(archive["asOf"]))
    Path("opponent_strength_report.json").write_text(json.dumps(result,indent=2))
    print(json.dumps(result["aggregate"]))
    print("Validation-only selection:",json.dumps(result["validationSelectedAggregate"]))
