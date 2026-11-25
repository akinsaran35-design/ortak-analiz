import unittest
import math
from dixon_coles import distribution, markets
class Tests(unittest.TestCase):
    def test_poisson(self):
        m=markets(1.5,1.2)
        self.assertAlmostEqual(m["over25"],1-math.exp(-2.7)*(1+2.7+2.7**2/2))
        self.assertAlmostEqual(m["btts"],(1-math.exp(-1.5))*(1-math.exp(-1.2)))
    def test_correction(self):
        p=distribution(1.5,1.2,-0.1)
        self.assertAlmostEqual(sum(p.values()),1)
        self.assertGreater(p[0,0],distribution(1.5,1.2)[0,0])
        self.assertAlmostEqual(markets(1.5,1.2,-0.1)["over25"],markets(1.5,1.2)["over25"])
    def test_invalid(self):
        with self.assertRaises(ValueError):
            distribution(4,4,1)
if __name__=="__main__":
    unittest.main()
