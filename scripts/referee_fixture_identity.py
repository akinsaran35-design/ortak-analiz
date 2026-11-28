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
def shadow_alias_candidates(targets,candidates,target_ids,ids,strict_rows,pairs=None):
    """Measure unique candidates using existing CSV/ESPN aliases; never promote them.
    API-Football aliases have not been independently verified.
    """
    from league_config import LEAGUES as CORE
    from extra_historical_metric_coverage import LEAGUES as EXTRA
    from extra_fixture_aliases import fixture_team_key
    sports={entry[1]:entry[2] for entry in (*CORE,*EXTRA)}
    def key(k):
        code,h,a,t=k
        if code not in sports:return None
        h,a=(fixture_team_key(name,code,sports[code]) for name in (h,a))
        if not h or not a or h==a:return None
        return code,h,a,t
    left={};right={}
    for k in targets:
        ck=key(k)
        if ck is not None:left.setdefault(ck,[]).append(k)
    for k in candidates:
        ck=key(k)
        if ck is not None:right.setdefault(ck,[]).append(k)
    used_events={(r["league"],r["eventId"]) for r in strict_rows}
    used_provider={r["providerId"] for r in strict_rows}
    counts=Counter();with_referee=Counter()
    for ck,keys in left.items():
        other=right.get(ck,[])
        if len(keys)!=1 or len(other)!=1:continue
        k,p=keys[0],other[0]
        events=targets[k];rows=candidates[p]
        if k==p or len(events)!=1 or len(rows)!=1:continue
        if target_ids[(k[0],events[0])]!=1 or ids[rows[0][0]]!=1:continue
        if (k[0],events[0]) in used_events or rows[0][0] in used_provider:continue
        if pairs is not None:pairs[(k[0],events[0],rows[0][0])]=bool(rows[0][1])
        counts[k[0]]+=1
        if rows[0][1]:with_referee[k[0]]+=1
    return dict(mode="candidate_only",verified=False,additionalCandidates=sum(counts.values()),
                candidatesWithReferee=sum(with_referee.values()),
                groups=[dict(league=c,candidates=n,withReferee=with_referee[c]) for c,n in sorted(counts.items())])

def source_name_evidence(targets,candidates,target_ids,ids,strict_rows,source_names,pairs=None):
    """Measure ordered names explicitly supplied by ESPN; never promote candidates."""
    used_targets={(r["league"],r["eventId"]) for r in strict_rows}
    used_providers={r["providerId"] for r in strict_rows}
    possible={}; reverse=Counter()
    for k,events in targets.items():
        if len(events)!=1 or target_ids[(k[0],events[0])]!=1:continue
        names=source_names.get(k)
        if not names:continue
        h,a=names
        if h & a:continue
        for p in candidates:
            if p[0]!=k[0] or p[3]!=k[3] or p[1] not in h or p[2] not in a:continue
            possible.setdefault(k,[]).append(p)
            reverse[p]+=1
    counts=Counter();refs=Counter()
    for k,keys in possible.items():
        if len(keys)!=1:continue
        p=keys[0];rows=candidates[p]
        if k==p or reverse[p]!=1 or len(rows)!=1 or ids[rows[0][0]]!=1:continue
        if (k[0],targets[k][0]) in used_targets or rows[0][0] in used_providers:continue
        if pairs is not None:pairs[(k[0],targets[k][0],rows[0][0])]=bool(rows[0][1])
        counts[k[0]]+=1
        if rows[0][1]:refs[k[0]]+=1
    return dict(mode="source_name_candidate_only",verified=False,
                additionalCandidates=sum(counts.values()),candidatesWithReferee=sum(refs.values()),
                groups=[dict(league=c,candidates=n,withReferee=refs[c]) for c,n in sorted(counts.items())])

def combined_evidence(alias,source,eligible,strict_count):
    """Count distinct candidates; reject disagreements on either identity."""
    a,b=set(alias),set(source)
    union=a|b
    left=Counter(k[:2] for k in union)
    right=Counter(k[2] for k in union)
    accepted={k for k in union if left[k[:2]]==right[k[2]]==1}
    return dict(mode="deduplicated_candidate_only",verified=False,
                sharedCandidates=len(accepted&a&b),
                aliasOnly=len((accepted&a)-b),sourceOnly=len((accepted&b)-a),
                conflictingPairs=len(union-accepted),additionalCandidates=len(accepted),
                candidatesWithReferee=sum(bool(alias.get(k) or source.get(k)) for k in accepted),
                remainingIdentities=max(0,eligible-strict_count-len(accepted)),
                predictionsEnabled=False)

