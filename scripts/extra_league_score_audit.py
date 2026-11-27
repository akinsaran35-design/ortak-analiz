"""Read-only source audit for six additional competitions; never writes forecast archives."""
import json
from collections import Counter
from datetime import datetime,timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from results_source_pilot import read,csv_results,espn_results,TR
from match_odds import normalize

# League-specific, evidence-reviewed aliases only; never infer from score agreement.
# Observed in source name evidence, run 46066942435; scoped to competition.
REVIEWED_ALIASES={
    "sco.1": {
        "hearts": "heart of midlothian"
    },
    "bel.1": {
        "oud heverlee leuven": "oh leuven",
        "beveren": "waasland beveren",
        "gent": "kaa gent",
        "kortrijk": "kv kortrijk",
        "st gilloise": "union st gilloise",
        "standard": "standard liege",
        "charleroi": "royal charleroi",
        "st truiden": "sint truidense",
        "genk": "racing genk",
        "mechelen": "kv mechelen",
        "waregem": "zulte waregem",
        "cercle brugge": "cercle brugge ksv",
        "westerlo": "kvc westerlo"
    },
    "ger.2": {
        "cottbus": "energie cottbus",
        "hertha": "hertha berlin",
        "dresden": "dynamo dresden",
        "karlsruhe": "karlsruher",
        "osnabruck": "vfl osnabruck",
        "nurnberg": "1 nurnberg",
        "braunschweig": "tsv eintracht braunschweig",
        "hannover": "hannover 96",
        "greuther furth": "spvgg greuther furth",
        "bochum": "vfl bochum",
        "wolfsburg": "vfl wolfsburg",
        "bielefeld": "arminia bielefeld",
        "magdeburg": "1 magdeburg",
        "darmstadt": "sv darmstadt 98",
        "heidenheim": "1 heidenheim 1846"
    },
    "esp.2": {
        "celta b": "rc celta fortuna",
        "valladolid": "real valladolid",
        "oviedo": "real oviedo",
        "sp gijon": "sporting gijon",
        "sabadell": "cd sabadell",
        "sociedad b": "real sociedad ii"
    },
    "ita.2": {
        "avellino": "us avellino",
        "verona": "hellas verona"
    },
    "fra.2": {
        "laval": "stade laval",
        "reims": "stade de reims",
        "st etienne": "saint etienne",
        "clermont": "clermont foot",
        "nancy": "as nancy lorraine",
        "dijon": "dijon fco",
        "rodez": "rodez aveyron",
        "red star": "red star 93"
    }
}
def team_key(code,name):
    n=normalize(name)
    return REVIEWED_ALIASES.get(code,{}).get(n,n)

def unmatched_names(rows):
    out={}
    for source in ('csv_only','espn_only'):
        subset=[r for r in rows if r['status']==source]
        out[source]=sorted({r[k] for r in subset for k in ('home','away')})
    return out

COMPETITIONS=(("sco.1","SC0"),("bel.1","B1"),("ger.2","D2"),("esp.2","SP2"),("ita.2","I2"),("fra.2","F2"))
HISTORY_WINDOW_DAYS=28
SAMPLE_DATE_LIMIT=7

def audit_league(code,csv_code,now,reader=read):
    year=now.year if now.month>=7 else now.year-1
    csv_url=f"https://football-data.co.uk/mmz4281/{year%100:02d}{(year+1)%100:02d}/{csv_code}.csv"
    out=dict(league=code,sourceUrls=[csv_url],errors=[],days=[],rows=[])
    # Exact normalized names only: no fuzzy identity guesses.
    identity=lambda d,h,a:(d,team_key(code,h),team_key(code,a))
    try: primary=csv_results(reader(csv_url),identity)
    except (OSError,ValueError,TypeError,KeyError,AttributeError) as exc:
        out["errors"].append(dict(source="csv",type=type(exc).__name__))
        return out
    days=sorted({k[0] for k in primary if (now.date()-timedelta(days=HISTORY_WINDOW_DAYS)).isoformat()<=k[0]<now.date().isoformat()},reverse=True)[:SAMPLE_DATE_LIMIT]
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
    for g in leagues:
        g["counts"]=dict(Counter(x["status"] for x in g["rows"]))
        g["unmatchedNames"]=unmatched_names(g["rows"])
    return dict(version="6.27",historyWindowDays=HISTORY_WINDOW_DAYS,sampleDateLimit=SAMPLE_DATE_LIMIT,mode="source_audit_only",updatedAt=now.isoformat(),leagues=leagues,
        configured=len(COMPETITIONS),responding=sum(bool(g["days"]) and not g["errors"] for g in leagues),
        corroborated=sum(g["counts"].get("corroborated",0) for g in leagues),
        archivesModified=False,predictionsEnabled=False,realBettingEnabled=False,decision="PAS")

if __name__=="__main__":
    report=build(datetime.now(TR))
    Path("extra_league_score_audit.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    for g in report["leagues"]:
        print("LEAGUE_AUDIT",json.dumps({k:g[k] for k in ("league","days","counts","errors")},ensure_ascii=False))
        print("NAME_EVIDENCE",json.dumps({"league":g["league"],"names":g["unmatchedNames"],"rows":[r for r in g["rows"] if r["status"] in ("csv_only","espn_only")]},ensure_ascii=False))
    print("AUDIT_TOTAL",json.dumps({k:report[k] for k in ("configured","responding","corroborated","archivesModified")}))
