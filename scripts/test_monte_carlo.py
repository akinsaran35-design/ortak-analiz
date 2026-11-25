import unittest
from monte_carlo import simulate
from dixon_coles import markets

class Tests(unittest.TestCase):
    def test_reproducible(self):
        self.assertEqual(simulate(1.5,1.2,trials=1000),simulate(1.5,1.2,trials=1000))
    def test_convergence(self):
        for rho in (0,-0.1):
            result=simulate(1.5,1.2,rho,trials=50000)
            for k,p in markets(1.5,1.2,rho).items():
                self.assertLess(abs(result["markets"][k]["probability"]-p),0.015)
    def test_invalid(self):
        with self.assertRaises(ValueError):
            simulate(1,1,trials=0)
if __name__=="__main__":
    unittest.main()
