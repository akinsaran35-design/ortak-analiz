import unittest
from datetime import datetime, timezone, timedelta
from shadow_performance import archive_coupon, settle, metrics
from shadow_results import resolve

class ShadowTests(unittest.TestCase):
    def test_coupon(self):
        now = datetime(2026,11,25,12,tzinfo=timezone.utc)
        kickoff = now + timedelta(hours=2)
        picks = [{"eventId":str(i),"kickoff":kickoff.isoformat(),"market":"2.5 Over","odds":1.5} for i in range(3)]
        records = {}
        coupon = {"mode":"shadow","liveEnabled":False,"selections":picks}
        archive_coupon(records,coupon,now)
        archive_coupon(records,coupon,now)
        self.assertEqual(len(records),1)
        later = now + timedelta(days=1)
        results = {str(i):{"status":"final","score":[2,1]} for i in range(3)}
        settle(records,{},later)
        self.assertEqual(metrics(list(records.values()))["pending"],1)
        settle(records,results,later)
        self.assertEqual(metrics(list(records.values()))["profit"],237.5)
        self.assertEqual(metrics(list(records.values()))["roi"],2.375)
        records = {}
        archive_coupon(records,coupon,now)
        results["0"]["score"] = [0,0]
        settle(records,results,later)
        self.assertEqual(metrics(list(records.values()))["profit"],-100)
    def test_score_matching(self):
        now = datetime(2026,11,26,12,tzinfo=timezone.utc)
        p = {"eventId":"a","kickoff":"2026-11-25T18:00:00+00:00","league":"soccer_epl","match":"Home FC – Away FC"}
        records = {"x":{"status":"pending","selections":[p]}}
        results = {}
        fixture = {"date":"2026-11-25","team1":"Home FC","team2":"Away FC","score":{"ft":[2,1]}}
        resolve(records,results,now,lambda *args:[fixture,fixture])
        self.assertEqual(results,{})
        resolve(records,results,now,lambda *args:[fixture])
        self.assertEqual(results["a"]["score"],[2,1])

if __name__ == "__main__":
    unittest.main()
