import unittest
from score_model import score_report
class Tests(unittest.TestCase):
    def test_mass(self):
        r=score_report(1.5,1.2,-0.05)
        self.assertAlmostEqual(r["homeWin"]+r["draw"]+r["awayWin"],1)
        self.assertAlmostEqual(r["expectedHome"],1.5)
        self.assertAlmostEqual(r["expectedAway"],1.2)
        self.assertEqual(len(r["topScores"]),3)
        p=[x["probability"] for x in r["topScores"]]
        self.assertEqual(p,sorted(p,reverse=True))
        self.assertAlmostEqual(sum(p),r["topScoresCombined"])
    def test_symmetry(self):
        r=score_report(1,1)
        self.assertAlmostEqual(r["homeWin"],r["awayWin"])
if __name__=="__main__":
    unittest.main()
