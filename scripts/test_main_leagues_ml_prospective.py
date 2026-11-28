import copy,unittest
from test_extra_ml_preflight import PreflightTests
from extra_ml_prospective import capture,empty_ledger
from main_leagues_ml_prospective import VERSION
from main_ml_common_input_reference import reference
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
    def test_common_input_reference_new_only(self):
        f=PreflightTests();f.setUp()
        meta=dict(modelSha256="test",frozenAt="2026-11-28T09:00:00+03:00",featureKeys=sorted(f.keys))
        class Stub:
            def predict_proba(self,x):return [[.2,.2,.2,.2,.2] for _ in x]
        from extra_league_score_audit import team_key
        args=(f.rows,[f.fixture],Stub(),meta,f.now)
        ledger=empty_ledger(meta,version=VERSION)
        capture(ledger,*args,version=VERSION,identity_fn=team_key,research_reference=reference)
        row=next(iter(ledger["forecasts"].values()))
        ref=row["commonInputReference"]
        self.assertEqual(ref["featureFingerprint"],row["featureFingerprint"])
        self.assertFalse(ref["publishedLegacyReproduction"])
        self.assertFalse(ref["productionEnabled"])
        self.assertEqual(set(ref["probabilities"]),{"over15","over25","btts"})
        old=empty_ledger(meta,version=VERSION)
        capture(old,*args,version=VERSION,identity_fn=team_key)
        frozen=copy.deepcopy(old)
        self.assertEqual(capture(old,*args,version=VERSION,identity_fn=team_key,research_reference=reference)[0],0)
        self.assertEqual(old,frozen)
    def test_reference_formula_and_fallback(self):
        import math
        features={}
        for side in ("home","away"):
            for prefix,n in ((side+"Venue_last10",4),(side+"_last10",10)):
                features.update({prefix+"_matches":n,prefix+"_goals_for":1.5,prefix+"_goals_against":1.5})
        ref=reference(features)
        self.assertEqual(ref["sample"],{"home":10,"away":10})
        self.assertEqual(ref["venueSpecific"],{"home":False,"away":False})
        self.assertAlmostEqual(ref["probabilities"]["over15"],round(100*(1-4*math.exp(-3)),1)/100)
if __name__=="__main__":unittest.main()
