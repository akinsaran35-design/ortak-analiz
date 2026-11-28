"""V6.70 main cohort calibration review, read-only and never automatic approval."""
import copy,json
from datetime import datetime,timedelta,date
from pathlib import Path
from statistics import median
from main_ml_matched_comparison import build,PAIRS,LEDGER,META,VERSION
from extra_ml_prospective import read_json,write_json
from extra_model_review_gate import market_gate,STALE_DAYS,MAX_STALE_SHARE,MIN_BRIER_GAIN,MAX_ECE,MAX_LOGLOSS_DEGRADATION
from extra_prospective_reliability import MIN_BIN,aware
from extra_league_prospective import MIN_SETTLED,MIN_DATES
from extra_league_score_audit import MARKETS
from main_leagues_ml_settlement import CODES
from results_source_pilot import TR

MIN_PAIR_COVERAGE=.8
LEAGUE_MIN_SETTLED=100
LEAGUE_MIN_DATES=15

def evaluate(pairs,ledger,meta,now):
    now=now.astimezone(TR)
    # Recompute from locked forecasts and verified outcomes, not a mutable summary.
    checked=copy.deepcopy(pairs)
    overall=build(checked,ledger,meta,{},now)
    if checked!=pairs:raise ValueError("unexpected pair mutation")
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
        ready=sample and complete
        timing=[abs((aware(ledger["forecasts"][k]["recordedAt"])-aware(pairs["pairs"][k]["legacyRecordedAt"])).total_seconds())/3600 for k in locked]
        markets={}
        for m in MARKETS:
            v=report["markets"][m]
            markets[m]=dict(legacyBrier=v["legacy"]["brier"],candidateBrier=v["candidate"]["brier"],
                legacyLogLoss=v["legacy"]["logLoss"],candidateLogLoss=v["candidate"]["logLoss"],
                legacyECE=v["legacy"]["ece10"],candidateECE=v["candidate"]["ece10"],
                gate=market_gate(v["legacy"],v["candidate"],v["pairedBootstrap"]) if ready else dict(status="not_evaluated",checks={}))
        return dict(recorded=len(keys),paired=len(locked),validSettled=report["validSettled"],pending=report["pending"],
            dateBlocks=report["dateBlocks"],matureFixtures=len(mature),maturePairs=len(mature_pairs),maturePairCoverage=coverage,
            staleOrQuarantinedShare=stale,sampleTargetReached=sample,completenessReady=complete,
            reviewScreenReady=ready,status="manual_review_screen" if ready else "collecting_data",
            medianAbsoluteForecastTimeGapHours=median(timing) if timing else None,markets=markets)
    result=group_report(set(ledger["forecasts"]),overall,MIN_SETTLED,MIN_DATES)
    leagues={}
    for l in sorted(CODES):
        keys={k for k,f in ledger["forecasts"].items() if f["league"]==l}
        sub={**ledger,**{name:{k:v for k,v in ledger[name].items() if k in keys} for name in ("forecasts","settlements","quarantine")}}
        subpairs={**pairs,"pairs":{k:v for k,v in pairs["pairs"].items() if k in keys}}
        report=build(copy.deepcopy(subpairs),sub,meta,{},now)
        leagues[l]=group_report(keys,report,LEAGUE_MIN_SETTLED,LEAGUE_MIN_DATES)
    return dict(version="6.70",mode="manual_review_screen_only",cohortVersion=VERSION,
        modelSha256=meta["modelSha256"],overall=result,leagues=leagues,
        thresholds=dict(minimumSettled=MIN_SETTLED,minimumDates=MIN_DATES,leagueMinimumSettled=LEAGUE_MIN_SETTLED,
            leagueMinimumDates=LEAGUE_MIN_DATES,minimumMaturePairCoverage=MIN_PAIR_COVERAGE,staleDays=STALE_DAYS,
            maximumStaleShare=MAX_STALE_SHARE,minimumBrierGain=MIN_BRIER_GAIN,maximumECE=MAX_ECE,
            minimumBinSample=MIN_BIN,maximumLogLossDegradation=MAX_LOGLOSS_DEGRADATION),
        repeatedMonitoringDescriptiveOnly=True,forecastTimingMayDiffer=True,formalIndependentConfirmationRequired=True,
        automaticApproval=False,productionModelValidated=False,existingArchivesModified=False,updatedAt=now.isoformat())

def run():
    report=evaluate(read_json(PAIRS),read_json(LEDGER),read_json(META),datetime.now(TR))
    write_json(Path("main_ml_calibration_review.json"),report)
    print("MAIN_ML_REVIEW_670",json.dumps({k:v for k,v in report.items() if k!="leagues"}))
if __name__=="__main__":run()
