import unittest
from unittest.mock import patch
from main_leagues_ml_research import evaluate
class MainLeagueTests(unittest.TestCase):
    def test_insufficient(self):
        with self.assertRaises(ValueError):evaluate([])
    def test_fixed_policy(self):
        features={str(i):0 for i in range(119)}
        row=lambda day:dict(date=day,league="en.1",home="a",away="b",features=features)
        groups=[[row("2024-06-30")]*500,[row("2025-06-30")]*300,[row("2025-07-01")]*300]
        with patch("main_leagues_ml_research.feature_rows",return_value=[]),patch("main_leagues_ml_research.partition",return_value=groups),patch("main_leagues_ml_research.metrics",return_value={}) as m:
            def fit(train,tune,test,keys,name):
                self.assertEqual(name,"catboost")
                return [],[(.7,.5,.4)]*len(test)
            r=evaluate([],fit)
            self.assertEqual(r["featureCount"],119)
            self.assertEqual(m.call_args.args[-1],.5)
if __name__=="__main__":unittest.main()
