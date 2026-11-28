"""V6.63 manual review screen for V6.59 ML cohort, no automatic approval."""
from datetime import datetime,date,timedelta
from pathlib import Path
import json
from extra_ml_prospective import LEDGER,META,read_json,write_json
from extra_ml_settlement import validate,summarize
from extra_model_review_gate import market_gate,STALE_DAYS,MAX_STALE_SHARE
from extra_league_score_audit import MARKETS
from results_source_pilot import TR

def assess(ledger,meta,now):
    now=now.astimezone(TR)
    validate(ledger,meta,now)
    r=summarize(ledger)
    mature=[k for k,f in ledger["forecasts"].items() if date.fromisoformat(f["date"])<=now.date()-timedelta(days=STALE_DAYS)]
    stale=sum(k not in ledger["settlements"] or k in ledger["quarantine"] for k in mature)
    share=stale/len(mature) if mature else None
    ready=r["sampleTargetReached"] and share is not None and share<=MAX_STALE_SHARE
    markets={}
    for k in MARKETS:
        q=r["markets"][k]
        markets[k]=market_gate(q["models"]["poisson"],q["models"]["candidate"],q["pairedBootstrap"]) if ready else dict(status="not_evaluated",checks={})
    return dict(version="6.63",cohortVersion="6.59",mode="manual_review_screen_only",modelSha256=meta["modelSha256"],
        recorded=r["recorded"],validSettled=r["validSettled"],pending=r["pending"],quarantined=r["quarantined"],dateBlocks=r["dateBlocks"],
        minimumSettled=r["minimumSettled"],minimumDates=r["minimumDates"],matureFixtures=len(mature),staleShare=share,
        reviewScreenReady=ready,markets=markets,status="manual_review_screen" if ready else "collecting_data",
        automaticApproval=False,productionModelValidated=False,formalIndependentConfirmationRequired=True,updatedAt=now.isoformat())

if __name__=="__main__":
    r=assess(read_json(LEDGER),read_json(META),datetime.now(TR))
    write_json(Path("extra_ml_review_gate.json"),r)
    print("ML_REVIEW_GATE_663",json.dumps(r))
