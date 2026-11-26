import unittest
from datetime import date, timedelta
from historical_opponent import Strength, compare, multiyear
from historical_baseline import evaluate

def fixture():
    start=date(2026,1,1)
    return [dict(matchID=i,date=(start+timedelta(days=i*3)).isoformat(),
                 league="L",home="A" if i%2 else "B",away="B" if i%2 else "A",
                 ft=[i%4,(i+1)%3]) for i in range(100)]

class OpponentTest(unittest.TestCase):
    def test_neutral_and_venue(self):
        m=Strength()
        r=fixture()[0]
        self.assertEqual(m.expected(r),(1.5,1.2))
        m.update(r,m.exposure(r))
        self.assertNotEqual(m.factors("L","B","home"),(1,1))
        self.assertEqual(m.factors("L","B","away"),(1,1))
    def test_paired_and_baseline(self):
        rows=fixture()
        end=date(2026,11,26)
        report=compare(rows,end)
        self.assertTrue(report["metrics"])
        baseline=evaluate(rows,end)
        for k,v in report["metrics"].items():
            self.assertEqual(v["baseline"]["n"],v["opponent"]["n"])
            self.assertEqual(v["baseline"]["n"],v["venue"]["n"])
            self.assertAlmostEqual(v["baseline"]["brier"],baseline["metrics"][k]["brier"])
    def test_future_and_order(self):
        rows=fixture()
        end=date(2026,11,26)
        future=dict(rows[-1],matchID=999,date="2026-11-27",ft=[9,9])
        self.assertEqual(compare(rows,end),compare([future]+list(reversed(rows)),end))
    def test_same_day_frozen_exposures(self):
        m=Strength()
        a,b=fixture()[:2]
        b=dict(b,date=a["date"])
        exposures=[m.exposure(r) for r in (a,b)]
        self.assertEqual(exposures[0],exposures[1])
        m.update(a,exposures[0])
        m.update(b,exposures[1])
        self.assertEqual(m.history[("L",b["home"])][-1][3],1.5)
    def test_empty(self):
        report=multiyear([],date(2026,11,26))
        self.assertFalse(report["realBettingEnabled"])
        self.assertIsNone(report["aggregate"]["over15"]["brierImprovement"])

if __name__=="__main__": unittest.main()
