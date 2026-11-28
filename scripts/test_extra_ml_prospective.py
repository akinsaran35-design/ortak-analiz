import unittest,copy,json
from datetime import datetime,timedelta
from unittest.mock import patch
import extra_ml_prospective as engine
from results_source_pilot import TR
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
    def test_source_failure_isolated(self):
        now=datetime(2026,11,28,12,tzinfo=TR)
        leagues=[l for l,_ in engine.COMPETITIONS]
        blocked,offline=leagues[:2]
        inventory=dict(sources=[dict(league=blocked,error="OSError")],successfulSources=23,requestedSources=24)
        history=[dict(league=l) for l in leagues]
        def reader(url):
            if "/"+offline+"/" in url:raise OSError("offline")
            return json.dumps({"events":[]}).encode()
        def schedule(payload,league,started):
            return [dict(league=league,date=(started.date()+timedelta(days=1)).isoformat())]
        with patch.object(engine,"build",return_value=(inventory,history)),patch.object(engine,"scheduled_fixtures",side_effect=schedule):
            with self.assertRaises(ValueError):engine.collect_inputs(now,reader)
            rows,games,diag=engine.collect_inputs(now,reader,allow_partial=True)
        self.assertEqual(diag["excludedHistoricalLeagues"],[blocked])
        self.assertEqual(diag["sourceSuccessful"],23)
        self.assertEqual(len(diag["fixtureSourceFailures"]),engine.HORIZON)
        self.assertTrue(diag["partial"])
        self.assertFalse(any(r["league"]==blocked for r in rows))
        self.assertEqual(len(games),len(leagues)-2)
        self.assertFalse(any(r["league"] in (blocked,offline) for r in games))
    def test_real_catboost(self):
        train=[row("2024-06-30",i) for i in range(100)]
        keys=sorted(train[0]["features"])
        m=fit_frozen(train,keys)
        self.assertEqual(list(m.classes_),list(range(5)))
        self.assertAlmostEqual(sum(m.predict_proba(vector(train[:1],keys))[0]),1)
if __name__=="__main__":
    unittest.main()
