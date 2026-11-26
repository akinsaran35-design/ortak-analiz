import unittest
from historical_weighted import rates,weighted_average
class WeightedTests(unittest.TestCase):
    def test_constant(self):
        self.assertEqual(rates([(2,1,"home")]*5,[(1,2,"away")]*5),(2,1))
    def test_recency(self):
        self.assertGreater(weighted_average([(0,0,"home")]*5+[(4,0,"home")]*5,"home",0),2)
    def test_venue(self):
        h=[(4,0,"home"),(0,0,"away")]*5
        self.assertGreater(weighted_average(h,"home",0),weighted_average(h,"away",0))
    def test_missing(self):
        self.assertIsNone(rates([],[]))
if __name__=="__main__":
    unittest.main()
