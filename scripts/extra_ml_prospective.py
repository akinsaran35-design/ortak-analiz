"""V6.59 prospective research cohort; frozen model, append-only forecasts, no production use."""
import json,hashlib,math
from collections import Counter
from datetime import datetime,timedelta
from pathlib import Path
from extra_league_training_inventory import build
from extra_league_features import feature_rows
from extra_league_retraining import vector,label,baseline,blend,TUNE_START
from extra_league_score_audit import MARKETS,score_class,xgb_market_probabilities,COMPETITIONS
from extra_league_prospective import key,scheduled_fixtures,HORIZON
from extra_ml_preflight import input_features
from extra_prospective_reliability import probabilities
from results_source_pilot import TR,read

VERSION="6.59"
MODEL=Path("extra_ml_frozen.cbm")
META=Path("extra_ml_frozen_manifest.json")
LEDGER=Path("extra_ml_prospective_ledger.json")
WEIGHT=.5
EXPECTED_TRAIN=1791
EXPECTED_FEATURES=119

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()

def read_json(p):
    return json.loads(p.read_text(encoding="utf-8"))

def write_json(p,value):
    p.write_text(json.dumps(value,ensure_ascii=False,indent=2,sort_keys=True,allow_nan=False)+"\n",encoding="utf-8")

def fit_frozen(train,keys):
    from catboost import CatBoostClassifier
    y=[score_class(label(r)) for r in train]
    if set(y)!=set(range(5)):
        raise ValueError("missing training class")
    model=CatBoostClassifier(loss_function="MultiClass",iterations=100,depth=3,learning_rate=.05,
        l2_leaf_reg=10,random_seed=653,thread_count=1,bootstrap_type="No",random_strength=0,
        allow_writing_files=False,verbose=False)
    model.fit(vector(train,keys),y)
    return model

def training_snapshot(history,expected_train):
    train=sorted(feature_rows([r for r in history if r["date"]<TUNE_START]),
        key=lambda r:(r["date"],r["league"],r["home"],r["away"]))
    if len(train)!=expected_train:
        raise ValueError("historical training count changed; review required")
    keys=sorted(train[0]["features"])
    if len(keys)!=EXPECTED_FEATURES or any(set(r["features"])!=set(keys) for r in train):
        raise ValueError("training schema changed")
    return train,keys,digest(train)

def verify_training(meta,keys,fingerprint):
    if meta.get("featureKeys")!=keys or meta.get("trainingFingerprint")!=fingerprint:
        raise ValueError("frozen training provenance changed; review required")

def load_or_freeze(history,model_path=MODEL,meta_path=META,ledger_path=LEDGER,now=None,version=VERSION,expected_train=EXPECTED_TRAIN,verify_history=True):
    from catboost import CatBoostClassifier,__version__
    now=(now or datetime.now(TR)).astimezone(TR)
    existing=(model_path.exists(),meta_path.exists())
    if any(existing) and not all(existing) or ledger_path.exists() and not all(existing):
        raise ValueError("partial frozen cohort; refuse replacement")
    if verify_history or not all(existing):
        train,keys,fingerprint=training_snapshot(history,expected_train)
    if all(existing):
        meta=read_json(meta_path)
        if (meta["version"]!=version or meta["weight"]!=WEIGHT or meta["catboostVersion"]!=__version__
            or meta["modelSha256"]!=hashlib.sha256(model_path.read_bytes()).hexdigest()
            or len(meta["featureKeys"])!=EXPECTED_FEATURES or len(set(meta["featureKeys"]))!=EXPECTED_FEATURES
            or meta["trainingMatches"]!=expected_train or meta["trainingCutoff"]!=TUNE_START):
            raise ValueError("frozen model mismatch")
        if verify_history:verify_training(meta,keys,fingerprint)
        model=CatBoostClassifier()
        model.load_model(str(model_path))
    else:
        model=fit_frozen(train,keys)
        model.save_model(str(model_path))
        meta=dict(version=version,model="catboost",weight=WEIGHT,catboostVersion=__version__,
            modelSha256=hashlib.sha256(model_path.read_bytes()).hexdigest(),trainingFingerprint=fingerprint,
            trainingMatches=len(train),trainingCutoff=TUNE_START,featureKeys=keys,
            frozenAt=now.isoformat(),trainingSourceVerification="single_source_only")
        write_json(meta_path,meta)
    if list(model.classes_)!=list(range(5)):
        raise ValueError("model class order mismatch")
    return model,meta

