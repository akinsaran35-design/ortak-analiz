"""V6.69 read-only paired comparison of frozen main ML and archived match-card v1.6.
Pairs are locked before kickoff, never created after outcomes are available."""
import json,copy
from datetime import datetime,date
from pathlib import Path
from collections import defaultdict,Counter
from league_config import FIXTURE_CODES
from main_leagues_ml_preflight import identity
from main_leagues_ml_prospective import LEDGER,META,VERSION
from main_leagues_ml_settlement import CODES
from extra_ml_settlement import validate
from extra_ml_prospective import read_json,write_json,digest
from extra_prospective_reliability import aware,probabilities,reliability
from extra_league_score_audit import MARKETS,labels,paired_date_bootstrap
from extra_league_prospective import MIN_SETTLED,MIN_DATES
from results_source_pilot import TR

PAIRS=Path("main_ml_matched_pairs.json")
OLD=Path("prediction_archive.json")
LEGACY_VERSION="1.6"
LEGACY_MARKETS=dict(over15="1.5 Üst",over25="2.5 Üst",btts="KG Var")

def legacy_entries(archive):
    groups=defaultdict(list)
    for key,row in archive.items():
        try:
            if key!=json.dumps([row["date"],row["league"],row["match"]],ensure_ascii=False):
                # Key formatting may vary; verify decoded identity instead.
                if json.loads(key)!=[row["date"],row["league"],row["match"]]:continue
            code=FIXTURE_CODES[row["league"]]
            h,a=row["match"].split(" – ")
            ident=(code,row["date"],identity(code,h),identity(code,a))
            groups[ident].append((key,row))
        except (ValueError,TypeError,KeyError,AttributeError):continue
    return groups

def legacy_prob(row):
    if row.get("modelVersion")!=LEGACY_VERSION:return None
    try:
        vals={m:row["markets"][name] for m,name in LEGACY_MARKETS.items()}
        if any(type(v) not in (float,int) for v in vals.values()):return None
        probs={m:v/100 for m,v in vals.items()}
        return probs if probabilities(probs) else None
    except (TypeError,KeyError):return None

def locked_legacy_identity(value):
    try:
        day,league,match=json.loads(value)
        code=FIXTURE_CODES[league]
        h,a=match.split(" – ")
        return code,day,identity(code,h),identity(code,a)
    except (ValueError,TypeError,KeyError,AttributeError):
        return None

def valid_legacy_timing(t,recorded_at,fixture_date):
    if not isinstance(t,dict) or t.get("version")!="6.82" or t.get("sameSourceDataEstablished") is not False:
        return False
    try:
        start=aware(t["generationStartedAt"])
        end=aware(t["generationCompletedAt"])
        recorded=aware(recorded_at)
        cutoff=date.fromisoformat(t["historyCutoffExclusive"])
        latest=date.fromisoformat(t["historyThrough"])
        return (start<=end<=recorded and latest<cutoff<date.fromisoformat(fixture_date)
            and start.date()==end.date()==cutoff)
    except (KeyError,TypeError,ValueError,AttributeError,OverflowError):
        return False

def legacy_provenance(pairs,ledger,legacy):
    """Check immutable forecast fields, not the mutable result field."""
    groups=legacy_entries(legacy) if isinstance(legacy,dict) else {}
    counts=Counter()
    per_pair={}
    for k,x in pairs["pairs"].items():
        f=ledger["forecasts"][k]
        matches=groups.get((f["league"],f["date"],f["home"],f["away"]),[])
        if not isinstance(legacy,dict):
            status="source_unavailable"
        elif len(matches)!=1:
            status="missing_or_ambiguous"
        else:
            lk,old=matches[0]
            status="verified" if (lk==x["legacyKey"] and old.get("recordedAt")==x["legacyRecordedAt"]
                and old.get("modelVersion")==x["legacyVersion"] and legacy_prob(old)==x["legacy"]
                and ("legacyTiming" not in x or old.get("forecastTiming")==x["legacyTiming"])) else "changed"
        counts[status]+=1
        per_pair[k]=status
    return dict(counts=dict(counts),perPair=per_pair,sourceAvailable=isinstance(legacy,dict))

