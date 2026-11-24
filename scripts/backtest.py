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

def predict_v22(history, home, away):
    if len(history) < 40:
        return None
    recent = sorted(history, reverse=True)[:300]
    lh = max(0.3, sum(x[3] for x in recent)/len(recent))
    la = max(0.3, sum(x[4] for x in recent)/len(recent))
    def strength(name, at_home):
        games = sorted([x for x in history if (x[1] if at_home else x[2]) == name], reverse=True)[:12]
        if len(games) < 5:
            return None
        weights = [0.9**i for i in range(len(games))]
        gf = sum(w*x[3 if at_home else 4] for w,x in zip(weights,games))
        ga = sum(w*x[4 if at_home else 3] for w,x in zip(weights,games))
        n = sum(weights)
        return ((gf+5*(lh if at_home else la))/(n+5), (ga+5*(la if at_home else lh))/(n+5))
    hs, aws = strength(home, True), strength(away, False)
    if hs is None or aws is None:
        return None
    h = max(0.15,min(4,hs[0]*aws[1]/lh))
    a = max(0.15,min(4,aws[0]*hs[1]/la))
    return [over(h+a,1),over(h+a,2),(1-math.exp(-h))*(1-math.exp(-a))]

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
        new = predict_v22(past,h,a)
        if new is not None:
            for market,p,q,y in zip(MARKETS,probabilities,new,actual):
                experimental[market].append((d,p,q,y))
        tested += 1

    diagnostics.append({
        "league": league,
        "completed": len(history),
        "tested": tested,
        "errors": errors
    })

report = {
    "version": "2.2-experimental",
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

report["experimentalV22"] = {}
for market, rows in experimental.items():
    rows.sort()
    windows = []
    for start,end in [(0.4,0.6),(0.6,0.8),(0.8,1.0)]:
        if len(rows)<200:
            break
        lo = rows[int(len(rows)*start)][0]
        hi = rows[int(len(rows)*end)][0] if end<1 else today
        train = [y for d,p,q,y in rows if d<lo]
        test = [(p,q,y) for d,p,q,y in rows if lo<=d<hi]
        if not train or not test:
            continue
        base = sum(train)/len(train)
        windows.append({"from":lo.isoformat(),"untilExclusive":hi.isoformat(),"tested":len(test),
            "oldBrier":round(sum((p-y)**2 for p,q,y in test)/len(test),6),
            "newBrier":round(sum((q-y)**2 for p,q,y in test)/len(test),6),
            "baselineBrier":round(sum((base-y)**2 for p,q,y in test)/len(test),6)})
    report["experimentalV22"][market] = {"matchedSample":len(rows),"windows":windows}
output = Path(__file__).resolve().parent.parent / "backtest.json"
output.write_text(
    json.dumps(report, ensure_ascii=False, indent=2),
    encoding="utf-8"
)
print(json.dumps(report, ensure_ascii=False, indent=2))
