"""V5.44: extract explicit official match, club and referee identities from bounded discovered links."""
import json,re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit,urljoin,parse_qs
from html.parser import HTMLParser
from concurrent.futures import ThreadPoolExecutor
from tff_fixture_link_discovery import discover,FIXTURE_URL
from tff_referee_source_probe import decode_html,Anchors
from results_source_pilot import read,TR

MAX_SAMPLE=12
class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True);self.parts=[];self.hidden=0
    def handle_starttag(self,tag,attrs):
        if tag in ("script","style"):self.hidden+=1
    def handle_endtag(self,tag):
        if tag in ("script","style") and self.hidden:self.hidden-=1
    def handle_data(self,data):
        if not self.hidden:self.parts.append(data)

def official_id(href,page,key):
    u=urlsplit(urljoin(FIXTURE_URL,href))
    if u.scheme not in ("https","http") or u.netloc.lower()!="www.tff.org" or u.path.lower()!="/default.aspx":return None
    p={}
    for k,v in parse_qs(u.query).items():p.setdefault(k.lower(),[]).extend(v)
    ids=p.get(key,[])
    return ids[0] if p.get("pageid")==[page] and len(ids)==1 and re.fullmatch(r"[0-9]{1,10}",ids[0]) else None

def extract(raw):
    html=decode_html(raw);a=Anchors();a.feed(html);t=VisibleText();t.feed(html)
    visible=" ".join(" ".join(t.parts).split())
    # Only match-detail pages with explicit league heading and unique match code/date.
    if not re.search(r"Trendyol Süper Lig.{0,100}\(Profesyonel Takım\)",visible,re.I):raise ValueError("league context")
    codes=re.findall(r"Maç Kodu:\s*(\d+)",visible,re.I)
    dates=re.findall(r"(?<!\d)(\d{1,2}\.\d{1,2}\.\d{4})\s*-\s*(\d{1,2}:\d{2})(?!\d)",visible)
    if len(set(codes))!=1:raise ValueError("match code missing or ambiguous")
    if len(set(dates))>1:raise ValueError("match date ambiguity")
    kickoff=None
    if dates:
        day,clock=dates[0]
        kickoff=datetime.strptime(day+" "+clock,"%d.%m.%Y %H:%M").replace(tzinfo=TR)
    clubs=[]
    for label,href in a.links:
        ident=official_id(href,"28","kulupid")
        if ident and label and ident not in [x["id"] for x in clubs]:clubs.append(dict(id=ident,label=label))
    if len(clubs)!=2:raise ValueError("club identity ambiguity")
    refs=set()
    for label,href in a.links:
        m=re.fullmatch(r"(.+?)\s*\(Hakem\)",label,re.I)
        ident=official_id(href,"72","hakemid")
        if m and ident:refs.add((ident,m.group(1).strip()))
    referee=None
    if len(refs)==1:
        ident,label=next(iter(refs));referee=dict(id=ident,label=label)
    return dict(matchCode=codes[0],kickoff=kickoff.isoformat() if kickoff else None,kickoffStatus="observed" if kickoff else "missing",clubs=clubs,referee=referee,refereeStatus="observed" if referee else "ambiguous" if refs else "missing")

def build(now,reader=read):
    links=discover(reader(FIXTURE_URL))
    # Stratified bounded sample over discovered season links; no inference from numeric ID order.
    size=min(MAX_SAMPLE,len(links))
    selected=[links[i*(len(links)-1)//max(1,size-1)] for i in range(size)]
    def fetch(link):
        try:return dict(link,status="observed",**extract(reader(link["source"])))
        except (OSError,ValueError,TypeError,KeyError) as exc:return dict(link,status="error",error=type(exc).__name__,detail=str(exc)[:160] if isinstance(exc,ValueError) else None)
    with ThreadPoolExecutor(max_workers=3) as pool:rows=list(pool.map(fetch,selected))
    return dict(version="5.44",mode="official_match_identity_probe",updatedAt=now.isoformat(),discoveredLinks=len(links),requested=len(rows),observed=sum(r["status"]=="observed" for r in rows),withKickoff=sum(r.get("kickoff") is not None for r in rows),withReferee=sum(r.get("referee") is not None for r in rows),automaticFixtureLinking=False,predictionsEnabled=False,decision="PAS",rows=rows)

if __name__=="__main__":
    r=build(datetime.now(TR))
    Path("tff_match_identity_probe.json").write_text(json.dumps(r,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(r,ensure_ascii=False))
    if not any(x.get("referee") and x.get("kickoff") for x in r["rows"]):raise SystemExit("No official dated match and referee identity pairs")
