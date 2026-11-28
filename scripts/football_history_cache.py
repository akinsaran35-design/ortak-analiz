"""Bounded last-good historical scores only. Never replay old fixtures as live."""
import json
from datetime import date,datetime,timedelta
from pathlib import Path

PATH=Path("football_history_cache.json")
MAX_AGE=timedelta(hours=72)

def read():
    try:
        doc=json.loads(PATH.read_text(encoding="utf-8"))
        if doc.get("version")=="6.96" and isinstance(doc.get("seasons"),dict):return doc
    except (OSError,ValueError,TypeError,AttributeError):pass
    return {"version":"6.96","seasons":{}}

def rows_only(rows,season,cutoff):
    year=int(season[:4])
    grouped={}
    for r in rows:
        try:
            d=date.fromisoformat(r["date"])
            h,a=r["team1"],r["team2"]
            ft=r["score"]["ft"]
            if not date(year,7,1)<=d<date(year+1,7,1) or d>=cutoff or not all(isinstance(x,str) and x.strip() for x in (h,a)) or h==a or not isinstance(ft,list) or len(ft)!=2 or not all(type(n) is int and n>=0 for n in ft):continue
            key=(d.isoformat(),h,a)
            grouped.setdefault(key,[]).append(ft)
        except (KeyError,ValueError,TypeError,AttributeError):continue
    return [dict(date=k[0],team1=k[1],team2=k[2],score={"ft":v[0]}) for k,v in sorted(grouped.items()) if len({tuple(x) for x in v})==1]

def remember(doc,code,season,rows,now):
    scores=rows_only(rows,season,now.date())
    if not scores:return False
    key=code+"|"+season
    old=doc["seasons"].get(key)
    # A suspiciously incomplete refresh must not erase known historical scores.
    if isinstance(old,dict) and isinstance(old.get("rows"),list) and len(scores)<len(old["rows"]):return False
    doc["seasons"][key]=dict(capturedAt=now.isoformat(),rows=scores)
    return True

def recover(doc,code,season,now):
    try:
        old=doc["seasons"][code+"|"+season]
        stamp=datetime.fromisoformat(old["capturedAt"])
        if stamp.tzinfo is None or not timedelta(0)<=now-stamp<=MAX_AGE:return [],None
        scores=rows_only(old["rows"],season,stamp.date())
        if len(scores)!=len(old["rows"]) or not scores:return [],None
        return scores,old["capturedAt"]
    except (KeyError,ValueError,TypeError,AttributeError):return [],None

def write(doc,now,codes,seasons):
    allowed={code+"|"+season for code in codes for season in seasons}
    doc["seasons"]={k:v for k,v in doc["seasons"].items() if k in allowed}
    doc["updatedAt"]=now.isoformat()
    tmp=PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")
    tmp.replace(PATH)
