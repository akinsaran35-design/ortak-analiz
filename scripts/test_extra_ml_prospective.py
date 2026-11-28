import unittest,copy
from test_extra_ml_preflight import PreflightTests
from extra_ml_prospective import capture,empty_ledger,fit_frozen
from test_extra_league_retraining import row
from extra_league_retraining import vector

class CaptureTests(unittest.TestCase):
    def test_frozen_and_append_only(self):
        f=PreflightTests()
        f.setUp()
        meta=dict(modelSha256="test-hash",frozenAt="2026-11-28T09:00:00+03:00",featureKeys=sorted(f.keys))
        class Stub:
            def predict_proba(self,x):
                return [[.2,.2,.2,.2,.2] for _ in x]
        ledger=empty_ledger(meta)
        self.assertEqual(capture(ledger,f.rows,[f.fixture],Stub(),meta,f.now)[0],1)
        frozen=copy.deepcopy(ledger)
        self.assertEqual(capture(ledger,f.rows,[f.fixture],Stub(),meta,f.now)[0],0)
        self.assertEqual(ledger,frozen)
        with self.assertRaises(ValueError):
            capture(ledger,f.rows,[],Stub(),dict(meta,modelSha256="changed"),f.now)
    def test_real_catboost(self):
        train=[row("2024-06-30",i) for i in range(100)]
        keys=sorted(train[0]["features"])
        m=fit_frozen(train,keys)
        self.assertEqual(list(m.classes_),list(range(5)))
        self.assertAlmostEqual(sum(m.predict_proba(vector(train[:1],keys))[0]),1)
if __name__=="__main__":
    unittest.main()
