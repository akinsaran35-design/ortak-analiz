# Ortak Analiz V2.0 - Historical model backtest
import json
import math
import urllib.request
from datetime import date, timedelta
from pathlib import Path

BASE = "https://raw.githubusercontent.com/openfootball/football.json/master"
LEAGUES = ["en.1", "en.2", "de.1", "es.1", "it.1", "fr.1"]
MARKETS = ["1.5 Üst", "2.5 Üst", "KG Var"]

today = date.today()
year = today.year if today.month >= 7 else today.year - 1
seasons = [f"{y}-{str(y+1)[-2:]}" for y in (year-1, year)]

def fetch(season, league):
    url = f"{BASE}/{season}/{league}.json"
    req = urllib.request.Request(
        url, headers={"User-Agent": "OrtakAnaliz/2.0"}
    )
    with urllib.request.urlopen(req, timeout=20) as response:
        data = json.load(response)
    return data.get("matches", [])

def team(value):
    if isinstance(value, dict):
        return str(value.get("name") or value.get("code") or "").strip()
    return str(value or "").strip()

def stats(history, name, home):
    selected = []
    general = []
    for d, h, a, hg, ag in history:
        if h == name:
            general.append((d, hg, ag))
            if home:
                selected.append((d, hg, ag))
        elif a == name:
            general.append((d, ag, hg))
            if not home:
                selected.append((d, ag, hg))
    if len(selected) < 5:
        selected = general
    selected = sorted(selected, reverse=True)[:10]
    if len(selected) < 5:
        return None
    n = len(selected)
    return (
        sum(x[1] for x in selected) / n,
        sum(x[2] for x in selected) / n
    )

def over(lam, k):
    return 1 - sum(
        math.exp(-lam) * lam**i / math.factorial(i)
        for i in range(k+1)
    )

def predict(history, home, away):
    hs = stats(history, home, True)
    aws = stats(history, away, False)
    if hs is None or aws is None:
        return None
    h = max(0.15, min(4, (hs[0]+aws[1])/2))
    a = max(0.15, min(4, (aws[0]+hs[1])/2))
    return [
        over(h+a, 1),
        over(h+a, 2),
        (1-math.exp(-h))*(1-math.exp(-a))
    ]

# V4.0: experimental league-normalized Poisson and Dixon-Coles.
def dc_rates(past, home, away):
    recent = past[-380:]
    if len(recent) < 50:
        return None
    lh = max(0.2, sum(x[3] for x in recent)/len(recent))
    la = max(0.2, sum(x[4] for x in recent)/len(recent))
    hh = [x for x in recent if x[1] == home][-15:]
    aa = [x for x in recent if x[2] == away][-15:]
    def ratio(rows, idx, mean):
        return (sum(x[idx] for x in rows)+5*mean)/((len(rows)+5)*mean)
    h = lh*ratio(hh,3,lh)*ratio(aa,3,lh)
    a = la*ratio(aa,4,la)*ratio(hh,4,la)
    return max(.15,min(4,h)), max(.15,min(4,a))

def tau(h,a,x,y,rho):
    if (x,y)==(0,0): return 1-h*a*rho
    if (x,y)==(0,1): return 1+h*rho
    if (x,y)==(1,0): return 1+a*rho
    if (x,y)==(1,1): return 1-rho
    return 1.0

def fit_rho(records):
    if len(records)<50: return 0.0
    grid = [i/100 for i in range(-15,7)]
    return max(grid,key=lambda r: sum(math.log(tau(h,a,x,y,r)) for _,h,a,x,y in records)-10*r*r)

def dc_probs(h,a,rho):
    delta = math.exp(-h-a)*h*a*rho
    return [over(h+a,1)-delta,over(h+a,2),
            (1-math.exp(-h))*(1-math.exp(-a))-delta]

experimental = {m: [] for m in MARKETS}

results = {m: [] for m in MARKETS}
diagnostics = []

