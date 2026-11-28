"""Read-only review gate for V6.48 only; never grants production approval."""
import json,math
from datetime import datetime,date,timedelta
from pathlib import Path
from extra_prospective_reliability import audit,MIN_BIN
from extra_league_prospective import LEDGER,VERSION,MIN_SETTLED,MIN_DATES,summarize
from extra_league_score_audit import MARKETS
from results_source_pilot import TR

STALE_DAYS=7
MAX_STALE_SHARE=.05
MIN_BRIER_GAIN=.001
MAX_ECE=.05
MAX_LOGLOSS_DEGRADATION=0.0

def market_gate(baseline,candidate,bootstrap):
    b,q=baseline["brier"],candidate["brier"]
    interval=bootstrap.get("interval95")
    if b is None or q is None or interval is None:
        return dict(status="insufficient_evidence",checks={})
    checks=dict(brierGain=b-q>=MIN_BRIER_GAIN,
        descriptiveIntervalPositive=interval[0]>0,
        logLossNotWorse=candidate["logLoss"]<=baseline["logLoss"]+MAX_LOGLOSS_DEGRADATION,
        calibrationError=candidate["ece10"]<=MAX_ECE,
        supportedBins=all(g["n"]>=MIN_BIN for g in candidate["bins"] if g["n"]>0))
    return dict(status="eligible_for_manual_review" if all(checks.values()) else "retain_baseline",
        checks=checks,brierGain=b-q,descriptiveInterval95=interval)

def assess(ledger,now):
    now=now.astimezone(TR)
    r=audit(ledger,now)
    cutoff=now.date()-timedelta(days=STALE_DAYS)
    mature=stale=0
    if r["integrityPassed"]:
        for k,f in ledger["forecasts"].items():
            if date.fromisoformat(f["date"])<=cutoff:
                mature+=1
                if k not in ledger["settlements"] or k in ledger["quarantine"]:
                    stale+=1
    stale_share=stale/mature if mature else None
    sample_ready=r["sampleTargetReached"]
    completeness_ready=mature>0 and stale_share<=MAX_STALE_SHARE
    ready=r["integrityPassed"] and sample_ready and completeness_ready
    markets={m:dict(status="not_evaluated",checks={}) for m in MARKETS}
    if ready:
        prospective=summarize(ledger)
        for m in MARKETS:
            metrics=r["markets"][m]
            markets[m]=market_gate(metrics["poisson"],metrics["candidate"],prospective["markets"][m]["pairedBootstrap"])
    return dict(version="6.57",cohortVersion=VERSION,mode="manual_review_screen_only",
        recorded=r["recorded"],validSettled=r["validSettled"],validPending=r["validPending"],
        quarantined=r["quarantined"],dateBlocks=r["dateBlocks"],integrityPassed=r["integrityPassed"],
        matureFixtures=mature,staleOrQuarantined=stale,staleShare=stale_share,
        sampleTargetReached=sample_ready,completenessReady=completeness_ready,reviewScreenReady=ready,
        thresholds=dict(minimumSettled=MIN_SETTLED,minimumDates=MIN_DATES,staleDays=STALE_DAYS,
            maximumStaleShare=MAX_STALE_SHARE,minimumBrierGain=MIN_BRIER_GAIN,maximumECE=MAX_ECE,
            minimumBinSample=MIN_BIN,maximumLogLossDegradation=MAX_LOGLOSS_DEGRADATION),
        markets=markets,status="integrity_failure" if not r["integrityPassed"] else "manual_review_screen" if ready else "collecting_data",
        repeatedMonitoringDescriptiveOnly=True,formalIndependentConfirmationRequired=True,
        newerHistoricalModelsEvaluated=False,automaticApproval=False,productionModelValidated=False,
        existingArchivesModified=False)

if __name__=="__main__":
    ledger=json.loads(LEDGER.read_text(encoding="utf-8"))
    report=assess(ledger,datetime.now(TR))
    Path("extra_model_review_gate.json").write_text(json.dumps(report,indent=2)+"\n")
    print("MODEL_REVIEW_GATE_657",json.dumps(report))
    if not report["integrityPassed"]:
        raise SystemExit("ledger integrity failure")