def empty_ledger(meta,version=VERSION):
    return dict(version=version,modelSha256=meta["modelSha256"],forecasts={},settlements={},quarantine={})

def venue_form_reference(features):
    """V1.6 formula adapted to the same feature vector, not a published V1.6 forecast."""
    rates=[]
    for side in ("home","away"):
        venue=side+"Venue_last10"
        all_venues=side+"_last10"
        venue_n=features.get(venue+"_matches")
        if type(venue_n) is not int or not 0<=venue_n<=10:
            return None
        prefix=venue if venue_n>=5 else all_venues
        n=features.get(prefix+"_matches")
        if type(n) is not int or not 5<=n<=10:
            return None
        gf,ga=(features.get(prefix+"_goals_"+x) for x in ("for","against"))
        if any(type(x) not in (int,float) or not math.isfinite(x) or x<0 for x in (gf,ga)):
            return None
        rates.append((gf,ga))
    h=max(.15,min(4.,(rates[0][0]+rates[1][1])/2))
    a=max(.15,min(4.,(rates[1][0]+rates[0][1])/2))
    total=h+a
    def over(n):
        return 1-sum(math.exp(-total)*total**k/math.factorial(k) for k in range(n+1))
    def rounded(x):return round(100*min(1,max(0,x)),1)/100
    return dict(over15=rounded(over(1)),over25=rounded(over(2)),
        btts=rounded((1-math.exp(-h))*(1-math.exp(-a))))

def capture(ledger,history,fixtures,model,meta,now,version=VERSION,identity_fn=None,reference_fn=None,shared_reference=False):
    now=now.astimezone(TR)
    if ledger.get("version")!=version or ledger.get("modelSha256")!=meta["modelSha256"] or any(not isinstance(ledger.get(k),dict) for k in ("forecasts","settlements","quarantine")):
        raise ValueError("cohort mismatch")
    frozen=datetime.fromisoformat(meta["frozenAt"])
    if frozen.tzinfo is None or frozen>now:
        raise ValueError("invalid freeze time")
    keys=meta["featureKeys"]
    existing={(r["league"],r["eventId"]) for r in ledger["forecasts"].values()}
    ids=Counter((r["league"],r["eventId"]) for r in fixtures)
    identities=Counter(key(r) for r in fixtures)
    excluded=Counter()
    added=0
    for f in sorted(fixtures,key=key):
        k=key(f)
        identity=(f["league"],f["eventId"])
        if k in ledger["forecasts"] or identity in existing:
            excluded["already_recorded"]+=1
            continue
        if ids[identity]!=1 or identities[k]!=1:
            excluded["duplicate_identity"]+=1
            continue
        info,reason=input_features(history,f,now,**({"identity_fn":identity_fn} if identity_fn is not None else {}))
        if reason:
            excluded[reason]+=1
            continue
        features=info["features"]
        if set(features)!=set(keys):
            excluded["feature_schema_mismatch"]+=1
            continue
        row=dict(features=features)
        p=baseline(row)
        q=xgb_market_probabilities(model.predict_proba(vector([row],keys))[0])
        models=dict(poisson=dict(zip(MARKETS,p)),catboost=dict(zip(MARKETS,q)),
            candidate=dict(zip(MARKETS,blend(p,q,WEIGHT))))
        if not all(probabilities(v) for v in models.values()):
            raise ValueError("incoherent forecast")
        ledger["forecasts"][k]=dict(f,**models,recordedAt=now.isoformat(),policyVersion=version,
            modelSha256=meta["modelSha256"],featureFingerprint=digest(features),featureCount=len(keys),
            historyThrough=info["historyThrough"],teamHistoryThrough=info["teamHistoryThrough"],
            trainingSourceVerification="single_source_only")
        if reference_fn is not None:
            ref=reference_fn(history,f,now,info,identity_fn)
            if ref is not None:
                ledger["forecasts"][k]["sameSourceVenueReference"]=ref
        if shared_reference:
            ref=venue_form_reference(features)
            if ref is not None:
                if not probabilities(ref):raise ValueError("incoherent shared-input reference")
                ledger["forecasts"][k]["sharedInputReference"]=dict(version="6.84",method="adapted_v1.6_venue_form",
                    featureFingerprint=digest(features),historyCutoffExclusive=now.date().isoformat(),probabilities=ref)
        existing.add(identity)
        added+=1
    return added,dict(excluded)

