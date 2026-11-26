"""Build a presentation-only ESPN team logo catalog; never modify analysis data."""
import json,re
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from league_config import LEAGUES
from nine_league_results_pilot import SOURCES,result_key
from results_source_pilot import read,TR

def logo(team):
    ident=str(team.get("id",""))
    if not ident.isascii() or not ident.isdigit():return None
    for x in team.get("logos",[]):
        url=x.get("href","")
        if re.fullmatch(r"https://a\.espncdn\.com/i/teamlogos/soccer/(?:500|500-dark)/"+ident+r"\.png",url):
            return {"id":ident,"url":url}
    return None

def build(daily,reader=read):
    def group(item):
        label,code,sport=item
        url="https://site.api.espn.com/apis/site/v2/sports/soccer/"+SOURCES[code][1]+"/teams?limit=200"
        wanted={n for r in daily.get("upcoming",[]) if r.get("league")==label for n in r.get("match","").split(" – ") if n}
        try:
            payload=json.loads(reader(url))
            league,=[l for s in payload["sports"] for l in s["leagues"]]
            entries=[x["team"] for x in league["teams"]]
            if not entries:raise ValueError("empty teams")
            found=defaultdict(dict)
            for t in entries:
                v=logo(t)
                if not v:continue
                for n in (t.get("displayName"),t.get("shortDisplayName")):
                    if isinstance(n,str) and n.strip():
                        k=result_key(n,code,sport)
                        if k:found[k][v["id"]]=v
            mapped={}
            for n in wanted|{t["displayName"] for t in entries if isinstance(t.get("displayName"),str)}:
                hits=found[result_key(n,code,sport)]
                if len(hits)==1:mapped[n]=next(iter(hits.values()))
            return label,mapped,{"requested":len(wanted),"matched":len(wanted&mapped.keys()),"error":None}
        except (OSError,ValueError,TypeError,KeyError,AttributeError) as e:
            return label,{},{"requested":len(wanted),"matched":0,"error":type(e).__name__}
    with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(group,LEAGUES))
    return dict(version=1,source="ESPN team directory",updatedAt=datetime.now(TR).isoformat(),leagues={l:m for l,m,_ in results},coverage={l:c for l,_,c in results})

if __name__=="__main__":
    report=build(json.loads(Path("daily.json").read_text(encoding="utf-8")))
    Path("team_logos.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Logo coverage:",json.dumps(report["coverage"],ensure_ascii=False))
    if not any(x["matched"] for x in report["coverage"].values()):raise SystemExit("No verified team logos")
