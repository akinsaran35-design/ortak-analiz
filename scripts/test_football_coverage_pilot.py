import json,unittest
from datetime import datetime
from football_coverage_pilot import build,COMPETITIONS
class CoverageTests(unittest.TestCase):
    def test_scope_and_timezone(self):
        now=datetime.fromisoformat("2026-11-26T19:00:00+03:00")
        e={"id":"123","date":"2026-11-26T22:30:00Z","competitions":[{"competitors":[{"homeAway":"home","team":{"displayName":"A"}},{"homeAway":"away","team":{"displayName":"B"}}],"status":{"type":{"state":"pre","name":"STATUS_SCHEDULED"}}}]}
        def reader(url):
            if "/uefa.champions/" in url:return json.dumps({"events":[e]})
            if "/mex.1/" in url:raise OSError("unavailable")
            return json.dumps({"events":[]})
        r=build(now,reader)
        self.assertEqual(r["respondingCompetitions"],len(COMPETITIONS)-1)
        self.assertEqual(r["eventCount"],1)
        self.assertEqual(r["groups"][0]["rows"][0]["date"],"2026-11-27")
        self.assertFalse(r["coverageComplete"])
        self.assertFalse(r["predictionsEnabled"])
    def test_schema_failure(self):
        r=build(datetime.fromisoformat("2026-11-26T19:00:00+03:00"),lambda url:"{}")
        self.assertEqual(r["respondingCompetitions"],0)
        self.assertEqual(r["eventCount"],0)
if __name__=="__main__":unittest.main()
