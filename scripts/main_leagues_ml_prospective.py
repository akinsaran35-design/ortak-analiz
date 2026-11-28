"""V6.67 frozen prospective research cohort for nine main leagues.
Independent file set; never replaces published match-card predictions."""
import json
from datetime import datetime
from pathlib import Path
from main_leagues_ml_preflight import collect,identity
from extra_ml_prospective import load_or_freeze,empty_ledger,capture,read_json,write_json
from results_source_pilot import TR
VERSION="6.67"
MODEL=Path("main_ml_frozen.cbm")
META=Path("main_ml_frozen_manifest.json")
LEDGER=Path("main_ml_prospective_ledger.json")
EXPECTED_TRAIN=2848

def run():
    started=datetime.now(TR)
    history,training,keys,games,source_count=collect(started)
    model,meta=load_or_freeze(history,model_path=MODEL,meta_path=META,ledger_path=LEDGER,
        version=VERSION,expected_train=EXPECTED_TRAIN)
    if meta["version"]!=VERSION or set(meta["featureKeys"])!=keys:
        raise ValueError("frozen main cohort mismatch")
    ledger=read_json(LEDGER) if LEDGER.exists() else empty_ledger(meta,version=VERSION)
    now=datetime.now(TR)
    if now.date()!=started.date():raise ValueError("date changed; rerun")
    added,excluded=capture(ledger,history,games,model,meta,now,version=VERSION,identity_fn=identity,shared_reference=True)
    write_json(LEDGER,ledger)
    report=dict(version=VERSION,mode="prospective_research_only",sourceSuccessful=source_count,
        trainingMatches=meta["trainingMatches"],featureCount=len(keys),modelSha256=meta["modelSha256"],
        trainingFingerprint=meta["trainingFingerprint"],frozenAt=meta["frozenAt"],
        fixturesChecked=len(games),newForecasts=added,recorded=len(ledger["forecasts"]),
        settled=len(ledger["settlements"]),excluded=excluded,modelFrozen=True,
        sharedInputReferenceRecords=sum("sharedInputReference" in f for f in ledger["forecasts"].values()),
        productionModelValidated=False,automaticApproval=False,existingOtherArchivesModified=False,
        updatedAt=now.isoformat())
    write_json(Path("main_ml_prospective_report.json"),report)
    print("MAIN_ML_PROSPECTIVE_667",json.dumps(report))
if __name__=="__main__":run()
