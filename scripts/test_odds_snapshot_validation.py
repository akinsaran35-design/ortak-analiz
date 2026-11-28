import unittest,copy
from datetime import datetime,timezone,timedelta
from odds_snapshot_validation import normalize_event,finalize
class OddsTests(unittest.TestCase):
    def setUp(self):
        self.now=datetime(2026,11,28,12,tzinfo=timezone.utc)
        self.league="soccer_epl"
        self.event=dict(id="x",sport_key=self.league,home_team="A",away_team="B",commence_time=(self.now+timedelta(hours=1)).isoformat(),bookmakers=[dict(key="b",title="Book",markets=[dict(key="totals",last_update=self.now.isoformat(),outcomes=[dict(name="Over",point=2.5,price=1.9),dict(name="Under",point=2.5,price=2.0)])])])
    def test_completion_and_identity(self):
        e=normalize_event(self.event,self.league,self.now)
        self.assertIsNotNone(e)
        report=dict(startedAt=(self.now-timedelta(seconds=5)).isoformat(),events=[e],errors=[])
        finish=self.now+timedelta(seconds=5)
        result=finalize(report,finish)
        self.assertEqual(result["updatedAt"],finish.isoformat())
        self.assertEqual(result["eventCount"],1)
        self.assertEqual(finalize(dict(events=[e,e],errors=[]),finish)["errors"],["duplicate_event_identity"])
        self.assertEqual(finalize(dict(events=[e],errors=[]),self.now+timedelta(minutes=31))["eventCount"],0)
        self.assertIsNone(normalize_event(self.event,"other",self.now))
    def test_invalid_data(self):
        for invalid in ("duplicate_side","duplicate_book","future","nan","bool","missing_zone"):
            e=copy.deepcopy(self.event)
            b=e["bookmakers"][0]
            m=b["markets"][0]
            if invalid=="duplicate_side":m["outcomes"].append(m["outcomes"][0])
            if invalid=="duplicate_book":e["bookmakers"].append(copy.deepcopy(b))
            if invalid=="future":m["last_update"]=(self.now+timedelta(seconds=1)).isoformat()
            if invalid=="nan":m["outcomes"][0]["price"]=float("nan")
            if invalid=="bool":m["outcomes"][0]["price"]=True
            if invalid=="missing_zone":m["last_update"]="2026-11-28T12:00:00"
            self.assertIsNone(normalize_event(e,self.league,self.now),invalid)
if __name__=="__main__":unittest.main()
