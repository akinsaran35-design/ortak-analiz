"""V6.71 descriptive timing sensitivity of locked forecast pairs.
Keep all forecasts immutable. Timing strata are not automatic model approvals."""
import copy,json
from datetime import datetime
from pathlib import Path
from collections import Counter
from main_ml_matched_comparison import build,PAIRS,LEDGER,META,VERSION
from extra_ml_prospective import read_json,write_json
from extra_prospective_reliability import aware
from extra_league_score_audit import MARKETS
from results_source_pilot import TR

BANDS=("within_24h","24_to_48h","over_48h")

def band(hours):
    h=abs(hours)
    return BANDS[0] if h<=24 else BANDS[1] if h<=48 else BANDS[2]

def audit(pairs,ledger,meta,now):
    now=now.astimezone(TR)
    checked=copy.deepcopy(pairs)
    build(checked,ledger,meta,{},now)
    if checked!=pairs:raise ValueError("unexpected mutation")
    grouped={b:set() for b in BANDS}
    direction=Counter()
    for k,x in pairs["pairs"].items():
        gap=(aware(ledger["forecasts"][k]["recordedAt"])-aware(x["legacyRecordedAt"])).total_seconds()/3600
        grouped[band(gap)].add(k)
        direction["candidate_later" if gap>0 else "legacy_later" if gap<0 else "same_time"]+=1
    result={}
    for b,keys in grouped.items():
        sub={**ledger,**{name:{k:v for k,v in ledger[name].items() if k in keys} for name in ("forecasts","settlements","quarantine")}}
        sp={**pairs,"pairs":{k:v for k,v in pairs["pairs"].items() if k in keys}}
        q=build(copy.deepcopy(sp),sub,meta,{},now)
        result[b]=dict(paired=q["paired"],validSettled=q["validSettled"],pending=q["pending"],dateBlocks=q["dateBlocks"],
            markets={m:dict(legacyBrier=q["markets"][m]["legacy"]["brier"],candidateBrier=q["markets"][m]["candidate"]["brier"],
                legacyLogLoss=q["markets"][m]["legacy"]["logLoss"],candidateLogLoss=q["markets"][m]["candidate"]["logLoss"],
                pairedBootstrap=q["markets"][m]["pairedBootstrap"]) for m in MARKETS})
    return dict(version="6.71",mode="descriptive_timing_sensitivity_only",cohortVersion=VERSION,
        modelSha256=meta["modelSha256"],paired=len(pairs["pairs"]),direction=dict(direction),bands=result,
        bandLimitsHours=[24,48],sameInformationCutoffEstablished=False,
        independentConfirmationRequired=True,automaticApproval=False,productionModelValidated=False,
        existingArchivesModified=False,updatedAt=now.isoformat())

def run():
    r=audit(read_json(PAIRS),read_json(LEDGER),read_json(META),datetime.now(TR))
    write_json(Path("main_ml_timing_audit.json"),r)
    print("MAIN_ML_TIMING_671",json.dumps({**r,"bands":{k:{a:b for a,b in v.items() if a!="markets"} for k,v in r["bands"].items()}}))
if __name__=="__main__":run()
