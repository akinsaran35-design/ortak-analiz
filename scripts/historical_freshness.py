"""Report source freshness without promoting unverified records."""
import json
from pathlib import Path
from datetime import date,timedelta
from collections import Counter,defaultdict

def report(rows,as_of):
    groups=defaultdict(list)
    for r in rows:
        d=date.fromisoformat(r["date"])
        if d<as_of:
            groups[r["source"]].append(d)
    def stats(ds):
        return dict(latest=max(ds).isoformat() if ds else None,monthly=dict(sorted(Counter(d.strftime("%Y-%m") for d in ds).items())),recent={str(n):sum(d>=as_of-timedelta(days=n) for d in ds) for n in (7,30,61)})
    return dict(total=stats([date.fromisoformat(r["date"]) for r in rows if date.fromisoformat(r["date"])<as_of]),sources={k:stats(v) for k,v in groups.items()})
if __name__=="__main__":
    a=json.loads(Path("historical_data.json").read_text())
    t=json.loads(Path("historical_text.json").read_text())
    d=date.fromisoformat(a["asOf"])
    result=dict(status="research_only",realBettingEnabled=False,primary=report(a["matches"],d),pilot=report(t["matches"],d))
    Path("historical_freshness.json").write_text(json.dumps(result,indent=2))
    print("Freshness totals:",{k:result[k]["total"] for k in ("primary","pilot")})
