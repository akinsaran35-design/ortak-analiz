import unittest
from datetime import datetime
from tff_fixture_coverage_probe import compare,source_key,LEAGUE
NOW=datetime.fromisoformat("2026-11-27T08:00:00+03:00")
def fixture():
    return dict(updatedAt=NOW.isoformat(),upcoming=[dict(league=LEAGUE,date="2026-11-27",match="alanyaspor – konyaspor")])
def row():
    return dict(status="observed",kickoff="2026-11-27T20:00:00+03:00",clubs=[dict(label="CORENDON ALANYASPOR"),dict(label="TÜMOSAN KONYASPOR")])
class Tests(unittest.TestCase):
    def test_pair(self):
        self.assertEqual(compare(fixture(),[row()],NOW)[0]["comparison"],"pair_date_match")
    def test_absence(self):
        d=fixture();d["upcoming"][0]["match"]="goztepe – trabzonspor"
        self.assertEqual(compare(d,[row()],NOW)[0]["comparison"],"absent_from_daily")
    def test_outside_window(self):
        r=row();r["kickoff"]="2026-12-06T19:00:00+03:00"
        self.assertEqual(compare(fixture(),[r],NOW)[0]["comparison"],"outside_daily_window")
    def test_empty_window(self):
        d=fixture();d["upcoming"]=[]
        with self.assertRaises(ValueError):compare(d,[row()],NOW)
    def test_duplicate(self):
        self.assertEqual(compare(fixture(),[row(),row()],NOW)[1]["comparison"],"duplicate_official_pair")
    def test_no_fuzzy(self):
        self.assertIsNone(source_key("Gaziantepspor"))
    def test_stale(self):
        d=fixture();d["updatedAt"]="2026-11-26T08:00:00+03:00"
        with self.assertRaises(ValueError):compare(d,[row()],NOW)
if __name__=="__main__":unittest.main()