def match_evidence(ledger,locked,provenance):
    rows=[]
    for key,forecast in sorted(ledger["forecasts"].items()):
        pair=locked.get(key)
        settlement=ledger["settlements"].get(key)
        quarantine=ledger["quarantine"].get(key)
        row={field:forecast[field] for field in ("league","date","home","away","eventId","kickoff","recordedAt","historyThrough","featureFingerprint")}
        row.update(resultStatus="pending",legacyProvenance=provenance.get(key),
            legacyRecordedAt=pair["legacyRecordedAt"] if pair else None,
            probabilities=dict(candidate=forecast["candidate"],poisson=forecast["poisson"],
                legacy=pair["legacy"] if pair else None),
            result=None,matchedSquaredErrors=None)
        if quarantine is not None:
            row.update(resultStatus="quarantined",quarantineReason=quarantine["reason"])
        elif settlement is not None:
            row["resultStatus"]="verified"
            row["result"]={field:settlement[field] for field in ("score","settledAt","sources")}
            row["result"]["sourceUrls"]=settlement.get("sourceUrls")
            if pair is not None and provenance.get(key)=="verified":
                outcomes=dict(zip(MARKETS,labels(*settlement["score"])))
                row["matchedSquaredErrors"]={
                    model:{market:(probabilities[market]-outcome)**2 for market,outcome in outcomes.items()}
                    for model,probabilities in row["probabilities"].items()
                }
        rows.append(row)
    return rows

def market_evidence_summary(rows,market):
    outcome_index=MARKETS.index(market)
    matched=[row for row in rows if row["matchedSquaredErrors"] is not None]
    dates=sorted({row["date"] for row in matched})
    counts=Counter(row["resultStatus"] for row in rows)
    models={}
    for model in ("legacy","poisson","candidate"):
        observations=[(row["probabilities"][model][market],labels(*row["result"]["score"])[outcome_index])
            for row in matched]
        metrics=reliability(observations)
        metrics["accuracyAtHalf"]=(sum((p>=.5)==bool(outcome) for p,outcome in observations)/len(observations)
            if observations else None)
        models[model]=metrics
    improvements={}
    for baseline in ("legacy","poisson"):
        blocks=defaultdict(list)
        for row in matched:
            errors=row["matchedSquaredErrors"]
            blocks[row["date"]].append(errors[baseline][market]-errors["candidate"][market])
        improvements[baseline]=paired_date_bootstrap(blocks) if blocks else None
    return dict(
        forecasts=len(rows),pending=counts["pending"],quarantined=counts["quarantined"],
        verifiedResults=counts["verified"],comparableResults=len(matched),matchDays=len(dates),
        firstMatchDate=dates[0] if dates else None,lastMatchDate=dates[-1] if dates else None,
        minimumSettled=MIN_SETTLED,minimumDates=MIN_DATES,
        sampleTargetReached=len(matched)>=MIN_SETTLED and len(dates)>=MIN_DATES,
        forecastTimingMayDiffer=True,automaticApproval=False,models=models,
        pairedBrierImprovement=improvements)

