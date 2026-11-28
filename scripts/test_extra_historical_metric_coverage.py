import unittest
from datetime import datetime
from extra_historical_metric_coverage import build,LEAGUES

class CoverageTests(unittest.TestCase):
    def test_extra_leagues_and_missing_metrics(self):
        def reader(url):
            season=2000+int(url.split("/")[-2][:2])
            return ("Date,HomeTeam,AwayTeam,FTHG,FTAG,HTHG,HTAG,HC,AC\n"
                    f"01/08/{season},A,B,2,0,1,0,5,3\n"
                    f"02/08/{season},C,D,0,0,0,0,,\n").encode()
        report=build(datetime.fromisoformat("2026-11-28T14:00:00+03:00"),reader)
        self.assertEqual(report["configuredLeagues"],6)
        self.assertEqual(report["respondingLeagues"],6)
        self.assertEqual(report["historicalMatches"],72)
        self.assertFalse(report["predictionsEnabled"])
        for g in report["groups"]:
            self.assertEqual(len(g["seasons"]),6)
            self.assertEqual(g["aggregate"]["metrics"]["corners"]["sample"],6)
            self.assertEqual(g["aggregate"]["metrics"]["corners"]["missing"],6)
            self.assertIsNone(g["aggregate"]["metrics"]["yellowCards"]["totalAverage"])
    def test_outage_isolated(self):
        def reader(url):
            raise OSError("simulated outage")
        report=build(datetime.fromisoformat("2026-11-28T14:00:00+03:00"),reader)
        self.assertEqual(report["respondingLeagues"],0)
        self.assertEqual(report["historicalMatches"],0)
        self.assertTrue(all(len(g["sourceErrors"])==6 for g in report["groups"]))

if __name__=="__main__":unittest.main()
