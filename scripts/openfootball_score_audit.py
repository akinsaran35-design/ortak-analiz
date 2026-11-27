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

# League-scoped reviewed names from source inventories in run 46050613442.
# No score-based alias inference; only apply to OpenFootball side.
ALIAS_PAIRS = {
  "en.3": [
    [
      "Barnsley FC",
      "barnsley"
    ],
    [
      "Blackpool FC",
      "blackpool"
    ],
    [
      "Bolton Wanderers",
      "bolton"
    ],
    [
      "Bradford City",
      "bradford"
    ],
    [
      "Burton Albion",
      "burton"
    ],
    [
      "Cardiff City",
      "cardiff"
    ],
    [
      "Doncaster Rovers",
      "doncaster"
    ],
    [
      "Exeter City",
      "exeter"
    ],
    [
      "Huddersfield Town",
      "huddersfield"
    ],
    [
      "Lincoln City",
      "lincoln"
    ],
    [
      "Luton Town",
      "luton"
    ],
    [
      "Mansfield Town",
      "mansfield"
    ],
    [
      "Northampton Town",
      "northampton"
    ],
    [
      "Peterborough United",
      "peterboro"
    ],
    [
      "Plymouth Argyle",
      "plymouth"
    ],
    [
      "Port Vale FC",
      "port vale"
    ],
    [
      "Reading FC",
      "reading"
    ],
    [
      "Rotherham United",
      "rotherham"
    ],
    [
      "Stevenage FC",
      "stevenage"
    ],
    [
      "Stockport County",
      "stockport"
    ],
    [
      "Wigan Athletic",
      "wigan"
    ],
    [
      "Wycombe Wanderers",
      "wycombe"
    ]
  ],
  "de.2": [
    [
      "1. FC Kaiserslautern",
      "kaiserslautern"
    ],
    [
      "1. FC Magdeburg",
      "magdeburg"
    ],
    [
      "1. FC Nürnberg",
      "nurnberg"
    ],
    [
      "Arminia Bielefeld",
      "bielefeld"
    ],
    [
      "Dynamo Dresden",
      "dresden"
    ],
    [
      "Eintracht Braunschweig",
      "braunschweig"
    ],
    [
      "FC Schalke 04",
      "schalke 04"
    ],
    [
      "Hannover 96",
      "hannover"
    ],
    [
      "Hertha BSC",
      "hertha"
    ],
    [
      "Karlsruher SC",
      "karlsruhe"
    ],
    [
      "SC Paderborn 07",
      "paderborn"
    ],
    [
      "SV 07 Elversberg",
      "elversberg"
    ],
    [
      "SV Darmstadt 98",
      "darmstadt"
    ],
    [
      "SpVgg Greuther Fürth",
      "greuther furth"
    ],
    [
      "VfL Bochum",
      "bochum"
    ]
  ],
  "es.2": [
    [
      "AD Ceuta FC",
      "ceuta"
    ],
    [
      "Burgos CF",
      "burgos"
    ],
    [
      "CD Castellón",
      "castellon"
    ],
    [
      "CD Leganés",
      "leganes"
    ],
    [
      "CD Mirandés",
      "mirandes"
    ],
    [
      "Cádiz CF",
      "cadiz"
    ],
    [
      "Córdoba CF",
      "cordoba"
    ],
    [
      "Deportivo La Coruña",
      "la coruna"
    ],
    [
      "FC Andorra",
      "andorra"
    ],
    [
      "Granada CF",
      "granada"
    ],
    [
      "Málaga CF",
      "malaga"
    ],
    [
      "Racing Santander",
      "santander"
    ],
    [
      "Real Sociedad B",
      "sociedad b"
    ],
    [
      "Real Valladolid",
      "valladolid"
    ],
    [
      "Real Zaragoza",
      "zaragoza"
    ],
    [
      "SD Eibar",
      "eibar"
    ],
    [
      "SD Huesca",
      "huesca"
    ],
    [
      "Sporting Gijón",
      "sp gijon"
    ],
    [
      "UD Almería",
      "almeria"
    ],
    [
      "UD Las Palmas",
      "las palmas"
    ]
  ],
  "it.2": [
    [
      "AC Monza",
      "monza"
    ],
    [
      "AC Reggiana 1919",
      "reggiana"
    ],
    [
      "Calcio Padova",
      "padova"
    ],
    [
      "Carrarese Calcio",
      "carrarese"
    ],
    [
      "Cesena FC",
      "cesena"
    ],
    [
      "Delfino Pescara",
      "pescara"
    ],
    [
      "Empoli FC",
      "empoli"
    ],
    [
      "FC Südtirol",
      "sudtirol"
    ],
    [
      "Frosinone Calcio",
      "frosinone"
    ],
    [
      "Mantova 1911 SSD",
      "mantova"
    ],
    [
      "Modena FC",
      "modena"
    ],
    [
      "Palermo FC",
      "palermo"
    ],
    [
      "SSC Bari",
      "bari"
    ],
    [
      "Spezia Calcio",
      "spezia"
    ],
    [
      "US Avellino",
      "avellino"
    ],
    [
      "US Catanzaro",
      "catanzaro"
    ],
    [
      "Venezia FC",
      "venezia"
    ]
  ],
  "fr.2": [
    [
      "AS Nancy Lorraine",
      "nancy"
    ],
    [
      "AS Saint-Étienne",
      "st etienne"
    ],
    [
      "Amiens SC",
      "amiens"
    ],
    [
      "Clermont Foot 63",
      "clermont"
    ],
    [
      "EA Guingamp",
      "guingamp"
    ],
    [
      "ESTAC Troyes",
      "troyes"
    ],
    [
      "FC Annecy",
      "annecy"
    ],
    [
      "Grenoble Foot 38",
      "grenoble"
    ],
    [
      "Le Mans FC",
      "le mans"
    ],
    [
      "Montpellier HSC",
      "montpellier"
    ],
    [
      "Red Star FC",
      "red star"
    ],
    [
      "Rodez AF",
      "rodez"
    ],
    [
      "SC Bastia",
      "bastia"
    ],
    [
      "Stade Lavallois",
      "laval"
    ],
    [
      "Stade de Reims",
      "reims"
    ],
    [
      "US Boulogne",
      "boulogne"
    ],
    [
      "USL Dunkerque",
      "dunkerque"
    ]
  ]
}
ALIASES = {code:{normalize(a):b for a,b in pairs} for code,pairs in ALIAS_PAIRS.items()}

