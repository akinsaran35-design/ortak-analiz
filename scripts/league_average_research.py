"""Prior-day league averages; no prediction or archive writes."""
from collections import defaultdict
from datetime import date, datetime
import json
from h2h_history_research import collect
from league_config import LEAGUES
from results_source_pilot import TR, read
from historical_metric_coverage import valid_pair

def summarize(rows, cutoff):
    unique = {}
    conflicts = set()
    for r in rows:
        if date.fromisoformat(r["date"]) >= cutoff:
            continue
        key = (r["date"], r["home"], r["away"])
        if key in unique and unique[key] != r:
            conflicts.add(key)
        unique[key] = r
    totals = defaultdict(lambda: [0, 0, 0])
    for key, r in unique.items():
        if key in conflicts:
            continue
        for metric, pair in {"goals": r["score"], **{k: r["stats"].get(k) for k in ("halfTimeGoals", "corners", "yellowCards")}}.items():
            if not valid_pair(pair):
                continue
            if metric == "halfTimeGoals" and (not valid_pair(r["score"]) or any(a > b for a,b in zip(pair,r["score"]))):
                continue
            n = totals[metric]
            n[0] += 1
            n[1] += pair[0]
            n[2] += pair[1]
    return {"conflicts": len(conflicts), "metrics": {k: {"sample": n, "homeMean": h/n if n else None, "awayMean": a/n if n else None, "totalMean": (h+a)/n if n else None} for k in ("goals","halfTimeGoals","corners","yellowCards") for n,h,a in [totals[k]]}}

def build(now, reader=read):
    cutoff = now.astimezone(TR).date()
    groups = []
    for label, code, sport in LEAGUES:
        rows, sources, errors, invalid = collect(code,sport,cutoff,reader)
        groups.append({"league":code,"sources":sources,"sourceErrors":errors,"invalid":invalid,**summarize(rows,cutoff)})
    return {"version":"5.52","cutoffExclusive":cutoff.isoformat(),"predictionsEnabled":False,"decision":"PAS","groups":groups}

if __name__ == "__main__":
    print(json.dumps(build(datetime.now(TR)),ensure_ascii=False,default=str))
