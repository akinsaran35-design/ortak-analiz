import unittest
from datetime import datetime,date,timedelta
from extra_ml_preflight import input_features,preflight
from extra_league_features import feature_rows
from extra_league_training_inventory import parse_season
from results_source_pilot import TR

class PreflightTests(unittest.TestCase):
    def setUp(self):
        self.now=datetime(2026,11,28,10,tzinfo=TR)
        self.rows=[dict(league="sco.1",date=(date(2026,11,17)+timedelta(days=i)).isoformat(),home="hearts",away="celtic",score=[2,1],stats={"shots":[10,5]},source="test",verification="single_source_only") for i in range(6)]
        self.fixture=dict(league="sco.1",date="2026-11-29",home="heart of midlothian",away="celtic",eventId="123",kickoff="2026-11-29T15:00:00+03:00")
        self.keys=set(feature_rows(self.rows)[0]["features"])
    def test_future_features_and_no_leakage(self):
        a,err=input_features(self.rows,self.fixture,self.now)
        self.assertIsNone(err)
        self.assertEqual(set(a["features"]),self.keys)
        self.assertEqual(a["features"]["home_last5_goals_for"],2)
        future=dict(self.rows[-1],date="2026-11-28",score=[99,99])
        self.assertEqual(input_features(self.rows+[future],self.fixture,self.now)[0],a)
        r=preflight(self.rows,[self.fixture],self.now,self.keys)
        self.assertEqual(r["eligibleFixtures"],1)
        self.assertEqual(r["forecastsRecorded"],0)
        self.assertFalse(r["modelFitted"])
    def test_identity_and_duplicates(self):
        ambiguous=dict(self.rows[0],home="heart of midlothian")
        self.assertEqual(input_features(self.rows+[ambiguous],self.fixture,self.now)[1],"unmatched_or_ambiguous_identity")
        self.assertEqual(preflight(self.rows,[self.fixture,self.fixture],self.now,self.keys)["eligibleFixtures"],0)
    def test_explicit_cutoff(self):
        raw=b"Date,HomeTeam,AwayTeam,FTHG,FTAG\n01/09/2026,A,B,2,0\n"
        self.assertEqual(len(parse_season(raw,"sco.1",2026,"test")[0]),0)
        self.assertEqual(len(parse_season(raw,"sco.1",2026,"test",end=date(2026,11,28))[0]),1)
if __name__=="__main__":
    unittest.main()
