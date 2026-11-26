"""Apply corroborated results only to existing, strictly pre-match records."""
import json
from datetime import date,datetime
from pathlib import Path

def load_verified(root,now=None):
    p=Path(root)/"verified_results.json"
    data=json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"records":[]}
    rows=data["records"]
    if not isinstance(rows,list): raise ValueError("verified result records")
    auto=Path(root)/"results_source_pilot.json"
    if now is not None and auto.exists():
        from automatic_results import verified_rows
        rows=rows+verified_rows(json.loads(auto.read_text(encoding="utf-8")),now)
    multi=Path(root)/"multi_league_results.json"
    if now is not None and multi.exists():
        from multi_league_results import verified_rows as multi_verified_rows
        rows=rows+multi_verified_rows(json.loads(multi.read_text(encoding="utf-8")),now)
    return rows

def settle_verified(records,rows,now,league_codes=None):
    today=now.date()
    found={}
    conflicts=set()
    for row in rows:
        try:
            ident=(row["date"],row["league"],row["home"],row["away"])
            if date.fromisoformat(ident[0])>=today: continue
            result=row["result"]
            sources=row["sources"]
            if not isinstance(result,list) or len(result)!=2 or not all(type(x) is int and x>=0 for x in result): continue
            if not isinstance(sources,list) or len(set(sources))<2 or not all(isinstance(s,str) and s.startswith("https://") for s in sources): continue
            if ident in found and found[ident]["result"]!=result: conflicts.add(ident)
            found[ident]=row
        except (ValueError,TypeError,KeyError): continue
    settled=0
    for record in records.values():
        try:
            if league_codes is None:
                league=record["league"]; h,a=record["home"],record["away"]
            else:
                league=league_codes.get(record["league"]); h,a=record["match"].split(" – ")
            ident=(record["date"],league,h,a)
            if ident in conflicts or ident not in found or record["result"] is not None: continue
            recorded=datetime.fromisoformat(record["recordedAt"])
            if recorded.tzinfo is None or recorded>now or recorded.astimezone(now.tzinfo).date()>=date.fromisoformat(record["date"]): continue
            row=found[ident]
            record["result"]=list(row["result"])
            record["settledAt"]=now.isoformat()
            record["resultSources"]=list(row["sources"])
            settled+=1
        except (ValueError,TypeError,KeyError): continue
    return settled
