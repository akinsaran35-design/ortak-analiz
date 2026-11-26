"""Conservative Football.TXT research importer."""
import json,re
from datetime import date,timedelta
from pathlib import Path
from urllib.request import urlopen
from urllib.parse import quote
MONTHS={m:i+1 for i,m in enumerate("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split())}
def parse(content,source,today):
    current=None
    year=None
    rows=[]
    for line in content.splitlines():
        s=line.strip()
        d=re.fullmatch(r"(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun) ([A-Z][a-z]{2}) (\d{1,2})(?: (\d{4}))?",s)
        if d:
            month,day,y=d.groups()
            try:
                if y: year=int(y)
                elif current and MONTHS[month]<current.month: year=None
                current=date(year,MONTHS[month],int(day)) if year else None
            except (ValueError,KeyError): current=None
            continue
        if not current or not today-timedelta(days=365)<=current<today: continue
        m=re.fullmatch(r"(?:\d{1,2}:\d{2}\s+)?(.+?)\s+v\s+(.+?)\s+(\d+)-(\d+)(?:\s+\((\d+)-(\d+)\))?",s)
        if not m: continue
        h,a,x,y,u,v=m.groups()
        ft=[int(x),int(y)]
        ht=[int(u),int(v)] if u is not None else None
        if ht and any(i>j for i,j in zip(ht,ft)): ht=None
        if h.strip().casefold()==a.strip().casefold(): continue
        rows.append(dict(date=current.isoformat(),home=h.strip(),away=a.strip(),ft=ft,ht=ht,source=source))
    return rows
def run(discovery,today):
    result=dict(status="research_only",realBettingEnabled=False,matches=[],errors=[],files=[])
    for row in discovery["sources"]:
        for p in row["candidatePaths"]:
            url="https://raw.githubusercontent.com/openfootball/"+row["repository"]+"/HEAD/"+quote(p)
            try:
                with urlopen(url,timeout=10) as f: content=f.read().decode("utf-8-sig")
                matches=parse(content,url,today)
                result["matches"].extend(matches)
                result["files"].append(dict(source=url,matchCount=len(matches)))
            except Exception as exc: result["errors"].append(dict(source=url,error=type(exc).__name__))
    result["rawMatchCount"]=len(result["matches"])
    return result
if __name__=="__main__":
    r=run(json.loads(Path("source_discovery.json").read_text()),date.today())
    Path("historical_text.json").write_text(json.dumps(r,ensure_ascii=False,indent=2))
    print("Text pilot raw matches:",r["rawMatchCount"],"files:",len(r["files"]),"errors:",len(r["errors"]))
