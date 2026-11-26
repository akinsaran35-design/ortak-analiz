import json,unittest
from datetime import datetime
from basketball_source_pilot import build

class PilotTests(unittest.TestCase):
    def test_cross_midnight_and_duplicates(self):
        now=datetime.fromisoformat("2026-11-26T19:00:00+03:00")
        def reader(url):
            event={"id":"1","date":"2026-11-25T23:30:00Z","competitions":[{"competitors":[
                {"homeAway":"home","team":{"displayName":"A"},"score":"110"},
                {"homeAway":"away","team":{"displayName":"B"},"score":"105"}],
                "status":{"type":{"state":"post","completed":True,"name":"STATUS_FINAL"}}}]}
            return json.dumps({"events":[event]})
        r=build(now,reader)
        self.assertEqual(r["completeDays"],3)
        self.assertEqual(r["eventCount"],1)
        self.assertEqual(r["groups"][1]["rows"][0]["score"],[110,105])
        self.assertEqual(r["groups"][0]["rows"],[])
        self.assertFalse(r["realBettingEnabled"])
    def test_source_failure(self):
        def fail(url):raise OSError("unavailable")
        r=build(datetime.fromisoformat("2026-11-26T19:00:00+03:00"),fail)
        self.assertEqual(r["completeDays"],0)
        self.assertEqual(r["eventCount"],0)
        self.assertEqual(r["decision"],"PAS")
if __name__=="__main__":unittest.main()
