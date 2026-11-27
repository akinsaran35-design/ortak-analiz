"""Compare archived public football scores against an independent CSV source.
No changes to fixture archives, predictions, or live reports.
"""
import csv, io, json, re, sys, unicodedata
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen

CODES = {"en.3":"E2","de.2":"D2","es.2":"SP2","it.2":"I2","fr.2":"F2"}
ROOT = Path(__file__).resolve().parent.parent

def normalize(s):
    if not isinstance(s,str): return ""
    return " ".join(re.findall(r"[a-z0-9]+","".join(c for c in unicodedata.normalize("NFKD",s.casefold()) if not unicodedata.combining(c))))

def key(d,h,a):
    return d,normalize(h),normalize(a)

def valid(s):
    return isinstance(s,list) and len(s)==2 and all(type(n) is int and n>=0 for n in s)

def csv_index(raw):
    reader=csv.DictReader(io.StringIO(raw.decode("utf-8-sig",errors="strict")))
    if not {"Date","HomeTeam","AwayTeam","FTHG","FTAG"}.issubset(reader.fieldnames or []):
        raise ValueError("invalid CSV schema")
    out=defaultdict(list)
    for row in reader:
        try:
            d=None
            for fmt in ("%d/%m/%Y","%d/%m/%y"):
                try: d=datetime.strptime(row["Date"],fmt).date().isoformat();break
                except ValueError: pass
            if not d or not all((row["HomeTeam"],row["AwayTeam"])):continue
            if not all(re.fullmatch(r"[0-9]+",row[k] or "") for k in ("FTHG","FTAG")):continue
            out[key(d,row["HomeTeam"],row["AwayTeam"])].append([int(row["FTHG"]),int(row["FTAG"])])
        except (ValueError,TypeError,KeyError):continue
    if not out:raise ValueError("no valid independent scores")
    return out

def full_time(m):
    s=m.get("score")
    return s.get("ft") if isinstance(s,dict) else None

def compare(matches,independent):
    scored=[m for m in matches if valid(full_time(m))]
    ids=Counter(key(m["date"],m["team1"],m["team2"]) for m in scored)
    rows=[]
    for m in scored:
        k=key(m["date"],m["team1"],m["team2"])
        a=full_time(m); candidates=independent.get(k,[])
        if ids[k]!=1 or not all(k) or k[1]==k[2] or len(candidates)>1:status="ambiguous"
        elif not candidates:status="unmatched"
        elif a==candidates[0]:status="matched"
        else:status="score_conflict"
        rows.append(dict(date=m["date"],home=m["team1"],away=m["team2"],openfootball=a,independent=candidates[0] if len(candidates)==1 else None,status=status))
    return rows

def main():
    reports=[]
    for code,division in CODES.items():
        source=ROOT/"research"/"openfootball"/"2025-26"/(code+".json")
        a=json.loads(source.read_text())
        url="https://football-data.co.uk/mmz4281/2526/"+division+".csv"
        error=None
        try:
            with urlopen(Request(url,headers={"User-Agent":"OrtakAnaliz research score audit"}),timeout=30) as response:
                raw=response.read(4_000_001)
            if len(raw)>4_000_000:raise ValueError("oversized source")
            independent=csv_index(raw)
            rows=compare(a["matches"],independent)
        except (OSError,ValueError,UnicodeError) as exc:
            error=str(exc)
            rows=compare(a["matches"],{})
            for row in rows:row["status"]="source_unavailable"
        counts=dict(Counter(r["status"] for r in rows))
        reports.append(dict(league=code,sourceBlobSha=a["sourceBlobSha"],secondarySource=url,sourceError=error,counts=counts,nonstandardScoreRows=sum("score" in m and not isinstance(m["score"],dict) for m in a["matches"]),rows=rows))
        print(json.dumps({"league":code,"counts":counts,"error":error,"nonstandardScoreRows":reports[-1]["nonstandardScoreRows"]},ensure_ascii=False))
    totals=Counter()
    for report in reports:totals.update(report["counts"])
    result=dict(mode="historical_score_audit",identityMethod="exact date and normalized full team names; no fuzzy matches",counts=dict(totals),leagues=reports)
    Path("openfootball_score_audit.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    print("TOTAL",json.dumps(dict(totals)))
    if sum(totals.values())!=860:raise SystemExit("unexpected archive score count")
    if any(r["sourceError"] for r in reports):raise SystemExit("independent source access incomplete")

def self_test():
    raw=b"Date,HomeTeam,AwayTeam,FTHG,FTAG\n01/08/25,Home FC,Away FC,2,1\n"
    row={"date":"2025-08-01","team1":"Home FC","team2":"Away FC","score":{"ft":[2,1]}}
    idx=csv_index(raw)
    assert compare([row],idx)[0]["status"]=="matched"
    assert compare([dict(row,score={"ft":[0,0]})],idx)[0]["status"]=="score_conflict"
    assert compare([row,row],idx)[0]["status"]=="ambiguous"
    assert compare([row],{})[0]["status"]=="unmatched"
    assert compare([row],csv_index(raw+raw.splitlines()[1]+b"\n"))[0]["status"]=="ambiguous"
    assert compare([dict(row,score=[0,0]),dict(row,score=None),dict(row,score={})],idx)==[]
    print("OpenFootball score audit self-tests passed")

if __name__=="__main__":
    if sys.argv[1:]==["--self-test"]:self_test()
    else:main()
