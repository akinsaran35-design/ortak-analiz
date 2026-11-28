import copy,unittest
from test_extra_ml_preflight import PreflightTests
from extra_ml_prospective import capture,empty_ledger
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
if __name__=="__main__":unittest.main()
