import copy,unittest
from test_extra_ml_preflight import PreflightTests
from extra_ml_prospective import capture,empty_ledger
from main_leagues_ml_prospective import VERSION
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
if __name__=="__main__":unittest.main()
