import unittest
from extra_league_historical_calibration import calibrate,fit_calibration,reliability,evaluate
from extra_league_retraining import baseline
from test_extra_league_retraining import row

class CalibrationTests(unittest.TestCase):
    def test_identity_and_monotonicity(self):
        self.assertEqual(calibrate(0,1,0),0)
        self.assertEqual(calibrate(1,1,0),1)
        vals=[calibrate(p,.75,.2) for p in (0,.1,.5,.9,1)]
        self.assertEqual(vals,sorted(vals))
        self.assertTrue(all(0<=p<=1 for p in vals))
    def test_fallback_and_reliability(self):
        self.assertEqual(fit_calibration([],[]),(1,0))
        r=reliability([(.2,0),(.8,1)])
        self.assertAlmostEqual(r["ece10"],.2)
        self.assertAlmostEqual(r["brier"],.04)
        self.assertEqual(sum(b["n"] for b in r["bins"]),2)
    def test_distinct_selection_calibration_and_test(self):
        rows=[row(d,i) for d,n in (("2024-06-30",500),("2024-07-01",300),("2025-01-01",300),("2025-07-01",300)) for i in range(n)]
        def fit(train,tune,test,keys):
            self.assertEqual([len(g) for g in (train,tune,test)],[500,600,300])
            return [[baseline(r) for r in g] for g in (tune,test)]
        r=evaluate(rows,{"catboost":fit})
        self.assertEqual([r[k] for k in ("selectionMatches","calibrationMatches","testMatches")],[300,300,300])
        self.assertEqual(r["selectedModel"],"poisson")
        self.assertFalse(r["independentValidation"])
        self.assertEqual(r["markets"]["over15"]["n"],300)
        self.assertEqual(evaluate(rows[:500])["status"],"insufficient_data")
if __name__=="__main__":
    unittest.main()
