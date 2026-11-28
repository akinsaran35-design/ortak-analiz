"""V6.70 main cohort calibration review, read-only and never automatic approval."""
import copy,json
from datetime import datetime,timedelta,date
from pathlib import Path
from statistics import median
from main_ml_matched_comparison import build,PAIRS,LEDGER,META,VERSION,OLD,legacy_provenance
from extra_ml_prospective import read_json,write_json
from extra_model_review_gate import market_gate,STALE_DAYS,MAX_STALE_SHARE,MIN_BRIER_GAIN,MAX_ECE,MAX_LOGLOSS_DEGRADATION
from extra_prospective_reliability import MIN_BIN,aware
from extra_league_prospective import MIN_SETTLED,MIN_DATES
from extra_league_score_audit import MARKETS
from main_leagues_ml_settlement import CODES
from main_ml_timing_audit import cutoff_class
from results_source_pilot import TR

MIN_PAIR_COVERAGE=.8
LEAGUE_MIN_SETTLED=100
LEAGUE_MIN_DATES=15

def dual_gate(metrics,ready):
    if not ready:
        return dict(status="not_evaluated",checks={},versusLegacy=None,versusPoisson=None)
    legacy=market_gate(metrics["legacy"],metrics["candidate"],metrics["pairedBootstrap"])
    poisson=market_gate(metrics["poisson"],metrics["candidate"],metrics["pairedPoissonBootstrap"])
    checks=dict(legacyPass=legacy["status"]=="eligible_for_manual_review",
        poissonPass=poisson["status"]=="eligible_for_manual_review")
    return dict(status="eligible_for_manual_review" if all(checks.values()) else "retain_baseline",
        checks=checks,versusLegacy=legacy,versusPoisson=poisson)

def cutoff_screen(pairs,ledger,meta,now,provenance,keys,min_n,min_days):
    """A descriptive screen for newly documented calendar cutoffs, not identical input data."""
    locked=set(pairs["pairs"])&keys
    documented={k for k in locked if cutoff_class(pairs["pairs"][k],ledger["forecasts"][k]) in ("same_calendar_cutoff","different_calendar_cutoff")}
    same={k for k in documented if cutoff_class(pairs["pairs"][k],ledger["forecasts"][k])=="same_calendar_cutoff"}
    sub={**ledger,**{n:{k:v for k,v in ledger[n].items() if k in same} for n in ("forecasts","settlements","quarantine")}}
    sp={**pairs,"pairs":{k:v for k,v in pairs["pairs"].items() if k in same}}
    report=build(copy.deepcopy(sp),sub,meta,{},now)
    cutoff=now.date()-timedelta(days=STALE_DAYS)
    mature={k for k in documented if date.fromisoformat(ledger["forecasts"][k]["date"])<=cutoff}
    mature_same=mature&same
    unavailable={k for k in mature_same if k not in ledger["settlements"] or k in ledger["quarantine"]}
    coverage=len(mature_same)/len(mature) if mature else None
    stale=len(unavailable)/len(mature_same) if mature_same else None
    provenance_ready=bool(same) and all(provenance["perPair"][k]=="verified" for k in same)
    checks=dict(sample=report["validSettled"]>=min_n and report["dateBlocks"]>=min_days,
        matureDocumentedCoverage=coverage is not None and coverage>=MIN_PAIR_COVERAGE,
        completeResults=stale is not None and stale<=MAX_STALE_SHARE,legacyProvenance=provenance_ready)
    ready=all(checks.values())
    return dict(paired=len(locked),documented=len(documented),sameCutoffPairs=len(same),
        validSettled=report["validSettled"],pending=report["pending"],dateBlocks=report["dateBlocks"],
        matureDocumentedPairs=len(mature),matureSameCutoffPairs=len(mature_same),
        matureSameCutoffShareAmongDocumentedPairs=coverage,staleOrQuarantinedShare=stale,
        sampleMinimum=min_n,dateMinimum=min_days,checks=checks,descriptiveScreenReady=ready,
        markets={m:dual_gate(report["markets"][m],ready) for m in MARKETS},
        sameSourceDataEstablished=False,independentConfirmationRequired=True,automaticApproval=False)

