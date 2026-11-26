import unittest
from live_score_scenario import scenario
from dixon_coles import markets
from score_model import score_report
class Tests(unittest.TestCase):
    def test_start_matches_prematch(self):
        s=scenario([0,0],0,1.5,1.2)
        expected={**markets(1.5,1.2),**score_report(1.5,1.2)}
        for k in ("homeWin","draw","awayWin","over15","over25","btts"):
            self.assertAlmostEqual(s[k],expected[k],places=10)
    def test_end_deterministic(self):
        s=scenario([2,1],90,1.5,1.2)
        self.assertEqual([s[k] for k in ("homeWin","draw","awayWin","over15","over25","btts")],[1,0,0,1,1,1])
    def test_no_remaining_goals(self):
        s=scenario([0,0],45,0,0)
        self.assertEqual(s["draw"],1)
        self.assertEqual(s["over15"],0)
    def test_probability_and_symmetry(self):
        s=scenario([0,0],60,1.5,1.5)
        self.assertAlmostEqual(s["homeWin"],s["awayWin"])
        self.assertAlmostEqual(s["homeWin"]+s["draw"]+s["awayWin"],1)
        self.assertFalse(s["predictionsEnabled"])
        self.assertFalse(s["modelCalibrated"])
    def test_reject_invalid_inputs(self):
        for args in [([0,0],91,1,1),([0,0],True,1,1),([0,-1],30,1,1),([0,0],30,float("nan"),1),([0,0],30,5,1)]:
            with self.assertRaises(ValueError):scenario(*args)
if __name__=="__main__":unittest.main()
