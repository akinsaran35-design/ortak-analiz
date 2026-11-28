import unittest
from datetime import datetime,timezone,timedelta
from market_data_health import coverage
class CoverageTests(unittest.TestCase):
    def test_scope_and_age(self):
        now=datetime(2026,11,28,12,tzinfo=timezone.utc)
        stamp=now.isoformat()
        event=dict(id="x",kickoff=(now+timedelta(hours=2)).isoformat(),bookmakers=[dict(key=k,lines=[dict(point=2.5,over=1.9,under=2,lastUpdate=stamp)]) for k in "abc"])
        event["bookmakers"][0]["lines"].append(dict(point=1.5,over=1.3,under=3,lastUpdate=stamp))
        snapshot=dict(source="The Odds API",region="uk",market="totals",errors=[],updatedAt=stamp,events=[event],remainingCredits=98)
        archive=dict(mode="research_only",updatedAt=stamp,records={"x":dict(market="btts")})
        r=coverage(snapshot,archive,now)
        self.assertEqual(r["markets"]["over15"]["observedEvents"],1)
        self.assertEqual(r["markets"]["over15"]["freshFutureThreeBookEvents"],0)
        self.assertEqual(r["markets"]["over25"]["freshFutureThreeBookEvents"],1)
        self.assertIsNone(r["markets"]["btts"]["observedEvents"])
        self.assertEqual(r["markets"]["btts"]["status"],"not_requested")
        self.assertFalse(r["historicalExtraMarketArchive"]["usedAsCurrentEvidence"])
        self.assertEqual(r["additionalApiRequests"],0)
        stale=coverage(snapshot,archive,now+timedelta(minutes=31))
        self.assertEqual(stale["markets"]["over25"]["observedEvents"],1)
        self.assertEqual(stale["markets"]["over25"]["freshFutureThreeBookEvents"],0)
        self.assertFalse(stale["snapshotFresh"])
        self.assertEqual(coverage(dict(snapshot,events=[event,event]),archive,now)["markets"]["over25"]["observedEvents"],0)
        self.assertEqual(coverage(dict(snapshot,region="tr"),archive,now)["markets"]["over25"]["observedEvents"],0)
        self.assertEqual(coverage(dict(snapshot,events=[dict(event,bookmakers=event["bookmakers"]+[event["bookmakers"][0]])]),archive,now)["markets"]["over25"]["freshFutureThreeBookEvents"],0)
if __name__=="__main__":unittest.main()