def evaluate(pairs,ledger,meta,now,legacy=None):
    now=now.astimezone(TR)
    # Recompute from locked forecasts and verified outcomes, not a mutable summary.
    checked=copy.deepcopy(pairs)
    overall=build(checked,ledger,meta,{},now)
    if checked!=pairs:raise ValueError("unexpected pair mutation")
    provenance=legacy_provenance(pairs,ledger,legacy)
    cutoff=now.date()-timedelta(days=STALE_DAYS)
    def group_report(keys,report,min_n,min_days):
        locked=set(pairs["pairs"])&keys
        mature={k for k in keys if date.fromisoformat(ledger["forecasts"][k]["date"])<=cutoff}
        mature_pairs=mature&locked
        unavailable={k for k in mature_pairs if k not in ledger["settlements"] or k in ledger["quarantine"]}
        coverage=len(mature_pairs)/len(mature) if mature else None
        stale=len(unavailable)/len(mature_pairs) if mature_pairs else None
        sample=report["validSettled"]>=min_n and report["dateBlocks"]>=min_days
        complete=coverage is not None and coverage>=MIN_PAIR_COVERAGE and stale is not None and stale<=MAX_STALE_SHARE
        verified=sum(provenance["perPair"][k]=="verified" for k in locked)
        provenance_ready=provenance["sourceAvailable"] and bool(locked) and verified==len(locked)
        ready=sample and complete and provenance_ready
        timing=[abs((aware(ledger["forecasts"][k]["recordedAt"])-aware(pairs["pairs"][k]["legacyRecordedAt"])).total_seconds())/3600 for k in locked]
        markets={}
        for m in MARKETS:
            v=report["markets"][m]
            markets[m]=dict(legacyBrier=v["legacy"]["brier"],candidateBrier=v["candidate"]["brier"],
                legacyLogLoss=v["legacy"]["logLoss"],candidateLogLoss=v["candidate"]["logLoss"],
                legacyECE=v["legacy"]["ece10"],candidateECE=v["candidate"]["ece10"],
                poissonBrier=v["poisson"]["brier"],poissonLogLoss=v["poisson"]["logLoss"],poissonECE=v["poisson"]["ece10"],
                gate=dual_gate(v,ready))
        return dict(recorded=len(keys),paired=len(locked),validSettled=report["validSettled"],pending=report["pending"],
            dateBlocks=report["dateBlocks"],matureFixtures=len(mature),maturePairs=len(mature_pairs),maturePairCoverage=coverage,
            staleOrQuarantinedShare=stale,sampleTargetReached=sample,completenessReady=complete,
            legacyProvenanceReady=provenance_ready,legacyProvenanceVerified=verified,
            reviewScreenReady=ready,status="manual_review_screen" if ready else "collecting_data",
            medianAbsoluteForecastTimeGapHours=median(timing) if timing else None,markets=markets)
    all_keys=set(ledger["forecasts"])
    result=group_report(all_keys,overall,MIN_SETTLED,MIN_DATES)
    result["sameCalendarCutoffScreen"]=cutoff_screen(pairs,ledger,meta,now,provenance,all_keys,MIN_SETTLED,MIN_DATES)
    leagues={}
    for l in sorted(CODES):
        keys={k for k,f in ledger["forecasts"].items() if f["league"]==l}
        sub={**ledger,**{name:{k:v for k,v in ledger[name].items() if k in keys} for name in ("forecasts","settlements","quarantine")}}
        subpairs={**pairs,"pairs":{k:v for k,v in pairs["pairs"].items() if k in keys}}
        report=build(copy.deepcopy(subpairs),sub,meta,{},now)
        leagues[l]=group_report(keys,report,LEAGUE_MIN_SETTLED,LEAGUE_MIN_DATES)
        leagues[l]["sameCalendarCutoffScreen"]=cutoff_screen(pairs,ledger,meta,now,provenance,keys,LEAGUE_MIN_SETTLED,LEAGUE_MIN_DATES)
    return dict(version="6.70",reviewPolicyVersion="6.84",sameInformationCutoffEstablished=False,requiresBothBaselineScreens=True,legacyProvenanceCounts=provenance["counts"],legacySourceAvailable=provenance["sourceAvailable"],mode="manual_review_screen_only",cohortVersion=VERSION,
        modelSha256=meta["modelSha256"],overall=result,leagues=leagues,
        thresholds=dict(minimumSettled=MIN_SETTLED,minimumDates=MIN_DATES,leagueMinimumSettled=LEAGUE_MIN_SETTLED,
            leagueMinimumDates=LEAGUE_MIN_DATES,minimumMaturePairCoverage=MIN_PAIR_COVERAGE,staleDays=STALE_DAYS,
            maximumStaleShare=MAX_STALE_SHARE,minimumBrierGain=MIN_BRIER_GAIN,maximumECE=MAX_ECE,
            minimumBinSample=MIN_BIN,maximumLogLossDegradation=MAX_LOGLOSS_DEGRADATION),
        repeatedMonitoringDescriptiveOnly=True,forecastTimingMayDiffer=True,formalIndependentConfirmationRequired=True,
        automaticApproval=False,productionModelValidated=False,existingArchivesModified=False,updatedAt=now.isoformat())

def run():
    try:legacy=read_json(OLD)
    except (OSError,ValueError):legacy=None
    report=evaluate(read_json(PAIRS),read_json(LEDGER),read_json(META),datetime.now(TR),legacy=legacy)
    write_json(Path("main_ml_calibration_review.json"),report)
    print("MAIN_ML_REVIEW_670",json.dumps({k:v for k,v in report.items() if k!="leagues"}))
if __name__=="__main__":run()
