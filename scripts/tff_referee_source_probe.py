"""V5.42: bounded official TFF match-detail referee source probe."""
import json,re
from html.parser import HTMLParser
from datetime import datetime
from pathlib import Path
from results_source_pilot import read,TR

BASE="https://www.tff.org/Default.aspx?macID={}&pageID=29"
# Explicit official links inspected 2026-11-27; no crawling guessed IDs.
SAMPLES=[
 ("317884","22.11.2026","KASIMPAŞA","ALANYASPOR"),
 ("317894","27.11.2026","ALANYASPOR","KONYASPOR"),
 ("317895","27.11.2026","RİZESPOR","KASIMPAŞA"),
]
class Anchors(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True);self.links=[];self.parts=None;self.href=""
    def handle_starttag(self,tag,attrs):
        if tag=="a":self.parts=[];self.href=dict(attrs).get("href","")
    def handle_data(self,data):
        if self.parts is not None:self.parts.append(data)
    def handle_endtag(self,tag):
        if tag=="a" and self.parts is not None:
            self.links.append((" ".join("".join(self.parts).split()),self.href));self.parts=None

def decode_html(raw):
    # TFF serves legacy Turkish encodings; honor a supported declared charset.
    declared=re.search(rb'charset\s*=\s*["\']?\s*([a-zA-Z0-9_-]+)',raw[:16384],re.I)
    enc=declared.group(1).decode("ascii").lower() if declared else None
    supported={"utf-8":"utf-8-sig","windows-1254":"cp1254","iso-8859-9":"iso8859_9","cp1254":"cp1254"}
    for codec in dict.fromkeys([supported.get(enc,"utf-8-sig"),"utf-8-sig","cp1254"]):
        try:return raw.decode(codec)
        except UnicodeDecodeError:continue
    raise ValueError("unsupported page encoding")

def extract(raw,expected):
    parser=Anchors()
    html=decode_html(raw)
    parser.feed(html)
    # Require the official match heading and date; do not infer from nearby fixtures.
    if "Süper Lig" not in html or expected[1] not in html:raise ValueError("match context")
    if not all(any(name in label for label,_ in parser.links) for name in expected[2:]):raise ValueError("team labels")
    names=set()
    for label,href in parser.links:
        m=re.fullmatch(r"(.+?)\s*\(Hakem\)",label,re.IGNORECASE)
        if m:names.add(m.group(1).strip())
    return dict(status="observed" if len(names)==1 else "ambiguous" if names else "missing",refereeLabel=next(iter(names)) if len(names)==1 else None)
def build(now,reader=read):
    rows=[]
    for sample in SAMPLES:
        ident,day,home,away=sample;url=BASE.format(ident)
        row=dict(matchId=ident,date=day,homeLabel=home,awayLabel=away,source=url)
        try:row.update(extract(reader(url),sample))
        except (OSError,ValueError,UnicodeError) as exc:row.update(status="error",refereeLabel=None,error=type(exc).__name__)
        rows.append(row)
    return dict(version="5.42",mode="official_referee_source_probe",updatedAt=now.isoformat(),source="TFF",automaticFixtureLinking=False,cardModelEnabled=False,predictionsEnabled=False,decision="PAS",rows=rows)
if __name__=="__main__":
    r=build(datetime.now(TR));Path("tff_referee_source_probe.json").write_text(json.dumps(r,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(r,ensure_ascii=False))
    if not any(x["status"]=="observed" for x in r["rows"]):raise SystemExit("No referee labels extracted from real source")
