"""Descriptive team histories from already collected football-data rows.
No source requests, fixture identity guesses or forecasts.
"""
from datetime import date
from historical_metric_coverage import summarize

def team_view(row,team):
    if row["home"]==team:
        return row
    return dict(row,score=list(reversed(row["score"])),
        stats={k:list(reversed(v)) for k,v in row["stats"].items()})

def window(rows,team,limit=10):
    # Exclude ambiguous multiple same-day appearances rather than choosing arbitrarily.
    counts={}
    for row in rows:
        counts[row["date"]]=counts.get(row["date"],0)+1
    chosen=sorted((r for r in rows if counts[r["date"]]==1),
                  key=lambda r:r["date"],reverse=True)[:limit]
    oriented=[team_view(r,team) for r in chosen]
    stats=summarize(oriented)
    # summarize uses home/away field names; rename for team-relative interpretation.
    metrics={}
    for k,v in stats["metrics"].items():
        metrics[k]=dict(sample=v["sample"],missing=v["missing"],
            forAverage=v["homeAverage"],againstAverage=v["awayAverage"],
            totalAverage=v["totalAverage"])
    return dict(sample=len(chosen),latestCompletedDate=chosen[0]["date"] if chosen else None,
        ambiguousDatesExcluded=sum(n>1 for n in counts.values()),
        wins=sum(r["score"][0]>r["score"][1] for r in oriented),
        draws=sum(r["score"][0]==r["score"][1] for r in oriented),
        losses=sum(r["score"][0]<r["score"][1] for r in oriented),
        metrics=metrics)

def build_team_statistics(rows,cutoff):
    season_start=date(cutoff.year-(cutoff.month<7),7,1).isoformat()
    valid=[r for r in rows if r["date"]<cutoff.isoformat()]
    current=[r for r in valid if r["date"]>=season_start]
    teams=sorted({r[s] for r in current for s in ("home","away")})
    out=[]
    for team in teams:
        history=[r for r in valid if team in (r["home"],r["away"])]
        out.append(dict(team=team,scope="same_division_history",recent=window(history,team),
            home=window([r for r in history if r["home"]==team],team),
            away=window([r for r in history if r["away"]==team],team)))
    return dict(seasonStart=season_start,cutoffExclusive=cutoff.isoformat(),
        teamCount=len(out),windowLimit=10,teams=out,predictionsEnabled=False)
