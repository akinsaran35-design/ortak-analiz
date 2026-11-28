import copy,unittest
from test_extra_ml_preflight import PreflightTests
from extra_ml_prospective import capture,empty_ledger,venue_form_reference
from main_leagues_ml_settlement import shared_input_summary
from main_leagues_ml_prospective import VERSION
from same_source_venue_reference import reference,summarize,FIELD
class MainCohortTests(unittest.TestCase):
    def test_separate_cohort(self):
        f=PreflightTests();f.setUp()
        meta=dict(modelSha256="test",frozenAt="2026-11-28T09:00:00+03:00",featureKeys=sorted(f.keys))
        class Stub:
            def predict_proba(self,x):return [[.2,.2,.2,.2,.2] for _ in x]
        ledger=empty_ledger(meta,version=VERSION)
        from extra_league_score_audit import team_key
        self.assertEqual(capture(ledger,f.rows,[f.fixture],Stub(),meta,f.now,version=VERSION,identity_fn=team_key)[0],1)
        saved=copy.deepcopy(ledger)
        self.assertEqual(capture(ledger,f.rows,[f.fixture],Stub(),meta,f.now,version=VERSION,identity_fn=team_key)[0],0)
        self.assertEqual(ledger,saved)
        self.assertEqual(next(iter(ledger["forecasts"].values()))["policyVersion"],VERSION)
        with self.assertRaises(ValueError):capture(ledger,f.rows,[],Stub(),meta,f.now)
        self.assertNotIn(FIELD,next(iter(ledger["forecasts"].values())))
        self.assertEqual(capture(ledger,f.rows,[f.fixture],Stub(),meta,f.now,version=VERSION,identity_fn=team_key,reference_fn=reference)[0],0)
        self.assertEqual(ledger,saved)
        new=empty_ledger(meta,version=VERSION)
        self.assertEqual(capture(new,f.rows,[f.fixture],Stub(),meta,f.now,version=VERSION,identity_fn=team_key,reference_fn=reference)[0],1)
        row=next(iter(new["forecasts"].values()))
        self.assertEqual(row[FIELD]["featureFingerprint"],row["featureFingerprint"])
        self.assertEqual(row[FIELD]["historyThrough"],row["historyThrough"])
        report=summarize(new)
        self.assertEqual(report["recorded"],1)
        self.assertEqual(report["validSettled"],0)
        self.assertFalse(report["legacyV16Reproduction"])
        self.assertIsNone(report["markets"]["over15"]["candidate"]["brier"])
        row[FIELD]["probabilities"]["over15"]=.99
        with self.assertRaises(ValueError):summarize(new)
        # No backfilling of already recorded forecasts.
        capture(ledger,f.rows,[f.fixture],Stub(),meta,f.now,version=VERSION,identity_fn=team_key,shared_reference=True)
        self.assertEqual(ledger,saved)
        new=empty_ledger(meta,version=VERSION)
        self.assertEqual(capture(new,f.rows,[f.fixture],Stub(),meta,f.now,version=VERSION,identity_fn=team_key,shared_reference=True)[0],1)
        row=next(iter(new["forecasts"].values()))
        self.assertEqual(row["sharedInputReference"]["featureFingerprint"],row["featureFingerprint"])
        self.assertEqual(shared_input_summary(new)["pending"],1)
        self.assertFalse(shared_input_summary(new)["actualLegacyForecast"])
        k=next(iter(new["forecasts"]))
        new["settlements"][k]=dict(score=[2,1])
        self.assertEqual(shared_input_summary(new)["markets"]["over15"]["reference"]["n"],1)
        new["forecasts"][k]["sharedInputReference"]["featureFingerprint"]="bad"
        with self.assertRaises(ValueError):shared_input_summary(new)
    def test_venue_formula(self):
        features={}
        for side in ("home","away"):
            features.update({side+"Venue_last10_matches":5,side+"Venue_last10_goals_for":1.5,side+"Venue_last10_goals_against":1.5})
        ref=venue_form_reference(features)
        self.assertAlmostEqual(ref["over15"],.801)
        self.assertAlmostEqual(ref["over25"],.577)
        self.assertAlmostEqual(ref["btts"],.604)
    def test_venue_reference_fallback_and_invalid_history(self):
        features={}
        for side in ("home","away"):
            features.update({side+"Venue_last10_matches":4,side+"_last10_matches":10,side+"_last10_goals_for":1.5,side+"_last10_goals_against":1.5})
        self.assertEqual(venue_form_reference(features),dict(over15=.801,over25=.577,btts=.604))
        for key,invalid in (("homeVenue_last10_matches",True),("homeVenue_last10_matches",11),("away_last10_matches",11),("away_last10_matches",4),("away_last10_matches",5.5),("home_last10_goals_for",float("nan")),("home_last10_goals_against",-1)):
            with self.subTest(key=key,invalid=invalid):
                self.assertIsNone(venue_form_reference(dict(features,**{key:invalid})))
        del features["home_last10_goals_for"]
        self.assertIsNone(venue_form_reference(features))
if __name__=="__main__":unittest.main()
