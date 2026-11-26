import unittest
from datetime import date,timedelta
from historical_baseline import evaluate
class ComparisonTests(unittest.TestCase):
    def test_same_sample(self):
        today=date(2026,11,26)
        rows=[dict(date=(today-timedelta(days=i)).isoformat(),league="test",home="A",away="B",ft=[i%4,1]) for i in range(360,0,-3)]
        a=evaluate(rows,today)
        b=evaluate(rows,today,weighted=True)
        self.assertGreater(a["metrics"]["over15"]["n"],0)
        self.assertEqual(a["metrics"]["over15"]["n"],b["metrics"]["over15"]["n"])
if __name__=="__main__": unittest.main()
