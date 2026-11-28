"""V6.84 prospective venue-form reference on the exact ML capture history.
This is a new research comparator, not archived or reproduced V1.6 predictions.
"""
from collections import defaultdict
from datetime import date
from extra_league_training_inventory import deduplicate
from extra_league_score_audit import MARKETS,goal_probabilities,labels,paired_date_bootstrap
from extra_ml_prospective import digest
from extra_prospective_reliability import probabilities,reliability,aware
from results_source_pilot import TR

VERSION="6.84"
FIELD="sameSourceVenueReference"

def reference(history,fixture,now,info,identity_fn):
    cutoff=now.astimezone(TR).date().isoformat()
    league=fixture["league"]
    past,_,_=deduplicate([r for r in history if r["league"]==league and r["date"]<cutoff
        and r.get("verification")=="single_source_only"])
    if not past or max(r["date"] for r in past)!=info["historyThrough"]:
        raise ValueError("reference history mismatch")
    names={r[s] for r in past for s in ("home","away")}
    stats=[]
    for side in ("home","away"):
        matches={n for n in names if identity_fn(league,n)==fixture[side]}
        if len(matches)!=1:return None
        team=next(iter(matches))
        venue=[r for r in past if r[side]==team]
        all_games=[r for r in past if team in (r["home"],r["away"])]
        selected=venue if len(venue)>=5 else all_games
        if len(selected)<5:return None
        # Stable date/identity ordering, newest games first.
        selected=sorted(selected,key=lambda r:(r["date"],r["home"],r["away"]),reverse=True)[:10]
        goals=[(r["score"][0],r["score"][1]) if r["home"]==team else (r["score"][1],r["score"][0]) for r in selected]
        stats.append(dict(gf=sum(x[0] for x in goals)/len(goals),ga=sum(x[1] for x in goals)/len(goals),
            matches=len(goals),mode="venue" if len(venue)>=5 else "all_venues"))
    h,a=stats
    hg=max(.15,min(4,(h["gf"]+a["ga"])/2))
    ag=max(.15,min(4,(a["gf"]+h["ga"])/2))
    result=dict(version=VERSION,kind="same_source_venue_form_reference",historyCutoffExclusive=cutoff,
        historyThrough=info["historyThrough"],historyFingerprint=digest(past),historyRows=len(past),
        featureFingerprint=digest(info["features"]),probabilities=dict(zip(MARKETS,goal_probabilities(hg,ag))),
        expectedGoals=[hg,ag],samples=[h["matches"],a["matches"]],sampleModes=[h["mode"],a["mode"]])
    if not probabilities(result["probabilities"]):raise ValueError("invalid reference")
    return result

def valid_reference(f,r):
    try:
        return (r["version"]==VERSION and r["kind"]=="same_source_venue_form_reference"
            and r["historyCutoffExclusive"]==aware(f["recordedAt"]).date().isoformat()
            and r["historyThrough"]==f["historyThrough"]<r["historyCutoffExclusive"]
            and r["featureFingerprint"]==f["featureFingerprint"]
            and isinstance(r["historyFingerprint"],str) and len(r["historyFingerprint"])==64
            and all(c in "0123456789abcdef" for c in r["historyFingerprint"])
            and type(r["historyRows"]) is int and r["historyRows"]>=5
            and isinstance(r["samples"],list) and len(r["samples"])==2
            and all(type(n) is int and 5<=n<=10 for n in r["samples"])
            and isinstance(r["sampleModes"],list) and len(r["sampleModes"])==2
            and all(m in ("venue","all_venues") for m in r["sampleModes"])
            and isinstance(r["expectedGoals"],list) and len(r["expectedGoals"])==2
            and all(type(x) in (int,float) and .15<=x<=4 for x in r["expectedGoals"])
            and probabilities(r["probabilities"])
            and all(abs(p-r["probabilities"][m])<=1e-12 for m,p in zip(MARKETS,goal_probabilities(*r["expectedGoals"]))))
    except (KeyError,TypeError,ValueError,AttributeError,OverflowError):return False

def summarize(ledger):
    covered={k:f for k,f in ledger["forecasts"].items() if FIELD in f}
    if any(not valid_reference(f,f[FIELD]) for f in covered.values()):
        raise ValueError("invalid same-source reference")
    valid=[(f,ledger["settlements"][k]["score"]) for k,f in covered.items() if k in ledger["settlements"] and k not in ledger["quarantine"]]
    markets={}
    for i,m in enumerate(MARKETS):
        rows=[(f["date"],f[FIELD]["probabilities"][m],f["candidate"][m],labels(*s)[i]) for f,s in valid]
        blocks=defaultdict(list)
        for d,b,c,y in rows:blocks[d].append((b-y)**2-(c-y)**2)
        markets[m]=dict(reference=reliability([(b,y) for _,b,_,y in rows]),candidate=reliability([(c,y) for _,_,c,y in rows]),
            pairedBootstrap=paired_date_bootstrap(blocks))
    return dict(version=VERSION,mode="same_source_prospective_research_only",recorded=len(covered),
        olderForecastsWithoutReference=len(ledger["forecasts"])-len(covered),validSettled=len(valid),
        pending=sum(k not in ledger["settlements"] and k not in ledger["quarantine"] for k in covered),
        quarantined=sum(k in ledger["quarantine"] for k in covered),dateBlocks=len({f["date"] for f,_ in valid}),
        markets=markets,legacyV16Reproduction=False,automaticApproval=False,productionModelValidated=False)
