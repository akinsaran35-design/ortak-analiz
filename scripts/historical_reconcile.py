"""Audit text candidates against the existing archive; no automatic promotion."""
import json
from pathlib import Path
from collections import defaultdict

def reconcile(primary,pilot):
    def key(row):
        return (row["date"],row["home"].strip().casefold(),row["away"].strip().casefold())
    groups=defaultdict(list)
    for row in primary:
        groups[key(row)].append(row)
    candidates=defaultdict(list)
    for row in pilot:
        candidates[key(row)].append(row)
    report=dict(status="research_only",realBettingEnabled=False,primaryCount=len(primary),pilotRawCount=len(pilot),overlap=[],conflicts=[],unverifiedNew=[])
    for k,rows in sorted(candidates.items()):
        existing=groups.get(k,[])
        combined=existing+rows
        conflict=len({tuple(x["ft"]) for x in combined})>1 or len({tuple(x["ht"]) for x in combined if x.get("ht") is not None})>1
        bucket="conflicts" if conflict else "overlap" if existing else "unverifiedNew"
        report[bucket].append(dict(key=list(k),primary=existing,pilot=rows))
    report["counts"]={k:len(report[k]) for k in ("overlap","conflicts","unverifiedNew")}
    report["pilotExactKeyCount"]=len(candidates)
    return report
if __name__=="__main__":
    p=json.loads(Path("historical_data.json").read_text())
    t=json.loads(Path("historical_text.json").read_text())
    r=reconcile(p["matches"],t["matches"])
    Path("historical_reconcile.json").write_text(json.dumps(r,ensure_ascii=False,indent=2))
    print("Reconciliation:",r["counts"])
