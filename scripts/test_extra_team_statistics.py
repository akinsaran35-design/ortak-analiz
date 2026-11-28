import unittest
from datetime import date
from extra_team_statistics import build_team_statistics

class TeamTests(unittest.TestCase):
    def test_orientation_and_cutoff(self):
        rows=[
            dict(date="2026-08-01",home="a",away="b",score=[2,0],stats={"corners":[5,2]}),
            dict(date="2026-08-02",home="b",away="a",score=[1,3],stats={"corners":[3,7]}),
            dict(date="2026-11-28",home="a",away="b",score=[99,0],stats={})]
        report=build_team_statistics(rows,date(2026,11,28))
        a=report["teams"][0]
        self.assertEqual(report["teamCount"],2)
        self.assertEqual(a["recent"]["wins"],2)
        self.assertEqual(a["recent"]["metrics"]["goals"]["forAverage"],2.5)
        self.assertEqual(a["away"]["metrics"]["corners"]["forAverage"],7)
        self.assertEqual(a["home"]["metrics"]["corners"]["againstAverage"],2)
        self.assertIsNone(a["recent"]["metrics"]["shots"]["forAverage"])
    def test_ambiguous_day_and_old_team(self):
        rows=[dict(date="2025-08-01",home="c",away="d",score=[0,0],stats={}),
              dict(date="2026-08-01",home="a",away="b",score=[1,0],stats={}),
              dict(date="2026-08-01",home="c",away="a",score=[1,0],stats={})]
        report=build_team_statistics(rows,date(2026,11,28))
        self.assertEqual(report["teamCount"],3)
        self.assertEqual(report["teams"][0]["recent"]["sample"],0)
        self.assertEqual(report["teams"][0]["recent"]["ambiguousDatesExcluded"],1)
    def test_empty(self):
        self.assertEqual(build_team_statistics([],date(2026,11,28))["teamCount"],0)

if __name__=="__main__":unittest.main()
