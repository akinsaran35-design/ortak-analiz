"""V5.43: discover official TFF match links, without guessing match IDs."""
import json,re
from urllib.parse import urljoin,urlsplit,parse_qs
from datetime import datetime
from pathlib import Path
from html.parser import HTMLParser
from tff_referee_source_probe import decode_html,BASE
from results_source_pilot import TR,read

FIXTURE_URL="https://www.tff.org/Default.aspx?pageID=198"
MAX_LINKS=400
class FixtureLinks(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True);self.ids=set()
    def handle_starttag(self,tag,attrs):
        if tag!="a":return
        href=dict(attrs).get("href","")
        if not href:return
        u=urlsplit(urljoin(FIXTURE_URL,href))
        if u.scheme not in ("http","https") or u.netloc.lower()!="www.tff.org" or u.path.lower()!="/default.aspx":return
        params={}
        for key,values in parse_qs(u.query).items():
            params.setdefault(key.lower(),[]).extend(values)
        ids=params.get("macid",[])
        if params.get("pageid")!=["29"] or len(ids)!=1 or not re.fullmatch(r"[0-9]{1,10}",ids[0]):return
        self.ids.add(ids[0])
def discover(raw):
    parser=FixtureLinks();parser.feed(decode_html(raw))
    if not parser.ids or len(parser.ids)>MAX_LINKS:raise ValueError("fixture links missing or out of bounds")
    return [dict(matchId=i,source=BASE.format(i)) for i in sorted(parser.ids,key=int)]
def build(now,reader=read):
    links=discover(reader(FIXTURE_URL))
    return dict(version="5.43",mode="official_fixture_link_discovery_only",updatedAt=now.isoformat(),source=FIXTURE_URL,links=links,linkCount=len(links),fixtureIdentityVerified=False,automaticFixtureLinking=False,predictionsEnabled=False,decision="PAS")
if __name__=="__main__":
    r=build(datetime.now(TR))
    Path("tff_fixture_link_discovery.json").write_text(json.dumps(r,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(r,ensure_ascii=False))
