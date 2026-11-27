import unittest
from datetime import date
from league_average_research import summarize

class Tests(unittest.TestCase):
    def test_cutoff_duplicates_missing(self):
        row = dict(date="2026-11-26",home="a",away="b",score=[2,0],stats={"corners":[4,6],"halfTimeGoals":[1,0]})
        r = summarize([row,row,dict(row,date="2026-11-27")],date(2026,11,27))["metrics"]
        self.assertEqual(r["goals"]["sample"],1)
        self.assertEqual(r["corners"]["totalMean"],10)
        self.assertIsNone(r["yellowCards"]["totalMean"])
    def test_conflict(self):
        row = dict(date="2026-11-26",home="a",away="b",score=[2,0],stats={})
        r = summarize([row,dict(row,score=[1,0])],date(2026,11,27))
        self.assertEqual(r["conflicts"],1)
        self.assertEqual(r["metrics"]["goals"]["sample"],0)
if __name__ == "__main__":
    unittest.main()
