import unittest
from historical_roi import evaluate
class TestROI(unittest.TestCase):
    def test_roi(self):
        a=dict(matchID=1,market="over15",probability=.8,odds=1.5,outcome=1,verified=True,predictionAt="2026-01-01T10:00:00Z",oddsAt="2026-01-01T11:00:00Z",kickoff="2026-01-01T12:00:00Z")
        self.assertEqual(evaluate([a,a])["roi"],.5)
        self.assertIsNone(evaluate([a,dict(a,outcome=0)])["roi"])
        self.assertEqual(evaluate([dict(a,oddsAt="2026-01-01T11:00:00")])["rejected"],1)
        self.assertEqual(evaluate([dict(a,oddsAt=a["kickoff"])])["rejected"],1)
if __name__=="__main__": unittest.main()
