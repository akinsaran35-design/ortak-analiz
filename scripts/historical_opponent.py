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

def compare(rows, as_of):
    groups, meta = split(rows, as_of)
    model = Strength()
    history = defaultdict(list)
    scores = defaultdict(lambda: [[], [], []])
    skipped = 0
    for day, batch in groupby(sorted(sum(groups.values(), []), key=lambda r: (r["date"],str(r["matchID"]))), key=lambda r:r["date"]):
        batch = list(batch)
        pending = [(r, model.exposure(r)) for r in batch]
        for r, _ in pending:
            l, h, a = r["league"], r["home"], r["away"]
            hh, ah = history[(l,h)], history[(l,a)]
            if day < meta["testStart"]:
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
            forecasts = [markets(*p) for p in (base, venue, model.expected(r))]
            x,y = r["ft"]
            for k,o in (("over15",x+y>=2),("over25",x+y>=3),("btts",x>0 and y>0)):
                for series,p in zip(scores[k],forecasts):
                    series.append((p[k],int(o)))
        # Freeze every exposure before recording any same-day result.
        for r, e in pending:
            model.update(r,e)
            l,h,a = r["league"],r["home"],r["away"]
            x,y = r["ft"]
            history[(l,h)].append((x,y,"home"))
            history[(l,a)].append((y,x,"away"))
    return dict(skipped=skipped, metrics={k:{name:market_metrics(v) for name,v in zip(("baseline","venue","opponent"),series)} for k,series in scores.items()})

def multiyear(rows, today):
    windows = []
    for offset in range(0,1096,61):
        end = today-timedelta(days=offset)
        windows.append(dict(asOf=end.isoformat(), **compare(rows,end)))
    aggregate = {}
    for k in ("over15","over25","btts"):
        aggregate[k] = {}
        for name in ("baseline","venue","opponent"):
            ms = [w["metrics"][k][name] for w in windows if k in w["metrics"]]
            n = sum(m["n"] for m in ms)
            s = sum(m["selected"] for m in ms)
            h = sum(m["hits"] for m in ms)
            aggregate[k][name] = dict(n=n,selected=s,hits=h,hitRate=h/s if s else None,brier=sum(m["n"]*m["brier"] for m in ms)/n if n else None)
        a = aggregate[k]
        a["brierImprovement"] = a["baseline"]["brier"]-a["opponent"]["brier"] if a["baseline"]["n"] else None
    return dict(status="research_only",realBettingEnabled=False,independentHoldout=False,matchCount=len(rows),aggregate=aggregate,windows=windows)

if __name__ == "__main__":
    import json
    from pathlib import Path
    archive = json.loads(Path("openliga_archive.json").read_text())
    result = multiyear(archive["matches"],date.fromisoformat(archive["asOf"]))
    Path("opponent_strength_report.json").write_text(json.dumps(result,indent=2))
    print(json.dumps(result["aggregate"]))
