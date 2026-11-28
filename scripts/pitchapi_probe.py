"""Read-only alternative-source probe. No credential, no data; never modify model archives."""
import json,os,re
from urllib.request import Request,build_opener,HTTPRedirectHandler
from urllib.error import HTTPError,URLError
from pathlib import Path

BASE="https://api.pitchapi.dev/v1/"
TARGETS=(("sco.1","Scotland","Premiership"),("bel.1","Belgium","First Division A"),
    ("ger.2","Germany","2. Bundesliga"),("esp.2","Spain","LaLiga2"),
    ("ita.2","Italy","Serie B"),("fra.2","France","Ligue 2"))

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):
        return None

def get(path,key):
    if not re.fullmatch(r"[a-zA-Z0-9_/]+",path):
        raise ValueError("invalid path")
    req=Request(BASE+path,headers={"X-API-KEY":key,"Accept":"application/json"})
    with build_opener(NoRedirect()).open(req,timeout=20) as res:
        raw=res.read(4_000_001)
    if len(raw)>4_000_000:
        raise ValueError("response exceeds limit")
    payload=json.loads(raw)
    if not isinstance(payload,dict) or "data" not in payload or "error" in payload:
        raise ValueError("invalid envelope")
    return payload["data"]

def catalog(data):
    rows=data.get("leagues") if isinstance(data,dict) else data
    if not isinstance(rows,list):
        raise ValueError("invalid league catalogue")
    out=[]
    for code,country,name in TARGETS:
        matches=[]
        for item in rows:
            if not isinstance(item,dict):
                continue
            nation=item.get("country")
            if isinstance(nation,dict):
                nation=nation.get("name")
            if item.get("name")==name and nation==country and isinstance(item.get("id"),str) and re.fullmatch(r"l_[A-Za-z0-9]{6}",item["id"]):
                matches.append(item["id"])
        out.append(dict(league=code,country=country,name=name,status="matched" if len(matches)==1 else "missing_or_ambiguous",providerId=matches[0] if len(matches)==1 else None))
    ids=[v["providerId"] for v in out if v["providerId"]]
    for v in out:
        if v["providerId"] and ids.count(v["providerId"])>1:
            v.update(status="duplicate_provider_id",providerId=None)
    return out

SAFE_CODES={"UNAUTHORIZED","INVALID_PARAMETER","RESOURCE_NOT_FOUND","ANALYTICS_UNAVAILABLE",
    "HALVES_UNAVAILABLE","INTERNAL_SERVER_ERROR","RATE_LIMIT_EXCEEDED","DAILY_QUOTA_EXCEEDED",
    "FORBIDDEN","ACCESS_DENIED","IP_NOT_ALLOWED"}

def safe_http_diagnostics(exc):
    result=dict(httpStatus=exc.code,responseFormat="unknown",providerErrorCode=None,requestId=None)
    try:
        content_type=exc.headers.get_content_type() if exc.headers else ""
        request_id=exc.headers.get("X-Request-ID","") if exc.headers else ""
        # Only conventional UUID-shaped request IDs are safe to log.
        if re.fullmatch(r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}",request_id):
            result["requestId"]=request_id
        raw=exc.read(8192)
        if content_type=="application/json":
            result["responseFormat"]="json"
            payload=json.loads(raw)
            error=payload.get("error") if isinstance(payload,dict) else None
            code=error.get("code") if isinstance(error,dict) else None
            if isinstance(code,str) and code in SAFE_CODES:
                result["providerErrorCode"]=code
        elif content_type=="text/html":
            result["responseFormat"]="html"
        elif content_type.startswith("text/"):
            result["responseFormat"]="text"
    except (OSError,ValueError,TypeError,AttributeError):
        pass
    return result

def run(key,reader=get):
    report=dict(version="6.51c",source="PitchAPI",mode="connection_catalog_probe",
        status="missing_key",keyFormatValid=False,leagues=[],matched=0,xgValidated=False,xtValidated=False,
        usedForTraining=False,existingArchivesModified=False,productionModelValidated=False)
    if not key:
        return report
    if not re.fullmatch(r"pk_(?:live|test)_[A-Za-z0-9_-]+",key):
        report["status"]="invalid_key_format"
        return report
    report["keyFormatValid"]=True
    # Report only safe diagnostics, never raw response or exception text.
    try:
        report["leagues"]=catalog(reader("leagues",key))
        report["matched"]=sum(v["status"]=="matched" for v in report["leagues"])
        report["status"]="catalog_received"
    except HTTPError as exc:
        report.update(status="http_error",**safe_http_diagnostics(exc))
    except (URLError,OSError,ValueError,TypeError,KeyError,AttributeError) as exc:
        report.update(status="connection_or_schema_error",errorType=type(exc).__name__)
    return report

if __name__=="__main__":
    report=run(os.environ.get("PITCHAPI_API_KEY","").strip())
    Path("pitchapi_connection_report.json").write_text(json.dumps(report,indent=2)+"\n")
    print("PITCHAPI_PROBE",json.dumps(report))
