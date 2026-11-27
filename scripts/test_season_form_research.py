import unittest
from datetime import date
from season_form_research import profile
class Tests(unittest.TestCase):
    def test_windows(self):
        rows=[dict(date=f"2026-11-{i:02d}",home="a",away="b",score=[i,0],stats={}) for i in range(1,12)]
        r=profile(rows+rows[:1],date(2026,11,11))
        a=next(t for t in r["teams"] if t["team"]=="a")
        self.assertEqual(a["windows"]["5"]["metrics"]["goals"]["homeMean"],8)
        self.assertEqual(a["windows"]["20"]["metrics"]["goals"]["sample"],10)
        self.assertEqual(a["latest"],"2026-11-10")
        self.assertEqual(r["seasons"]["2026"]["metrics"]["goals"]["sample"],10)
if __name__=="__main__":unittest.main()
