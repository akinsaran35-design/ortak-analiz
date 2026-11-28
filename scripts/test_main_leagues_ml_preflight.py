import unittest
from datetime import datetime,date
from results_source_pilot import TR
from main_leagues_ml_preflight import fixtures,identity
class MainPreflightTests(unittest.TestCase):
    def test_alias_and_schedule(self):
        self.assertEqual(identity("en.1","Man United"),identity("en.1","Manchester United"))
        e=dict(id="123",date="2026-11-29T12:00:00Z",competitions=[dict(date="2026-11-29T12:00:00Z",
            status=dict(type=dict(name="STATUS_SCHEDULED",completed=False)),
            competitors=[dict(homeAway="home",team=dict(displayName="Manchester United")),dict(homeAway="away",team=dict(displayName="Liverpool"))])])
        now=datetime(2026,11,28,12,tzinfo=TR)
        f=fixtures(dict(events=[e]),"en.1",date(2026,11,29),now)
        self.assertEqual(len(f),1)
        self.assertEqual(f[0]["eventId"],"123")
        e["competitions"][0]["status"]["type"]["name"]="STATUS_FULL_TIME"
        self.assertEqual(fixtures(dict(events=[e]),"en.1",date(2026,11,29),now),[])
if __name__=="__main__":unittest.main()
