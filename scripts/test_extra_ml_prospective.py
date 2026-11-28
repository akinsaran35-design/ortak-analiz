import unittest,copy
from test_extra_ml_preflight import PreflightTests
from extra_ml_prospective import capture,empty_ledger,fit_frozen,training_snapshot,verify_training
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
    def test_training_provenance(self):
        from unittest.mock import patch
        rows=[row("2024-06-30",i) for i in range(100)]
        for i,r in enumerate(rows):
            r.update(league="en.1",date="2024-06-30",home=str(i),away="away")
            r["features"]={str(k):float(i+k) for k in range(119)}
        with patch("extra_ml_prospective.feature_rows",return_value=rows):
            train,keys,fp=training_snapshot([],100)
        meta=dict(featureKeys=keys,trainingFingerprint=fp)
        verify_training(meta,keys,fp)
        with patch("extra_ml_prospective.feature_rows",return_value=list(reversed(rows))):
            self.assertEqual(training_snapshot([],100)[2],fp)
        changed=copy.deepcopy(rows)
        changed[0]["features"]["0"]+=1
        with patch("extra_ml_prospective.feature_rows",return_value=changed):
            other=training_snapshot([],100)[2]
        self.assertNotEqual(fp,other)
        with self.assertRaises(ValueError):verify_training(meta,keys,other)
        with self.assertRaises(ValueError):verify_training(meta,list(reversed(keys)),fp)
if __name__=="__main__":
    unittest.main()
