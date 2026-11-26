import unittest
from historical_archive_merge import merge
class TestMerge(unittest.TestCase):
    def test_conflict(self):
        a=dict(matchID=1,date="2026-01-01",ft=[1,0])
        b=dict(a,ft=[2,0])
        self.assertEqual(merge([a],[b],[],"2025-01-01","2027-01-01"),([],["1"]))
    def test_duplicate(self):
        a=dict(matchID=1,date="2026-01-01")
        self.assertEqual(merge([a],[a],[],"2025-01-01","2027-01-01"),([a],[]))
if __name__=="__main__": unittest.main()
