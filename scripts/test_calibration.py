import unittest
from calibration import report
class Tests(unittest.TestCase):
    def test_empty(self):
        self.assertIsNone(report({})["brier"])
    def test_verified(self):
        r={"candidate":0.8,"result":[2,1],"modelVersion":"4.4","recordedAt":"2026-01-01T12:00:00+03:00","date":"2026-01-02","league":"x","home":"a","away":"b"}
        x=report({"a":r,"duplicate":r,"pending":dict(r,result=None),"late":dict(r,recordedAt="2026-01-02T00:00:00+03:00")})
        self.assertEqual(x["tested"],1)
        self.assertAlmostEqual(x["brier"],0.04)
        self.assertAlmostEqual(x["ece"],0.2)
        self.assertFalse(x["realBettingEnabled"])
if __name__=="__main__":
    unittest.main()
