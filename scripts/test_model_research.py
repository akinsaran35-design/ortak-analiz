import unittest
from model_research import build
class Tests(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(build({})["rows"],[])
    def test_invalid(self):
        self.assertEqual(build({"candidates":[{}]})["rejected"],1)
    def test_valid(self):
        r=build({"candidates":[{"date":"2026-11-25","league":"test","match":"A - B","expectedGoals":{"home":1.5,"away":1.2}}]})
        self.assertFalse(r["realBettingEnabled"])
        self.assertFalse(r["rhoFitted"])
        self.assertEqual(len(r["rows"]),1)
        self.assertAlmostEqual(r["rows"][0]["poisson"]["over25"],r["rows"][0]["experimentalDixonColes"]["over25"])
if __name__=="__main__":
    unittest.main()
