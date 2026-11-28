"""Independent six-league historical descriptive coverage pilot; no predictions."""
import json
from datetime import datetime,date
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from h2h_history_research import collect
from historical_metric_coverage import summarize
from results_source_pilot import TR,read

LEAGUES=(
    ("İskoçya Premiership","sco.1","soccer_spl","SC0"),
    ("Belçika Pro League","bel.1","soccer_belgium_first_div","B1"),
    ("Almanya 2. Bundesliga","ger.2","soccer_germany_bundesliga2","D2"),
    ("İspanya Segunda División","esp.2","soccer_spain_segunda_division","SP2"),
    ("İtalya Serie B","ita.2","soccer_italy_serie_b","I2"),
    ("Fransa Ligue 2","fra.2","soccer_france_ligue_two","F2"),
)

def build(now,reader=read):
    cutoff=now.astimezone(TR).date()
    def group(entry):
        label,code,sport,csv_code=entry
        rows,sources,errors,invalid=collect(code,sport,cutoff,reader,csv_override=csv_code)
        def season(row):
            d=date.fromisoformat(row["date"])
            return d.year-(d.month<7)
        return dict(league=code,leagueName=label,csvCode=csv_code,sources=sources,
                    sourceErrors=errors,sourceInvalid=invalid,aggregate=summarize(rows),
                    seasons=[dict(season=s["season"],**summarize([r for r in rows if season(r)==s["season"]])) for s in sources])
    with ThreadPoolExecutor(max_workers=4) as pool:groups=list(pool.map(group,LEAGUES))
    return dict(version="7.07",mode="historical_metric_coverage_only",updatedAt=now.isoformat(),
                cutoffExclusive=cutoff.isoformat(),source="football-data.co.uk",
                predictionsEnabled=False,modelCalibrated=False,decision="PAS",
                configuredLeagues=len(groups),respondingLeagues=sum(bool(g["sources"]) for g in groups),
                historicalMatches=sum(g["aggregate"]["matches"] for g in groups),groups=groups)

if __name__=="__main__":
    r=build(datetime.now(TR))
    Path("extra_historical_metric_coverage.json").write_text(json.dumps(r,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    for g in r["groups"]:
        print(json.dumps(dict(league=g["league"],matches=g["aggregate"]["matches"],
            seasons=len(g["seasons"]),samples={k:v["sample"] for k,v in g["aggregate"]["metrics"].items()},
            sourceErrors=g["sourceErrors"]),ensure_ascii=False))
    if not r["respondingLeagues"]:raise SystemExit("No historical source data")
