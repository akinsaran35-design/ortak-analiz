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
            self.assertEqual(v["baseline"]["n"],v["leagueReference"]["n"])
            self.assertAlmostEqual(v["leagueReference"]["brier"],baseline["metrics"][k]["referenceBrier"])
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
    def test_league_aggregates(self):
        rows=fixture()
        rows += [dict(r,matchID=1000+r["matchID"],league="M") for r in rows]
        report=multiyear(rows,date(2026,11,26))
        self.assertEqual(set(report["leagueAggregate"]),{"L","M"})
        for k,v in report["aggregate"].items():
            for name in ("baseline","venue","opponent","leagueReference"):
                parts=[q[k]["models"][name] for q in report["leagueAggregate"].values()]
                n=sum(m["n"] for m in parts)
                self.assertEqual(v[name]["n"],n)
                self.assertAlmostEqual(v[name]["brier"],sum(m["n"]*m["brier"] for m in parts)/n)
            self.assertFalse(report["leagueAggregate"]["L"][k]["sampleAdequateForDescription"])
        self.assertTrue(report["leagueSampleRule"]["descriptiveOnly"])

    def test_empty(self):
        report=multiyear([],date(2026,11,26))
        self.assertFalse(report["realBettingEnabled"])
        self.assertIsNone(report["aggregate"]["over15"]["brierImprovement"])
        self.assertIsNone(report["aggregate"]["over15"]["referenceImprovement"])

if __name__=="__main__": unittest.main()
