"""Validate existing frozen model and ledger before independent outcome settlement."""
import hashlib,sys,json
from datetime import datetime
from pathlib import Path

def check(model,meta,ledger,now,version,codes):
    from extra_ml_settlement import validate
    from extra_ml_prospective import WEIGHT,EXPECTED_FEATURES
    if meta["version"]!=version or meta["weight"]!=WEIGHT or meta["modelSha256"]!=hashlib.sha256(model).hexdigest():
        raise ValueError("frozen cohort mismatch")
    keys=meta["featureKeys"]
    if not isinstance(keys,list) or len(keys)!=EXPECTED_FEATURES or len(set(keys))!=EXPECTED_FEATURES:
        raise ValueError("feature schema mismatch")
    validate(ledger,meta,now,version=version,codes=codes)

def run(cohort):
    from results_source_pilot import TR
    if cohort=="main":
        from main_leagues_ml_prospective import MODEL,META,LEDGER,VERSION
        from main_leagues_ml_settlement import CODES
    elif cohort=="extra":
        from extra_ml_prospective import MODEL,META,LEDGER,VERSION
        from extra_ml_settlement import CODES
    else:raise ValueError("unknown cohort")
    check(MODEL.read_bytes(),json.loads(META.read_text()),json.loads(LEDGER.read_text()),datetime.now(TR),VERSION,CODES)
    print("Frozen cohort integrity verified:",cohort)

if __name__=="__main__":run(sys.argv[1])
