import unittest
from datetime import date,datetime
from football_statistics_pilot import parse,describe,build
CSV=b"Date,HomeTeam,AwayTeam,FTHG,FTAG,HC,AC,HY,AY,HTHG,HTAG\n20/11/2026,A,B,2,1,5,3,2,1,1,0\n21/11/2026,B,A,0,1,4,6,,,0,0\n26/11/2026,A,B,9,0,99,99,9,9,9,0\n"
class Tests(unittest.TestCase):
    def test_orientation_missing_and_cutoff(self):
        rows,metrics,bad=parse(CSV,"en.1","soccer_epl",date(2026,11,26))
        self.assertEqual(len(rows),2)
        self.assertEqual(bad,0)
        self.assertNotIn("shots",metrics)
        r=describe(rows,"a")
        self.assertEqual(r["metrics"]["corners"],dict(sample=2,forAverage=5.5,againstAverage=3.5))
        self.assertEqual(r["metrics"]["yellowCards"]["sample"],1)
        self.assertIsNone(r["metrics"]["shots"]["forAverage"])
    def test_conflicting_duplicate(self):
        raw=CSV+b"20/11/2026,A,B,2,1,8,3,2,1,1,0\n"
        rows,_,bad=parse(raw,"en.1","soccer_epl",date(2026,11,26))
        self.assertEqual(len(rows),1)
        self.assertEqual(bad,1)
    def test_report(self):
        r=build({"upcoming":[{"date":"2026-11-27","league":"İngiltere Premier Lig","match":"A – B"}]},datetime.fromisoformat("2026-11-26T18:00:00+03:00"),lambda _:CSV)
        self.assertEqual(r["fixtureCount"],1)
        self.assertFalse(r["predictionsEnabled"])
if __name__=="__main__":unittest.main()
