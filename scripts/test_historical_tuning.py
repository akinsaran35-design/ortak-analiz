import unittest
from datetime import date
from historical_tuning import tune
class TestTuning(unittest.TestCase):
    def test_empty(self):
        r=tune([],date(2026,11,26))
        self.assertEqual(r["trials"],[])
        self.assertNotIn("selected",r)
        self.assertFalse(r["realBettingEnabled"])
if __name__=="__main__": unittest.main()
