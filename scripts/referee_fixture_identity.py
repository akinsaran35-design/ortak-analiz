"""Private referee attribution matching. No publication or forecast use.
Require same competition, ordered exact team names, kickoff and unique identities.
Provider league IDs must be corroborated by their country/name metadata.
"""
from collections import Counter
from datetime import datetime
import re,unicodedata

# Candidate IDs; require the accompanying provider metadata, otherwise abstain.
LEAGUES={
39:("en.1","England","Premier League"),40:("en.2","England","Championship"),
78:("de.1","Germany","Bundesliga"),79:("ger.2","Germany","2. Bundesliga"),
140:("es.1","Spain","La Liga"),141:("esp.2","Spain","Segunda División"),
135:("it.1","Italy","Serie A"),136:("ita.2","Italy","Serie B"),
61:("fr.1","France","Ligue 1"),62:("fra.2","France","Ligue 2"),
88:("nl.1","Netherlands","Eredivisie"),94:("pt.1","Portugal","Primeira Liga"),
203:("tr.1","Turkey","Süper Lig"),179:("sco.1","Scotland","Premiership"),
144:("bel.1","Belgium","Jupiler Pro League"),
}
def norm(s):
    if not isinstance(s,str):raise ValueError("name")
    t=unicodedata.normalize("NFKD",s.casefold())
    return " ".join(re.findall(r"[^\W_]+","".join(c for c in t if not unicodedata.combining(c)),re.UNICODE))
def instant(s):
    t=datetime.fromisoformat(s.replace("Z","+00:00"))
    if t.tzinfo is None:raise ValueError("timezone")
    return t
def identity(code,h,a,kickoff):
    h,a=norm(h),norm(a)
    if not h or not a or h==a:raise ValueError("teams")
    return code,h,a,instant(kickoff)
def match(doc,groups):
    if doc.get("errors") not in ({},[]) or not isinstance(doc.get("response"),list) or doc.get("results")!=len(doc["response"]) or doc.get("paging")!={"current":1,"total":1}:
        raise ValueError("incomplete provider response")
    candidates={};ids=Counter();targets={};target_ids=Counter()
    for group in groups:
        if group.get("error") or group.get("errors"):continue
        for r in group["rows"]:
            if r.get("state")!="pre" or r.get("status")!="STATUS_SCHEDULED":continue
            try:
                k=identity(group["league"],r["home"],r["away"],r["kickoff"])
                event_id=r["eventId"]
                if not isinstance(event_id,str) or not event_id.isdigit():continue
                targets.setdefault(k,[]).append(event_id);target_ids[(group["league"],event_id)]+=1
            except (ValueError,TypeError,KeyError,AttributeError):continue
    for row in doc["response"]:
        try:
            f=row["fixture"];l=row["league"];i=f["id"]
            if type(i) is not int or i<=0:continue
            ids[i]+=1
            meta=LEAGUES.get(l["id"])
            if not meta or norm(l["country"])!=norm(meta[1]) or norm(l["name"])!=norm(meta[2]) or f["status"]["short"]!="NS":continue
            k=identity(meta[0],row["teams"]["home"]["name"],row["teams"]["away"]["name"],f["date"])
            name=f.get("referee")
            if not isinstance(name,str) or norm(name) in ("","unknown","n a","na","tbd","none"):name=None
            candidates.setdefault(k,[]).append((i,name))
        except (ValueError,TypeError,KeyError,AttributeError):continue
    result=[]
    for k,events in targets.items():
        matches=candidates.get(k,[])
        if len(events)!=1 or target_ids[(k[0],events[0])]!=1 or len(matches)!=1 or ids[matches[0][0]]!=1:
            continue
        pid,ref=matches[0]
        result.append(dict(league=k[0],eventId=events[0],providerId=pid,referee=ref,
                           status="source_observed" if ref else "missing_referee"))
    return dict(eligibleIdentities=len(targets),matched=len(result),
                withReferee=sum(x["referee"] is not None for x in result),rows=result,
                predictionsEnabled=False,decision="PAS",publicationAllowed=False)
