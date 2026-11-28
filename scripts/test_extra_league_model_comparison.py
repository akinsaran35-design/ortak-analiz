import unittest
from extra_league_model_comparison import compare,choose,alternative_fit
from extra_league_retraining import baseline
from test_extra_league_retraining import row

class ComparisonTests(unittest.TestCase):
    def test_safe_selection(self):
        tune=[row("2024-07-01",i) for i in range(300)]
        self.assertEqual(choose(tune,{"xgboost":[baseline(r) for r in tune]})[1:],("poisson",0))
        exact=[tuple(r["labels"][k] for k in ("over15","over25","btts")) for r in tune]
        self.assertEqual(choose(tune,{"catboost":exact})[1:],("catboost",1))
    def test_matched_dates_and_baseline(self):
        rows=[row(d,i) for d,n in (("2024-06-30",500),("2024-07-01",300),("2025-07-01",300)) for i in range(n)]
        def fit(train,tune,test,keys):
            self.assertEqual([len(g) for g in (train,tune,test)],[500,300,300])
            return [[baseline(r) for r in g] for g in (tune,test)]
        r=compare(rows,{k:fit for k in ("xgboost","lightgbm","catboost")})
        self.assertEqual(r["selectedModel"],"poisson")
        self.assertEqual(r["markets"]["over25"]["poisson"],r["markets"]["over25"]["selected"])
        self.assertFalse(r["independentValidation"])
    def test_real_alternatives(self):
        train=[row("2024-06-30",i) for i in range(100)]
        for name in ("lightgbm","catboost"):
            pred,_=alternative_fit(train,train[:5],train[:5],sorted(train[0]["features"]),name)
            self.assertEqual(len(pred),5)
            self.assertTrue(all(0<=p<=1 for r in pred for p in r))
            self.assertTrue(all(r[0]>=max(r[1:])-1e-9 for r in pred))
if __name__=="__main__":
    unittest.main()