def match(doc,groups):
    if doc.get("errors") not in ({},[]) or not isinstance(doc.get("response"),list) or doc.get("results")!=len(doc["response"]) or doc.get("paging")!={"current":1,"total":1}:
        raise ValueError("incomplete provider response")
    candidates={};ids=Counter();targets={};target_ids=Counter()
    metadata_rejected=Counter();scheduled_seen=Counter();diagnostics={}
    unavailable=[];source_names={}
    for group in groups:
        if group.get("error") or group.get("errors"):
            unavailable.append(group["league"]);continue
        for r in group["rows"]:
            if r.get("state")!="pre" or r.get("status")!="STATUS_SCHEDULED":continue
            try:
                k=identity(group["league"],r["home"],r["away"],r["kickoff"])
                event_id=r["eventId"]
                if not isinstance(event_id,str) or not event_id.isdigit():continue
                targets.setdefault(k,[]).append(event_id);target_ids[(group["league"],event_id)]+=1
                info=r.get("sourceTeamNames")
                if isinstance(info,dict) and all(isinstance(info.get(s),list) for s in ("home","away")):
                    h={norm(n) for n in info["home"] if isinstance(n,str) and norm(n)}
                    a={norm(n) for n in info["away"] if isinstance(n,str) and norm(n)}
                    if k[1] in h and k[2] in a:
                        source_names[k]=(h,a)
            except (ValueError,TypeError,KeyError,AttributeError):continue
    for row in doc["response"]:
        try:
            f=row["fixture"];l=row["league"];i=f["id"]
            if type(i) is not int or i<=0:continue
            ids[i]+=1
            meta=LEAGUES.get(l["id"])
            if not meta:continue
            if norm(l["country"])!=norm(meta[1]) or norm(l["name"])!=norm(meta[2]):
                metadata_rejected[meta[0]]+=1;continue
            if f["status"]["short"]!="NS":continue
            scheduled_seen[meta[0]]+=1
            k=identity(meta[0],row["teams"]["home"]["name"],row["teams"]["away"]["name"],f["date"])
            name=f.get("referee")
            if not isinstance(name,str) or norm(name) in ("","unknown","n a","na","tbd","none"):name=None
            candidates.setdefault(k,[]).append((i,name))
        except (ValueError,TypeError,KeyError,AttributeError):continue
    result=[]
    for code,_,_ in LEAGUES.values():
        diagnostics[code]=Counter()
    for k,events in targets.items():
        matches=candidates.get(k,[])
        c=diagnostics.setdefault(k[0],Counter())
        c["eligible"]+=1
        if len(events)!=1 or target_ids[(k[0],events[0])]!=1:
            c["ambiguous_target"]+=1;continue
        if len(matches)>1 or (matches and ids[matches[0][0]]!=1):
            c["ambiguous_provider"]+=1;continue
        if not matches:
            if any(x[:3]==k[:3] for x in candidates):
                reason="kickoff_difference"
            elif any(x[0]==k[0] and x[3]==k[3] for x in candidates):
                reason="same_time_team_identity_unresolved"
            elif scheduled_seen[k[0]]:
                reason="no_exact_fixture"
            elif metadata_rejected[k[0]]:
                reason="league_metadata_unverified"
            else:reason="no_scheduled_provider_rows"
            c[reason]+=1;continue
        pid,ref=matches[0]
        c["matched_with_referee" if ref else "matched_missing_referee"]+=1
        result.append(dict(league=k[0],eventId=events[0],providerId=pid,referee=ref,
                           status="source_observed" if ref else "missing_referee"))
    alias_pairs={};source_pairs={}
    alias_report=shadow_alias_candidates(targets,candidates,target_ids,ids,result,alias_pairs)
    source_report=source_name_evidence(targets,candidates,target_ids,ids,result,source_names,source_pairs)
    return dict(eligibleIdentities=len(targets),matched=len(result),
                withReferee=sum(x["referee"] is not None for x in result),rows=result,
                aliasShadow=alias_report,sourceNameShadow=source_report,
                combinedShadow=combined_evidence(alias_pairs,source_pairs,len(targets),len(result)),
                diagnostics=[dict(league=code,counts=dict(c),providerScheduledRows=scheduled_seen[code],
                                  metadataRejectedRows=metadata_rejected[code],publicSourceUnavailable=code in unavailable)
                             for code,c in sorted(diagnostics.items())],
                predictionsEnabled=False,decision="PAS",publicationAllowed=False)