for league in LEAGUES:
    matches = {}
    errors = []
    for season in seasons:
        try:
            for m in fetch(season, league):
                try:
                    d = date.fromisoformat(m["date"][:10])
                    h = team(m.get("team1"))
                    a = team(m.get("team2"))
                    ft = m.get("score", {}).get("ft")
                    if (
                        d < today and h and a
                        and isinstance(ft, list)
                        and len(ft) == 2
                        and all(type(x) is int and x >= 0 for x in ft)
                    ):
                        matches[(d, h, a)] = tuple(ft)
                except (ValueError, TypeError, KeyError, AttributeError):
                    continue
        except Exception as exc:
            errors.append(f"{season}: {exc}")

    history = sorted(
        (d, h, a, s[0], s[1])
        for (d, h, a), s in matches.items()
    )
    tested = 0
    dc_history = []
    for d, h, a, hg, ag in history:
        if d < today - timedelta(days=365):
            continue
        past = [x for x in history if x[0] < d]
        probabilities = predict(past, h, a)
        if probabilities is None:
            continue
        actual = [
            int(hg+ag >= 2),
            int(hg+ag >= 3),
            int(hg > 0 and ag > 0)
        ]
        for market, p, y in zip(MARKETS, probabilities, actual):
            results[market].append((d, p, y))
        rates = dc_rates(past,h,a)
        if rates is not None:
            rh,ra = rates
            rho = fit_rho([x for x in dc_history if x[0]<d])
            independent = dc_probs(rh,ra,0)
            corrected = dc_probs(rh,ra,rho)
            for market,p,q,c,y in zip(MARKETS,probabilities,independent,corrected,actual):
                experimental[market].append((d,p,q,c,y))
            dc_history.append((d,rh,ra,hg,ag))
        tested += 1

    diagnostics.append({
        "league": league,
        "completed": len(history),
        "tested": tested,
        "errors": errors
    })

report = {
    "version": "2.1",
    "date": today.isoformat(),
    "modelCalibrated": False,
    "markets": {},
    "diagnostics": diagnostics
}

for market, dated_rows in results.items():
    rows = [(p,y) for d,p,y in dated_rows]
    n = len(rows)
    if not n:
        report["markets"][market] = {"tested": 0}
        continue
    report["markets"][market] = {
        "tested": n,
        "accuracy": round(
            100 * sum(int(p >= 0.5) == y for p, y in rows) / n, 2
        ),
        "averagePrediction": round(
            100 * sum(p for p, y in rows) / n, 2
        ),
        "actualRate": round(
            100 * sum(y for p, y in rows) / n, 2
        ),
        "brierScore": round(
            sum((p-y)**2 for p, y in rows) / n, 4
        )
    }

    ordered = sorted(dated_rows)
    cutoff = ordered[int(n*0.7)][0]
    train = [(p,y) for d,p,y in ordered if d < cutoff]
    test = [(p,y) for d,p,y in ordered if d >= cutoff]
    if len(train) < 100 or len(test) < 50:
        report["markets"][market]["validation"] = {"status":"insufficient_data"}
        continue
    base = sum(y for p,y in train)/len(train)
    bins = []
    for k in range(10):
        group = [(p,y) for p,y in train if min(9,int(p*10)) == k]
        bins.append((sum(y for p,y in group)+20*base)/(len(group)+20))
    raw = sum((p-y)**2 for p,y in test)/len(test)
    calibrated = sum((bins[min(9,int(p*10))]-y)**2 for p,y in test)/len(test)
    baseline = sum((base-y)**2 for p,y in test)/len(test)
    report["markets"][market]["validation"] = {
        "cutoff": cutoff.isoformat(), "train":len(train), "test":len(test),
        "rawBrier":round(raw,6), "calibratedBrier":round(calibrated,6),
        "baselineBrier":round(baseline,6),
        "improvesBoth":calibrated < min(raw,baseline),
        "trainingBinProbabilities":bins,
        "status":"experimental_holdout"
    }

report["experimentalV40"] = {}
for market, rows in experimental.items():
    rows.sort()
    dates = sorted(set(x[0] for x in rows))
    folds = []
    if len(dates)>=10:
        for k in range(5,10):
            start = dates[len(dates)*k//10]
            end = dates[len(dates)*(k+1)//10] if k<9 else today
            train = [x for x in rows if x[0]<start]
            test = [x for x in rows if start<=x[0]<end]
            if not train or not test: continue
            base = sum(x[4] for x in train)/len(train)
            def brier(idx):
                return round(sum((x[idx]-x[4])**2 for x in test)/len(test),6)
            folds.append({"start":start.isoformat(),"endExclusive":end.isoformat(),
                          "tested":len(test),"oldBrier":brier(1),
                          "normalizedBrier":brier(2),"dixonColesBrier":brier(3),
                          "baselineBrier":round(sum((base-x[4])**2 for x in test)/len(test),6)})
    report["experimentalV40"][market] = {"folds":folds,"status":"research_only"}

output = Path(__file__).resolve().parent.parent / "backtest.json"
output.write_text(
    json.dumps(report, ensure_ascii=False, indent=2),
    encoding="utf-8"
)
print(json.dumps(report, ensure_ascii=False, indent=2))