def build(pairs,ledger,meta,legacy,now):
    now=now.astimezone(TR)
    validate(ledger,meta,now,version=VERSION,codes=CODES)
    if pairs.get("version")!="6.69" or pairs.get("modelSha256")!=meta["modelSha256"] or not isinstance(pairs.get("pairs"),dict):
        raise ValueError("pair archive mismatch")
    locked=pairs["pairs"]
    groups=legacy_entries(legacy)
    excluded=Counter()
    added=0
    valid=[]
    pending=0
    seen_legacy=set()
    for k,f in sorted(ledger["forecasts"].items()):
        matches=groups.get((f["league"],f["date"],f["home"],f["away"]),[])
        if k not in locked:
            if k in ledger["quarantine"]:
                excluded["quarantined"]+=1;continue
            if now>=aware(f["kickoff"]) or k in ledger["settlements"]:
                excluded["pair_window_closed"]+=1;continue
            if len(matches)!=1:
                excluded["missing_or_ambiguous_legacy"]+=1;continue
            lk,old=matches[0]
            prob=legacy_prob(old)
            try: old_time=aware(old["recordedAt"])
            except (KeyError,ValueError,TypeError,AttributeError):
                excluded["invalid_legacy_timestamp"]+=1;continue
            if prob is None or not old_time<=now or old_time.date()>=aware(f["kickoff"]).date() or old.get("result") is not None:
                excluded["ineligible_legacy"]+=1;continue
            locked[k]=dict(legacyKey=lk,legacyVersion=LEGACY_VERSION,legacyRecordedAt=old["recordedAt"],legacy=prob,
                candidate=f["candidate"],forecastFingerprint=digest(f),pairedAt=now.isoformat())
            timing=old.get("forecastTiming")
            if valid_legacy_timing(timing,old["recordedAt"],f["date"]):
                locked[k]["legacyTiming"]=copy.deepcopy(timing)
                locked[k]["legacyTimingFingerprint"]=digest(timing)
            added+=1
        x=locked[k]
        if (x["forecastFingerprint"]!=digest(f) or x["candidate"]!=f["candidate"]
            or x["legacyVersion"]!=LEGACY_VERSION or not probabilities(x["legacy"])
            or locked_legacy_identity(x["legacyKey"])!=(f["league"],f["date"],f["home"],f["away"])
            or x["legacyKey"] in seen_legacy
            or aware(x["legacyRecordedAt"]).date()>=aware(f["kickoff"]).date()
            or not max(aware(f["recordedAt"]),aware(x["legacyRecordedAt"]))<=aware(x["pairedAt"])<=now
            or aware(x["pairedAt"])>=aware(f["kickoff"])):
            raise ValueError("locked pair integrity failure")
        if ("legacyTiming" in x or "legacyTimingFingerprint" in x) and (
            not valid_legacy_timing(x.get("legacyTiming"),x["legacyRecordedAt"],f["date"])
            or x.get("legacyTimingFingerprint")!=digest(x["legacyTiming"])):
            raise ValueError("locked legacy timing integrity failure")
        seen_legacy.add(x["legacyKey"])
        if k in ledger["quarantine"]:
            excluded["quarantined_pair"]+=1;continue
        if k not in ledger["settlements"]:
            pending+=1;continue
        # Outcomes come exclusively from the separately verified ML ledger.
        valid.append((f,x,ledger["settlements"][k]["score"]))
    if set(locked)-set(ledger["forecasts"]):raise ValueError("orphan pair")
    stats={}
    for i,m in enumerate(MARKETS):
        vals=[(f["date"],x["legacy"][m],x["candidate"][m],labels(*score)[i]) for f,x,score in valid]
        blocks=defaultdict(list)
        for day,b,c,y in vals:blocks[day].append((b-y)**2-(c-y)**2)
        stats[m]=dict(legacy=reliability([(b,y) for _,b,_,y in vals]),
            candidate=reliability([(c,y) for _,_,c,y in vals]),pairedBootstrap=paired_date_bootstrap(blocks))
        poisson_pairs=[(f["date"],f["poisson"][m],x["candidate"][m],labels(*score)[i]) for f,x,score in valid]
        poisson_blocks=defaultdict(list)
        for day,b,c,y in poisson_pairs:poisson_blocks[day].append((b-y)**2-(c-y)**2)
        stats[m]["poisson"]=reliability([(b,y) for _,b,_,y in poisson_pairs])
        stats[m]["pairedPoissonBootstrap"]=paired_date_bootstrap(poisson_blocks)
        stats[m]["identicalEvaluationSample"]=True
    dates=len({f["date"] for f,_,_ in valid})
    return dict(version="6.69",mode="matched_prospective_research_only",cohortVersion=VERSION,legacyVersion=LEGACY_VERSION,
        newPairs=added,paired=len(locked),validSettled=len(valid),pending=pending,excluded=dict(excluded),dateBlocks=dates,
        minimumSettled=MIN_SETTLED,minimumDates=MIN_DATES,sampleTargetReached=len(valid)>=MIN_SETTLED and dates>=MIN_DATES,
        forecastTimingMayDiffer=True,markets=stats,automaticApproval=False,productionModelValidated=False,existingArchivesModified=False,updatedAt=now.isoformat())

def run():
    ledger,meta=read_json(LEDGER),read_json(META)
    pairs=read_json(PAIRS) if PAIRS.exists() else dict(version="6.69",modelSha256=meta["modelSha256"],pairs={})
    legacy=read_json(OLD)
    report=build(pairs,ledger,meta,legacy,datetime.now(TR))
    provenance=legacy_provenance(pairs,ledger,legacy)
    report["matchEvidence"]=match_evidence(ledger,pairs["pairs"],provenance["perPair"])
    report["marketEvidenceSummaries"]={market:market_evidence_summary(report["matchEvidence"],market) for market in MARKETS}
    report["over25EvidenceSummary"]=report["marketEvidenceSummaries"]["over25"]
    write_json(PAIRS,pairs)
    write_json(Path("main_ml_matched_report.json"),report)
    print("MAIN_ML_MATCHED_669",json.dumps({k:v for k,v in report.items()
        if k not in ("markets","matchEvidence","over25EvidenceSummary","marketEvidenceSummaries")}))
if __name__=="__main__":run()
