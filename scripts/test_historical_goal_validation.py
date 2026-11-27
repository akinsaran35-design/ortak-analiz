import unittest,copy
from datetime import date,datetime
from historical_goal_validation import replay,progress
from results_source_pilot import TR

def fixture(d,h="a",a="b",score=None):
    return dict(date=d,home=h,away=a,score=score or [2,1])
class Tests(unittest.TestCase):
    def test_same_day_excluded(self):
        rows=[fixture("2026-08-01") for _ in range(5)]
        self.assertEqual(replay(rows)["2.5 Üst"]["models"]["old"]["sample"],0)
        rows.append(fixture("2026-08-02"))
        r=replay(rows)
        self.assertEqual(r["2.5 Üst"]["models"]["old"]["sample"],1)
        self.assertEqual(r["2.5 Üst"]["models"]["baseline"]["brier"],0)
    def test_old_season_excluded(self):
        rows=[fixture("2024-08-01") for _ in range(5)]+[fixture("2026-08-02")]
        self.assertEqual(replay(rows)["2.5 Üst"]["models"]["old"]["sample"],0)
    def test_progress_separate(self):
        now=datetime(2026,11,27,8,tzinfo=TR)
        row=dict(date="2026-11-28",recordedAt="2026-11-26T08:00:00+03:00",old=.6,candidate=.7,baseline=.5,result=None)
        a={"pending":row};before=copy.deepcopy(a)
        p=progress(a,now)
        self.assertEqual(a,before)
        self.assertEqual(p["tested"],0)
        self.assertEqual(p["pendingByDate"],{"2026-11-28":1})
        self.assertEqual(p["minimumMatches"],500)
if __name__=="__main__":unittest.main()
