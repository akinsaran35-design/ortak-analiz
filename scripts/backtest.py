# Ortak Analiz V2.0 - Historical model backtest
import json
import math
import urllib.request
from datetime import date, timedelta
from pathlib import Path

BASE = "https://raw.githubusercontent.com/openfootball/football.json/master"
from league_config import FIXTURE_CODES
LEAGUES = list(FIXTURE_CODES.values())
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

# V4.1 experimental weighted form; fixed parameters, no future results.
def weighted_stats(past,name,home):
    rows=[]
    for d,h,a,hg,ag in past:
        if h==name: rows.append((d,hg,ag,h==name and home))
        elif a==name: rows.append((d,ag,hg,not home))
    rows=rows[-30:]
    if len(rows)<5: return None
    weights=[math.exp(-math.log(2)*(len(rows)-1-i)/10)*(1 if x[3] else .5) for i,x in enumerate(rows)]
    total=sum(weights)
    return tuple(sum(w*x[j] for w,x in zip(weights,rows))/total for j in (1,2))

def weighted_predict(past,h,a):
    hs=weighted_stats(past,h,True)
    aws=weighted_stats(past,a,False)
    if hs is None or aws is None: return None
    x=max(.15,min(4,(hs[0]+aws[1])/2))
    y=max(.15,min(4,(aws[0]+hs[1])/2))
    return [over(x+y,1),over(x+y,2),(1-math.exp(-x))*(1-math.exp(-y))]

experiments={m:[] for m in MARKETS}

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
        weighted=weighted_predict(past,h,a)
        if weighted is not None:
            for market,p,q,y in zip(MARKETS,probabilities,weighted,actual):
                experiments[market].append((d,p,q,(p+q)/2,y))
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

report["experimentalV41"]={}
for market,rows in experiments.items():
    rows.sort()
    dates=sorted(set(x[0] for x in rows))
    folds=[]
    if len(dates)>=10:
        for k in range(5,10):
            start=dates[len(dates)*k//10]
            end=dates[len(dates)*(k+1)//10] if k<9 else today
            train=[x for x in rows if x[0]<start]
            test=[x for x in rows if start<=x[0]<end]
            if len(train)<100 or len(test)<50: continue
            base=sum(x[4] for x in train)/len(train)
            def score(idx,calibrate=False):
                bins=[]
                for b in range(10):
                    group=[x for x in train if min(9,int(x[idx]*10))==b]
                    bins.append((sum(x[4] for x in group)+20*base)/(len(group)+20))
                return round(sum(((bins[min(9,int(x[idx]*10))] if calibrate else x[idx])-x[4])**2 for x in test)/len(test),6)
            folds.append({"start":start.isoformat(),"endExclusive":end.isoformat(),"tested":len(test),
                "oldBrier":score(1),"weightedBrier":score(2),"ensembleBrier":score(3),
                "oldCalibratedBrier":score(1,True),"weightedCalibratedBrier":score(2,True),
                "ensembleCalibratedBrier":score(3,True),
                "baselineBrier":round(sum((base-x[4])**2 for x in test)/len(test),6)})
    report["experimentalV41"][market]={"folds":folds,"status":"research_only"}

output = Path(__file__).resolve().parent.parent / "backtest.json"
output.write_text(
    json.dumps(report, ensure_ascii=False, indent=2),
    encoding="utf-8"
)
print(json.dumps(report, ensure_ascii=False, indent=2))
# V4.2 - Automatic research model selection
report["modelSelectionV42"] = {}

model_keys = [
    "oldBrier",
    "weightedBrier",
    "ensembleBrier",
    "oldCalibratedBrier",
    "weightedCalibratedBrier",
    "ensembleCalibratedBrier"
]

for market, data in report.get("experimentalV41", {}).items():
    folds = data.get("folds", [])
    total = sum(f["tested"] for f in folds)

    if len(folds) < 5 or total < 500:
        report["modelSelectionV42"][market] = {
            "status": "insufficient_data",
            "liveEnabled": False
        }
        continue

    scores = {
        key: sum(f[key] * f["tested"] for f in folds) / total
        for key in model_keys
    }

    baseline = sum(
        f["baselineBrier"] * f["tested"]
        for f in folds
    ) / total

    best = min(scores, key=scores.get)

    wins = sum(
        f[best] < f["baselineBrier"]
        for f in folds
    )

    improvement = baseline - scores[best]

    eligible = (
        improvement >= 0.001
        and wins >= 4
        and scores[best] < scores["oldBrier"]
    )

    report["modelSelectionV42"][market] = {
        "tested": total,
        "folds": len(folds),
        "bestModel": best,
        "bestBrier": round(scores[best], 6),
        "baselineBrier": round(baseline, 6),
        "improvement": round(improvement, 6),
        "winningFolds": wins,
        "scores": {
            k: round(v, 6)
            for k, v in scores.items()
        },
        "status": "candidate" if eligible else "research_only",
        "liveEnabled": False
    }

output.write_text(
    json.dumps(report, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

print("V4.2 model selection completed")
