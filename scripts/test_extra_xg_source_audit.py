import unittest
from extra_xg_source_audit import extract_xg,completed_events

class XgTests(unittest.TestCase):
    def setUp(self):
        self.fixture=dict(eventId="123",teams={"home":"1","away":"2"})
        self.status=dict(type=dict(completed=True,name="STATUS_FULL_TIME"))
        self.payload=dict(header=dict(id="123",competitions=[dict(status=self.status)]),boxscore=dict(teams=[
            dict(team=dict(id="2"),statistics=[dict(name="expectedGoals",displayValue="0.84")]),
            dict(team=dict(id="1"),statistics=[dict(name="xG",value=1.53)])]))
    def test_explicit_xg_and_xga(self):
        out=extract_xg(self.payload,self.fixture)
        self.assertEqual(out["status"],"provider_xg_pair")
        self.assertEqual((out["homeXg"],out["awayXg"],out["homeXga"],out["awayXga"]),(1.53,0.84,0.84,1.53))
    def test_missing_never_estimated(self):
        self.payload["boxscore"]["teams"][0]["statistics"]=[dict(name="totalShots",value=12)]
        self.assertEqual(extract_xg(self.payload,self.fixture)["status"],"xg_missing")
    def test_invalid_and_identity(self):
        self.payload["boxscore"]["teams"][0]["statistics"][0]["displayValue"]="nan"
        self.assertEqual(extract_xg(self.payload,self.fixture)["status"],"invalid_xg")
        self.payload["header"]["id"]="999"
        self.assertEqual(extract_xg(self.payload,self.fixture)["status"],"event_mismatch")
    def test_final_event_only(self):
        event=dict(id="123",date="2026-11-27T17:00:00Z",competitions=[dict(date="2026-11-27T17:00:00Z",status=self.status,competitors=[
            dict(homeAway="home",team=dict(id="1")),dict(homeAway="away",team=dict(id="2"))])])
        self.assertEqual(len(completed_events(dict(events=[event]),"sco.1","2026-11-27")),1)
        self.assertEqual(completed_events(dict(events=[event,event]),"sco.1","2026-11-27"),[])
        self.status["type"]["completed"]=False
        self.assertEqual(completed_events(dict(events=[event]),"sco.1","2026-11-27"),[])
if __name__=="__main__":
    unittest.main()
