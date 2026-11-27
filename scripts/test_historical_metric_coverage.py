import unittest
from datetime import datetime
from historical_metric_coverage import summarize,build
class Tests(unittest.TestCase):
    def test_missing_vs_zero(self):
        a=summarize([dict(score=[1,0],stats={"corners":[0,0],"halfTimeGoals":[0,0]}),dict(score=[2,1],stats={"halfTimeGoals":[1,1]})])
        self.assertEqual(a["metrics"]["corners"]["sample"],1)
        self.assertEqual(a["metrics"]["corners"]["missing"],1)
        self.assertEqual(a["metrics"]["corners"]["totalAverage"],0)
        self.assertEqual(a["metrics"]["yellowCards"]["sample"],0)
        self.assertIsNone(a["metrics"]["yellowCards"]["totalAverage"])
        self.assertEqual(a["metrics"]["secondHalfGoals"]["totalAverage"],1)
        self.assertEqual(a["halves"]["sample"],2)
    def test_consistency(self):
        a=summarize([dict(score=[0,0],stats={"halfTimeGoals":[1,0],"shots":[2,1],"shotsOnTarget":[3,1]})])
        self.assertEqual(a["issues"],{"halfTimeExceedsFinal":1,"shotsOnTargetExceedsShots":1})
        self.assertEqual(a["metrics"]["halfTimeGoals"]["sample"],0)
        self.assertEqual(a["metrics"]["shotsOnTarget"]["sample"],0)
    def test_season_coverage(self):
        def reader(url):
            y=2000+int(url.split("/")[-2][:2])
            return f"Date,HomeTeam,AwayTeam,FTHG,FTAG,HTHG,HTAG,HC,AC\n01/08/{y},A,B,1,0,0,0,3,4\n".encode()
        r=build(datetime.fromisoformat("2026-11-27T07:00:00+03:00"),reader)
        self.assertEqual(len(r["groups"]),9)
        self.assertTrue(all(g["aggregate"]["matches"]==6 and len(g["seasons"])==6 for g in r["groups"]))
        self.assertFalse(r["predictionsEnabled"])
    def test_empty(self):
        a=summarize([])
        self.assertEqual(a["matches"],0)
        self.assertIsNone(a["metrics"]["goals"]["coverage"])
if __name__=="__main__":unittest.main()
