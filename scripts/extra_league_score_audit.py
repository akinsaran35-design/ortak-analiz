"""Read-only source audit for six additional competitions; never writes forecast archives."""
import json
from collections import Counter
from datetime import datetime,timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from results_source_pilot import read,csv_results,espn_results,TR,key

COMPETITIONS=(("sco.1","SC0"),("bel.1","B1"),("ger.2","D2"),("esp.2","SP2"),("ita.2","I2"),("fra.2","F2"))
def audit_league(code,csv_code,now,reader=read):
    year=now.year if now.month>=7 else now.year-1
    csv_url=f"https://football-data.co.uk/mmz4281/{year%100:02d}{(year+1)%100:02d}/{csv_code}.csv"
    out=dict(league=code,sourceUrls=[csv_url],errors=[],days=[],rows=[])
    # Exact normalized names only: no fuzzy identity guesses.
    identity=lambda d,h,a:(d,key(h),key(a))
    try: primary=csv_results(reader(csv_url),identity)
    except (OSError,ValueError,TypeError,KeyError,AttributeError) as exc:
        out["errors"].append(dict(source="csv",type=type(exc).__name__))
        return out
    days=sorted({k[0] for k in primary if (now.date()-timedelta(days=28)).isoformat()<=k[0]<now.date().isoformat()},reverse=True)[:3]
    out["days"]=days
    for day in days:
        url=f"https://site.api.espn.com/apis/site/v2/sports/soccer/{code}/scoreboard?dates={day.replace('-','')}"
        out["sourceUrls"].append(url)
        try: secondary=espn_results(json.loads(reader(url)),day,identity)
        except (OSError,ValueError,TypeError,KeyError,AttributeError) as exc:
            out["errors"].append(dict(source="espn",date=day,type=type(exc).__name__))
            continue
        for k in sorted({k for k in primary if k[0]==day}|{k for k in secondary if k[0]==day}):
            a,b=primary.get(k),secondary.get(k)
            status="corroborated" if a is not None and a==b else "conflict" if a is not None and b is not None else "csv_only" if a is not None else "espn_only"
            if not k[1] or not k[2] or k[1]==k[2]:status="invalid_identity"
            out["rows"].append(dict(date=day,home=k[1],away=k[2],csv=a,espn=b,status=status))
    return out

def build(now,reader=read):
    now=now.astimezone(TR)
    with ThreadPoolExecutor(max_workers=3) as pool:
        leagues=list(pool.map(lambda x:audit_league(*x,now,reader),COMPETITIONS))
    for g in leagues:g["counts"]=dict(Counter(x["status"] for x in g["rows"]))
    return dict(version="6.23",mode="source_audit_only",updatedAt=now.isoformat(),leagues=leagues,
        configured=len(COMPETITIONS),responding=sum(bool(g["days"]) and not g["errors"] for g in leagues),
        corroborated=sum(g["counts"].get("corroborated",0) for g in leagues),
        archivesModified=False,predictionsEnabled=False,realBettingEnabled=False,decision="PAS")

if __name__=="__main__":
    report=build(datetime.now(TR))
    Path("extra_league_score_audit.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    for g in report["leagues"]:
        print("LEAGUE_AUDIT",json.dumps({k:g[k] for k in ("league","days","counts","errors")},ensure_ascii=False))
    print("AUDIT_TOTAL",json.dumps({k:report[k] for k in ("configured","responding","corroborated","archivesModified")}))
