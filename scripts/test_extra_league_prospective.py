import unittest
from datetime import datetime,timedelta
from extra_league_prospective import empty_ledger,capture,settle,summarize,scheduled_fixtures,key,TR

class ProspectiveTests(unittest.TestCase):
    def setUp(self):
        self.now=datetime(2026,11,28,12,tzinfo=TR)
        self.fixture=dict(league="sco.1",date="2026-11-29",home="alpha",away="beta",eventId="123",kickoff="2026-11-29T15:00:00+03:00")
        self.history=[dict(league="sco.1",date=(self.now.date()-timedelta(days=i+1)).isoformat(),home="alpha",away="beta",csv=[2,1],espn=[2,1],status="corroborated") for i in range(25)]
    def test_future_only_and_no_overwrite(self):
        ledger=empty_ledger()
        self.assertEqual(capture(ledger,self.history,[self.fixture],self.now),1)
        saved=ledger["forecasts"][key(self.fixture)].copy()
        self.assertEqual(capture(ledger,self.history,[self.fixture],self.now),0)
        self.assertEqual(ledger["forecasts"][key(self.fixture)],saved)
        self.assertEqual(capture(empty_ledger(),self.history,[self.fixture],self.now+timedelta(days=1)),0)
        self.assertEqual(capture(empty_ledger(),self.history[:10],[self.fixture],self.now),0)
        self.assertEqual(capture(empty_ledger(),self.history,[self.fixture,self.fixture],self.now),0)
        later=dict(self.fixture,date="2026-11-30",kickoff="2026-11-30T15:00:00+03:00")
        self.assertEqual(capture(ledger,self.history,[later],self.now),0)
    def test_settlement_requires_agreement_and_prior_capture(self):
        ledger=empty_ledger()
        capture(ledger,self.history,[self.fixture],self.now)
        r=dict(self.fixture,csv=[2,1],espn=[2,1],status="corroborated")
        self.assertEqual(settle(ledger,[r],self.now),0)
        self.assertEqual(settle(ledger,[r],self.now+timedelta(days=2)),1)
        self.assertEqual(settle(ledger,[r],self.now+timedelta(days=3)),0)
        self.assertEqual(summarize(ledger)["settled"],1)
        self.assertFalse(summarize(ledger)["productionModelValidated"])
        self.assertEqual(settle(ledger,[dict(r,csv=[1,1],espn=[1,1])],self.now+timedelta(days=3)),0)
        self.assertEqual(summarize(ledger)["quarantined"],1)
        self.assertEqual(summarize(ledger)["settled"],0)
        self.assertEqual(settle(empty_ledger(),[r],self.now+timedelta(days=2)),0)
    def test_scheduled_source_gate(self):
        event=dict(id="123",date=self.fixture["kickoff"],competitions=[dict(date=self.fixture["kickoff"],status=dict(type=dict(state="pre",completed=False,name="STATUS_SCHEDULED")),competitors=[dict(homeAway="home",team=dict(displayName="Alpha")),dict(homeAway="away",team=dict(displayName="Beta"))])])
        self.assertEqual(scheduled_fixtures(dict(events=[event]),"sco.1",self.now),[self.fixture])
        self.assertEqual(scheduled_fixtures(dict(events=[event,event]),"sco.1",self.now),[])
        event["competitions"][0]["status"]["type"]["state"]="in"
        self.assertEqual(scheduled_fixtures(dict(events=[event]),"sco.1",self.now),[])
if __name__=="__main__":
    unittest.main()