def key(d,h,a,code=None):
    aliases=ALIASES.get(code,{})
    return d,aliases.get(normalize(h),normalize(h)),aliases.get(normalize(a),normalize(a))

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

def compare(matches,independent,code=None):
    scored=[m for m in matches if valid(full_time(m))]
    ids=Counter(key(m["date"],m["team1"],m["team2"],code) for m in scored)
    rows=[]
    for m in scored:
        k=key(m["date"],m["team1"],m["team2"],code)
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
            rows=compare(a["matches"],independent,code)
        except (OSError,ValueError,UnicodeError) as exc:
            error=str(exc)
            rows=compare(a["matches"],{},code)
            for row in rows:row["status"]="source_unavailable"
        # Inventory both naming systems without inferring club equivalence from scores.
        source_names=sorted({n for m in a["matches"] for n in (m["team1"],m["team2"])})
        independent_names=sorted({n for k in independent for n in k[1:]}) if error is None else []
        source_dates=sorted({m["date"] for m in a["matches"] if valid(full_time(m))})
        independent_dates=sorted({k[0] for k in independent}) if error is None else []
        print("IDENTITY_DIAGNOSTICS",json.dumps(dict(league=code,sourceNames=source_names,secondaryNormalizedNames=independent_names,sourceDateRange=source_dates[::max(1,len(source_dates)-1)],secondaryDateRange=independent_dates[::max(1,len(independent_dates)-1)],sharedDates=len(set(source_dates)&set(independent_dates))),ensure_ascii=False))
        counts=dict(Counter(r["status"] for r in rows))
        reports.append(dict(league=code,sourceBlobSha=a["sourceBlobSha"],secondarySource=url,sourceError=error,counts=counts,nonstandardScoreRows=sum("score" in m and not isinstance(m["score"],dict) for m in a["matches"]),rows=rows))
        print(json.dumps({"league":code,"counts":counts,"error":error,"nonstandardScoreRows":reports[-1]["nonstandardScoreRows"]},ensure_ascii=False))
    totals=Counter()
    for report in reports:totals.update(report["counts"])
    result=dict(mode="historical_score_audit",identityMethod="exact date and reviewed league-scoped club aliases; no fuzzy matches",counts=dict(totals),leagues=reports)
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
    for code,pairs in ALIAS_PAIRS.items():
        assert len(ALIASES[code])==len(pairs)==len(set(ALIASES[code].values()))
    assert key("2025-08-01","Luton Town","AFC Wimbledon","en.3")==("2025-08-01","luton","afc wimbledon")
    assert key("2025-08-01","Luton Town","AFC Wimbledon","it.2")[1]=="luton town"
    print("OpenFootball score audit self-tests passed")

if __name__=="__main__":
    if sys.argv[1:]==["--self-test"]:self_test()
    else:main()
