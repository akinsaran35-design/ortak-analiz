"""One bounded, private date-range coverage sample; no paid xG add-on requests."""
import os,json
from datetime import datetime,timedelta,timezone
from collections import Counter
from urllib.request import Request,urlopen
from urllib.parse import urlencode
from urllib.error import HTTPError
from sportmonks_access_probe import LEAGUES,FIELDS,inspect

BASE="https://api.sportmonks.com/v3/football/fixtures/between/"
FIELDS=(*FIELDS,"lineups","referees","events")
def request(token,start,end):
    url=BASE+start+"/"+end+"?"+urlencode({"include":";".join(FIELDS),"filters":"fixtureLeagues:271,501","per_page":50,"page":1})
    req=Request(url,headers={"Authorization":token,"Accept":"application/json"})
    with urlopen(req,timeout=20) as response:
        raw=response.read(4_000_001)
        if len(raw)>4_000_000:raise ValueError("size")
        return json.loads(raw)
def classify(row,now,start,end):
    ts=row.get("starting_at_timestamp")
    if type(ts) is not int:return "unverified"
    try:kick=datetime.fromtimestamp(ts,timezone.utc)
    except (ValueError,OverflowError,OSError):return "unverified"
    if not start<=kick.date()<=end:return "unverified"
    state=row.get("state_id")
    detail=row.get("state")
    if type(state) is not int or not isinstance(detail,dict) or detail.get("id")!=state:return "unverified"
    if state==1 and kick>now:return "upcoming"
    if state in (2,3,22) and kick<=now:return "in_play_reported"
    if state==5 and kick<now:return "completed_reported"
    return "other_or_unverified"
def summarize(doc,now,start,end):
    base=inspect(doc,FIELDS)
    ids=Counter(r.get("id") for r in doc["data"] if isinstance(r,dict) and type(r.get("id")) is int)
    groups=[]
    for league in sorted(LEAGUES):
        rows=[r for r in doc["data"] if isinstance(r,dict) and type(r.get("id")) is int and r["id"]>0 and ids[r["id"]]==1 and r.get("league_id")==league]
        buckets={}
        for row in rows:
            k=classify(row,now,start,end)
            buckets.setdefault(k,[]).append(row)
        groups.append(dict(leagueId=league,states={k:inspect({"data":v},FIELDS) for k,v in sorted(buckets.items())}))
    p=doc.get("pagination")
    return dict(base=base,groups=groups,paginationComplete=isinstance(p,dict) and p.get("has_more") is False)
def probe(token,now,reader=request):
    out=dict(version="7.31",mode="private_fixture_coverage_only",requestsAttempted=0,predictionsEnabled=False,
             decision="PAS",publicationPermissionVerified=False,xgStatus="documented_paid_addon_not_requested")
    if not token:return dict(out,status="missing_token")
    now=now.astimezone(timezone.utc);start=now.date()-timedelta(days=7);end=now.date()+timedelta(days=2)
    out.update(startDate=start.isoformat(),endDate=end.isoformat(),requestsAttempted=1)
    try:return dict(out,status="checked",**summarize(reader(token,start.isoformat(),end.isoformat()),now,start,end))
    except HTTPError as exc:return dict(out,status="provider_http_error",httpStatus=exc.code)
    except (OSError,ValueError,TypeError,KeyError,AttributeError):return dict(out,status="unverified")
if __name__=="__main__":print(json.dumps(probe(os.environ.get("SPORTMONKS_API_TOKEN",""),datetime.now(timezone.utc))))
