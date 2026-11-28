import unittest
from main_ml_weight_research import select,assess
class WeightTests(unittest.TestCase):
    def test_select_tuning_only(self):
        sample=[("2025-01-01",(.5,.5,.5),(.9,.9,.9),(1,1,1))]
        self.assertEqual(select(sample)[0],1)
        self.assertEqual(select([("2025-01-01",(.5,.5,.5),(.5,.5,.5),(1,1,1))])[0],.5)
        self.assertEqual(select([("2025-01-01",(.5,.5,.5),(.5001,.5001,.5001),(1,1,1))])[0],.5)
        self.assertLess(assess(sample,1)["over15"]["tunedBlend"]["brier"],assess(sample,1)["over15"]["fixedBlend"]["brier"])
        with self.assertRaises(ValueError):select([])
if __name__=="__main__":unittest.main()
