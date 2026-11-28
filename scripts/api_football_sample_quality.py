"""Aggregate API-Football sample quality; no odds, team names or identifiers published."""
from collections import Counter
from datetime import timedelta
from odds_snapshot_validation import instant

def inspect_sample(doc,now):
    rows=doc.get("response")
    if not isinstance(rows,list):
        raise ValueError("response schema")
    paging=doc.get("paging",{})
    current,total=paging.get("current"),paging.get("total")
    pages_valid=(type(current) is int and type(total) is int and current==1
                 and (total>=1 or (total==0 and not rows)))
    out=dict(sampleEventCount=len(rows),paginationVerified=pages_valid,
             sampleComplete=pages_valid and total<=1,
             totalPages=total if pages_valid else None,
             uniqueFutureEvents=0,freshWithin30Minutes=0,
             observedWithin3Hours=0,duplicateOrInvalidRows=0)
    ids=Counter(r.get("fixture",{}).get("id") for r in rows
        if isinstance(r,dict) and isinstance(r.get("fixture"),dict)
        and type(r["fixture"].get("id")) is int)
    for row in rows:
        try:
            fid=row["fixture"]["id"]
            kickoff=instant(row["fixture"]["date"])
            stamp=instant(row["update"])
            if type(fid) is not int or fid<=0 or ids[fid]!=1 or kickoff<=now or stamp>now:
                raise ValueError("invalid or started event")
            if not isinstance(row["bookmakers"],list) or not row["bookmakers"]:
                raise ValueError("no books")
        except (KeyError,TypeError,ValueError,AttributeError,OverflowError):
            out["duplicateOrInvalidRows"]+=1
            continue
        out["uniqueFutureEvents"]+=1
        if now-stamp<=timedelta(hours=3):out["observedWithin3Hours"]+=1
        if now-stamp<=timedelta(minutes=30):out["freshWithin30Minutes"]+=1
    return out
