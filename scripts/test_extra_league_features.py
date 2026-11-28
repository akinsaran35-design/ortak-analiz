import unittest
from datetime import date,timedelta
from extra_league_training_inventory import parse_season
from extra_league_features import feature_rows,report

class FeatureTests(unittest.TestCase):
    def test_stats_missing_and_invalid(self):
        raw=b"Date,HomeTeam,AwayTeam,FTHG,FTAG,HS,AS,HST,AST,HC,AC\n01/08/2023,A,B,2,0,10,4,11,2,3,4\n"
        rows,_=parse_season(raw,"sco.1",2023,"source")
        self.assertEqual(rows[0]["stats"]["shots"],[10,4])
        self.assertNotIn("shotsOnTarget",rows[0]["stats"])
    def test_past_only(self):
        rows=[dict(league="sco.1",date=(date(2023,8,1)+timedelta(days=i)).isoformat(),home="a",away="b",score=[2,1],stats={"shots":[10,5]},source="test",verification="single_source_only") for i in range(6)]
        a=feature_rows(rows)
        self.assertEqual(len(a),1)
        self.assertEqual(a[0]["features"]["home_last5_goals_for"],2)
        self.assertEqual(a[0]["features"]["away_last5_goals_for"],1)
        self.assertEqual(a[0]["features"]["home_last5_shots_for"],10)
        self.assertIsNone(a[0]["features"]["home_last5_shotsOnTarget_for"])
        revised=[dict(r) for r in rows]
        revised[-1]["score"]=[9,9]
        revised[-1]["stats"]={"shots":[99,99]}
        self.assertEqual(feature_rows(revised)[0]["features"],a[0]["features"])
        same_day=dict(rows[-1],home="b",away="a",score=[8,8])
        self.assertEqual(feature_rows(rows+[same_day])[0]["features"],a[0]["features"])
        r,_=report(rows,{"successfulSources":1})
        self.assertFalse(r["usedForTraining"])
        self.assertFalse(r["xgIncluded"])
        self.assertEqual(r["independentlyVerified"],0)
if __name__=="__main__":
    unittest.main()
