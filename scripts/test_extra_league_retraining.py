import unittest
from extra_league_retraining import partition,evaluate,tune_weight,baseline,fit_predict

def row(day,i):
    ys=[(0,0,0),(1,0,0),(1,0,1),(1,1,0),(1,1,1)][i%5]
    return dict(date=day,league="sco.1",home=str(i),away="away",
        features=dict(leagueHomeGoals=1.5,leagueAwayGoals=1.2,extra=float(i%5)),
        labels=dict(zip(("over15","over25","btts"),ys)))

class RetrainingTests(unittest.TestCase):
    def test_dates_and_insufficient_data(self):
        rows=[row(d,0) for d in ("2025-07-01","2024-07-01","2024-06-30")]
        self.assertEqual([g[0]["date"] for g in partition(rows)],["2024-06-30","2024-07-01","2025-07-01"])
        self.assertEqual(evaluate(rows)["status"],"insufficient_data")
    def test_frozen_tuning(self):
        rows=[row(d,i) for d,n in (("2024-06-30",500),("2024-07-01",300),("2025-07-01",300)) for i in range(n)]
        def fit(train,tune,test,keys):
            self.assertEqual([len(g) for g in (train,tune,test)],[500,300,300])
            return [[baseline(r) for r in group] for group in (tune,test)]
        r=evaluate(rows,fit)
        self.assertEqual(r["selectedBlendWeight"],0)
        self.assertEqual(r["markets"]["over15"]["poisson"],r["markets"]["over15"]["blended"])
        self.assertFalse(r["productionModelValidated"])
    def test_real_model(self):
        train=[row("2024-06-30",i) for i in range(100)]
        pred,_=fit_predict(train,train[:5],train[:5],sorted(train[0]["features"]))
        self.assertEqual(len(pred),5)
        self.assertTrue(all(0<=p<=1 for r in pred for p in r))
        self.assertTrue(all(r[0]>=max(r[1:])-1e-9 for r in pred))
if __name__=="__main__":
    unittest.main()
