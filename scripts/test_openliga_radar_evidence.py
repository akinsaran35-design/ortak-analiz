import unittest
from datetime import datetime
from openliga_radar_evidence import inspect,probe
NOW=datetime.fromisoformat("2026-11-28T15:00:00+00:00")
def fixture(**kw):
    return dict(dict(matchID=1,matchDateTimeUTC="2026-11-28T14:00:00Z",matchIsFinished=False,
        team1={"teamId":1},team2={"teamId":2},goals=[{"goalID":1}]),**kw)
class Tests(unittest.TestCase):
    def test_window_not_live(self):
        r=inspect([fixture()],NOW)
        self.assertEqual(r["unfinishedKickoffWindow"],1)
        self.assertEqual(r["candidatesWithGoalEntries"],1)
        self.assertFalse(r["actualLiveStatusVerified"])
        self.assertFalse(r["liveScoreVerified"])
    def test_duplicate_and_finished(self):
        self.assertEqual(inspect([fixture(),fixture()],NOW)["unfinishedKickoffWindow"],0)
        self.assertEqual(inspect([fixture(matchIsFinished=True)],NOW)["unfinishedKickoffWindow"],0)
        self.assertEqual(inspect([fixture(matchDateTimeUTC="2026-11-28T16:00:00Z")],NOW)["unfinishedKickoffWindow"],0)
    def test_one_request_per_league(self):
        urls=[]
        def read(url):
            urls.append(url);return [fixture()]
        r=probe(NOW,read)
        self.assertEqual(len(set(urls)),3)
        self.assertFalse(r["predictionsEnabled"])
        self.assertEqual(r["license"],"ODbL-1.0")
if __name__=="__main__":unittest.main()
