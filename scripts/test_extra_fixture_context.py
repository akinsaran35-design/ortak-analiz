import unittest,json
from datetime import datetime,timedelta
from extra_fixture_context import build,LEAGUES

class FixtureTests(unittest.TestCase):
    def test_exact_match_and_unresolved(self):
        now=datetime.fromisoformat("2026-11-28T14:00:00+03:00")
        history=dict(version="7.09",updatedAt=now.isoformat(),cutoffExclusive="2026-11-28",
            source="football-data.co.uk",predictionsEnabled=False,groups=[
                dict(league=code,teamStatistics=dict(cutoffExclusive="2026-11-28",
                     teams=[dict(team=t,recent=dict(sample=3)) for t in ("alpha","beta")]))
                for _,code,_,_ in LEAGUES])
        def event(i,away,minutes):
            return dict(id=str(i),date=(now+timedelta(minutes=minutes)).isoformat(),
                competitions=[dict(competitors=[dict(homeAway="home",team=dict(displayName="Alpha")),
                    dict(homeAway="away",team=dict(displayName=away))],
                    status=dict(type=dict(state="pre",name="STATUS_SCHEDULED")))])
        def reader(url):
            return json.dumps(dict(events=[event(1,"Beta",60),event(2,"Unknown",90),
                event(3,"Beta",-10)] if url.endswith("20261128") and "/sco.1/" in url else []))
        r=build(history,now,reader)
        self.assertEqual(r["fixtureCount"],2)
        self.assertEqual(r["matchedCount"],1)
        self.assertEqual(r["unmatchedCount"],1)
        self.assertIsNone(r["groups"][0]["rows"][1]["homeStatistics"])
        self.assertFalse(r["predictionsEnabled"])
        with self.assertRaises(ValueError):
            build(history,now+timedelta(days=1),reader)

if __name__=="__main__":unittest.main()
