"""V6.68 two-source settlement of the separate nine-league research cohort."""
import json
from datetime import datetime
from pathlib import Path
from main_leagues_ml_prospective import VERSION,LEDGER,META
from main_leagues_ml_preflight import identity
from nine_league_results_pilot import SOURCES
from extra_ml_prospective import read_json,write_json
from extra_ml_settlement import settle,summarize
from results_source_pilot import TR,read
from same_source_venue_reference import summarize as summarize_reference
CODES={k:v[0] for k,v in SOURCES.items()}
ESPN={k:v[1] for k,v in SOURCES.items()}

def run(reader=read):
    now=datetime.now(TR)
    ledger,meta=read_json(LEDGER),read_json(META)
    if meta.get("version")!=VERSION:raise ValueError("manifest version mismatch")
    diagnostics={}
    added,errors=settle(ledger,meta,now,reader=reader,version=VERSION,codes=CODES,identity_fn=identity,espn_codes=ESPN,diagnostics=diagnostics)
    report=dict(summarize(ledger,version=VERSION),newSettlements=added,sourceErrors=errors,updatedAt=now.isoformat())
    report["version"]="6.68"
    report["diagnosticsVersion"]="6.78"
    report["sourceDiagnostics"]=diagnostics
    report["sameSourceVenueReference"]=summarize_reference(ledger)
    write_json(LEDGER,ledger)
    write_json(Path("main_ml_settlement_report.json"),report)
    print("MAIN_ML_SETTLEMENT_668",json.dumps({k:v for k,v in report.items() if k not in ("markets","sameSourceVenueReference")}))
if __name__=="__main__":run()
