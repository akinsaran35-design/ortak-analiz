import unittest
from datetime import date,timedelta
from prospective_capture_window import identity,existing_identities,capture_status,HORIZON_DAYS

TODAY=date(2026,11,27)
class Tests(unittest.TestCase):
    def status(self,days,score=None,existing=None,blocked=None):
        return capture_status("en.1",TODAY+timedelta(days=days),"Man City","Arsenal",score,TODAY,existing or set(),blocked or set())
    def test_window(self):
        self.assertEqual(HORIZON_DAYS,14)
        for day in (1,7,8,14):self.assertEqual(self.status(day),"eligible")
        for day in (-1,0,15):self.assertEqual(self.status(day),"outside_future_window")
        self.assertEqual(self.status(1,[2,1]),"outside_future_window")
    def test_canonical_duplicate(self):
        r=dict(league="en.1",date="2026-11-28",home="Manchester City FC",away="Arsenal FC")
        ids=existing_identities({"a":r})
        self.assertEqual(self.status(1,existing=ids),"already_recorded")
        self.assertEqual(self.status(2,existing=ids),"eligible")
    def test_calendar_guard(self):
        self.assertEqual(self.status(1,blocked={("en.1","Man City","Arsenal","2026-11-28")}),"calendar_blocked")
    def test_distinct_teams(self):
        with self.assertRaises(ValueError):identity("en.1","2026-11-28","Man City","Manchester City FC")
if __name__=="__main__":unittest.main()
