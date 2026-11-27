import unittest
from datetime import date
from prospective_history_coverage import coverage
class Tests(unittest.TestCase):
    def test_window_and_conflicts(self):
        def row(day,score):return dict(date=day,home="a",away="b",score=score)
        rows=[row("2025-06-30",[1,0]),row("2026-10-01",[1,0]),row("2026-10-01",[1,0]),row("2026-10-02",[2,0]),row("2026-10-02",[0,2]),row("2026-11-27",[1,0])]
        self.assertEqual(coverage(rows,"a",date(2026,11,27)),dict(sample=1,latest="2026-10-01",conflicts=1))
    def test_missing(self):
        self.assertEqual(coverage([],"a",date(2026,11,27)),dict(sample=0,latest=None,conflicts=0))
if __name__=="__main__":unittest.main()
