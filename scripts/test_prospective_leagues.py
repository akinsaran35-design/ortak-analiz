import unittest,copy
from datetime import datetime,timezone
from prospective_leagues import build
class LeagueTests(unittest.TestCase):
    def test_partition(self):
        now=datetime(2026,11,30,18,tzinfo=timezone.utc)
        row=dict(league="en.2",date="2026-11-28",recordedAt="2026-11-26T12:00:00+00:00",result=[2,1],old=.6,candidate=.55,baseline=.5)
        archive={"a":row,"b":dict(row,league="de.1",result=None)}
        original=copy.deepcopy(archive)
        r=build(archive,now)
        self.assertEqual(archive,original)
        self.assertEqual(r["recorded"],2)
        self.assertEqual(len(r["leagues"]),9)
        self.assertEqual(r["leagues"]["en.2"]["markets"]["2.5 Üst"]["tested"],1)
        self.assertEqual(r["leagues"]["de.1"]["markets"]["2.5 Üst"]["pending"],1)
        self.assertEqual(r["leagues"]["en.2"]["markets"]["KG Var"]["legacyWithoutForecast"],1)
        self.assertFalse(r["leagues"]["en.2"]["markets"]["2.5 Üst"]["sampleAdequate"])
        self.assertFalse(r["realBettingEnabled"])
        self.assertAlmostEqual(r["leagues"]["en.2"]["markets"]["2.5 Üst"]["candidateMinusClassic"],.0425)
if __name__=="__main__":unittest.main()
