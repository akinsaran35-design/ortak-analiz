import unittest
from datetime import date
from h2h_pair_coverage import pairs
class Tests(unittest.TestCase):
    def test_pair(self):
        r=dict(date="2026-11-20",home="a",away="b",score=[2,1],stats={},competition="E0")
        s=dict(r,date="2026-11-21",home="b",away="a",competition="E1")
        p=pairs([r,r,s,dict(r,date="2026-11-27")],date(2026,11,27))["pairs"][0]
        self.assertEqual(p["sample"],2)
        self.assertEqual(p["ageDays"],6)
        self.assertEqual(p["competitions"],["E0","E1"])
        self.assertEqual(p["metrics"]["goals"]["totalMean"],3)
    def test_conflict(self):
        r=dict(date="2026-11-20",home="a",away="b",score=[2,1],stats={},competition="E0")
        self.assertEqual(pairs([r,dict(r,score=[1,1])],date(2026,11,27))["pairs"],[])
if __name__=="__main__":unittest.main()
