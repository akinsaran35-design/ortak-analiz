"""Private aggregate Sportmonks free-plan connectivity pilot; never publish fixture data."""
import json,os
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from urllib.parse import urlencode
from collections import Counter

BASE="https://api.sportmonks.com/v3/football/livescores/inplay"
LEAGUES={271,501}
FIELDS=("scores","participants","state","periods","statistics")
def inspect(doc,fields):
    if not isinstance(doc,dict) or not isinstance(doc.get("data"),list):
        raise ValueError("schema")
    data=doc["data"]
    if len(data)>100:raise ValueError("sample size")
    ids=Counter(r.get("id") for r in data if isinstance(r,dict) and type(r.get("id")) is int)
    counts=Counter()
    valid=[]
    for r in data:
        if not isinstance(r,dict) or type(r.get("id")) is not int or r["id"]<=0 or ids[r["id"]]!=1:continue
        if type(r.get("league_id")) is not int or r["league_id"] not in LEAGUES:continue
        valid.append(r)
        for f in fields:
            v=r.get(f)
            if isinstance(v,(list,dict)) and v:counts[f]+=1
    return dict(returned=len(data),eligible=len(valid),fieldPresentNonempty=dict(counts),
                fixtureValuesValidated=False,sourceTimestampVerified=False)
def request(token,fields):
    url=BASE+"?"+urlencode({"include":";".join(fields)})
    req=Request(url,headers={"Authorization":token,"Accept":"application/json"})
    with urlopen(req,timeout=15) as response:
        raw=response.read(2_000_001)
        if len(raw)>2_000_000:raise ValueError("size")
        return json.loads(raw)
def probe(token,reader=request):
    out=dict(version="7.30",mode="private_coverage_only",requestsAttempted=0,
             predictionsEnabled=False,decision="PAS",publicationPermissionVerified=False)
    if not token:return dict(out,status="missing_token")
    out["requestsAttempted"]=1
    try:
        out["base"]=inspect(reader(token,FIELDS),FIELDS)
    except HTTPError as exc:return dict(out,status="provider_http_error",httpStatus=exc.code)
    except (OSError,ValueError,TypeError,KeyError,AttributeError):return dict(out,status="unverified")
    # A second request is useful only when the first actually found eligible live matches.
    if out["base"]["eligible"]:
        out["requestsAttempted"]+=1
        try:
            out["xg"]=inspect(reader(token,("xGFixture",)),("xGFixture","xgfixture","xgFixture"))
        except HTTPError as exc:out["xg"]={"status":"provider_http_error","httpStatus":exc.code}
        except (OSError,ValueError,TypeError,KeyError,AttributeError):out["xg"]={"status":"unverified"}
    return dict(out,status="checked")
if __name__=="__main__":print(json.dumps(probe(os.environ.get("SPORTMONKS_API_TOKEN",""))))
