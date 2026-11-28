import unittest,copy
from datetime import datetime,timezone,timedelta
from observed_totals_history import collect
class HistoryTests(unittest.TestCase):
    def test_same_book_chronology(self):
        now=datetime(2026,11,28,8,tzinfo=timezone.utc)
        def snap(t,p):
            return dict(source="The Odds API",region="uk",market="totals",errors=[],updatedAt=t.isoformat(),events=[dict(id="a",league="en",home="a",away="b",kickoff=(now+timedelta(days=1)).isoformat(),bookmakers=[dict(key=str(i),lines=[dict(point=2.5,over=p,under=2.1,lastUpdate=t.isoformat())]) for i in range(3)])])
        a=dict(version="6.63",records={})
        first=snap(now,2.0)
        self.assertIsNone(collect(a,first,now)["events"][0]["medianDropPct"])
        self.assertEqual(collect(a,first,now)["added"],0)
        later=now+timedelta(minutes=10)
        second=snap(later,1.8)
        self.assertAlmostEqual(collect(a,second,later)["events"][0]["medianDropPct"],10)
        before=copy.deepcopy(a)
        self.assertEqual(collect(a,second,later+timedelta(hours=1))["status"],"snapshot_unavailable")
        self.assertEqual(a,before)
        changed=snap(later+timedelta(minutes=1),1.7)
        changed["events"][0]["away"]="c"
        self.assertIsNone(collect(a,changed,later+timedelta(minutes=1))["events"][0]["medianDropPct"])
if __name__=="__main__":unittest.main()
