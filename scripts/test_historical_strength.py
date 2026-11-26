import unittest
from historical_strength import rates
class StrengthTest(unittest.TestCase):
    def test_neutral(self):
        self.assertEqual(rates([(2,1,"home")]*5,[(1,2,"away")]*5,2,1),(2,1))
    def test_missing(self):
        self.assertIsNone(rates([],[],2,1))
if __name__=="__main__": unittest.main()
