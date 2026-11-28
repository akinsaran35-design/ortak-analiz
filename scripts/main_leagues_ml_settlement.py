"""V6.68 two-source settlement of the separate nine-league research cohort."""
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from main_leagues_ml_prospective import VERSION,LEDGER,META
from main_leagues_ml_preflight import identity
from nine_league_results_pilot import SOURCES
from extra_ml_prospective import read_json,write_json
from extra_ml_settlement import settle,summarize
from results_source_pilot import TR,read
from same_source_venue_reference import summarize as summarize_reference
from extra_prospective_reliability import aware,probabilities,reliability
from extra_league_score_audit import MARKETS,labels,paired_date_bootstrap
CODES={k:v[0] for k,v in SOURCES.items()}
ESPN={k:v[1] for k,v in SOURCES.items()}

def shared_input_summary(ledger):
    """Only records with a reference created at original capture; no retrospective fill."""
    recorded=0
    valid=[]
    pending=0
    quarantined=0
    for k,f in ledger["forecasts"].items():
        if "sharedInputReference" not in f:continue
        ref=f["sharedInputReference"]
        if (not isinstance(ref,dict) or ref.get("version")!="6.84" or ref.get("method")!="adapted_v1.6_venue_form"
            or ref.get("featureFingerprint")!=f["featureFingerprint"]
            or ref.get("historyCutoffExclusive")!=aware(f["recordedAt"]).date().isoformat()
            or not probabilities(ref.get("probabilities"))):
            raise ValueError("invalid shared-input reference")
        recorded+=1
        if k in ledger["quarantine"]:quarantined+=1;continue
        if k not in ledger["settlements"]:pending+=1;continue
        valid.append((f,ref["probabilities"],ledger["settlements"][k]["score"]))
    markets={}
    for i,m in enumerate(MARKETS):
        rows=[(f["date"],ref[m],f["candidate"][m],labels(*score)[i]) for f,ref,score in valid]
        blocks=defaultdict(list)
        for day,b,c,y in rows:blocks[day].append((b-y)**2-(c-y)**2)
        markets[m]=dict(reference=reliability([(b,y) for _,b,_,y in rows]),
            candidate=reliability([(c,y) for _,_,c,y in rows]),pairedBootstrap=paired_date_bootstrap(blocks))
    return dict(version="6.84",recorded=recorded,validSettled=len(valid),pending=pending,quarantined=quarantined,
        dateBlocks=len({f["date"] for f,_,_ in valid}),markets=markets,actualLegacyForecast=False,
        sharedFeatureVectorAtCapture=True,independentConfirmationRequired=True,automaticApproval=False)

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
    report["sharedInputReference"]=shared_input_summary(ledger)
    write_json(LEDGER,ledger)
    write_json(Path("main_ml_settlement_report.json"),report)
    print("MAIN_ML_SETTLEMENT_668",json.dumps({k:v for k,v in report.items() if k not in ("markets","sameSourceVenueReference")}))
if __name__=="__main__":run()