def collect_inputs(started,reader=read,allow_partial=False):
    inventory,history=build(reader=reader,end=started.date())
    failed=[s for s in inventory["sources"] if s["error"]]
    blocked={s["league"] for s in failed}
    if failed and not allow_partial:
        raise ValueError("incomplete historical inventory")
    history=[r for r in history if r["league"] not in blocked]
    fixtures=[]
    errors=[]
    requests=0
    for league,_ in COMPETITIONS:
        if league in blocked:continue
        for i in range(1,HORIZON+1):
            day=started.date()+timedelta(days=i)
            url=f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league}/scoreboard?dates={day:%Y%m%d}"
            requests+=1
            try:
                payload=json.loads(reader(url))
                if not isinstance(payload,dict):raise ValueError("fixture schema")
                fixtures.extend(f for f in scheduled_fixtures(payload,league,started) if f["date"]==day.isoformat())
            except (OSError,ValueError,TypeError,KeyError,AttributeError) as exc:
                errors.append(dict(league=league,date=day.isoformat(),error=type(exc).__name__))
    if errors and not allow_partial:raise ValueError("fixture source errors")
    return history,fixtures,dict(historySourceFailures=failed,fixtureSourceFailures=errors,
        excludedHistoricalLeagues=sorted(blocked),sourceSuccessful=inventory["successfulSources"],
        sourceRequested=inventory["requestedSources"],fixtureRequests=requests,
        fixtureSuccessful=requests-len(errors),partial=bool(failed or errors))

def run():
    started=datetime.now(TR)
    frozen=MODEL.exists() and META.exists()
    history,fixtures,diagnostics=collect_inputs(started,allow_partial=frozen)
    model,meta=load_or_freeze(history,verify_history=not diagnostics['historySourceFailures'])
    ledger=read_json(LEDGER) if LEDGER.exists() else empty_ledger(meta)
    now=datetime.now(TR)
    if now.date()!=started.date():
        raise SystemExit("date changed during collection; rerun")
    new,excluded=capture(ledger,history,fixtures,model,meta,now)
    write_json(LEDGER,ledger)
    report=dict(version=VERSION,mode="prospective_research_only",sourceDiagnostics=diagnostics,fixturesChecked=len(fixtures),newForecasts=new,
        recorded=len(ledger["forecasts"]),settled=len(ledger["settlements"]),excluded=excluded,
        modelFrozen=True,modelSha256=meta["modelSha256"],trainingMatches=meta["trainingMatches"],
        featureCount=len(meta["featureKeys"]),weights=dict(poisson=1-WEIGHT,catboost=WEIGHT),
        trainingSourceVerification="single_source_only",productionModelValidated=False,existingArchivesModified=False,
        updatedAt=now.isoformat())
    write_json(Path("extra_ml_prospective_report.json"),report)
    print("ML_PROSPECTIVE_659",json.dumps(report))
if __name__=="__main__":
    run()
