import unittest
from datetime import datetime,timedelta
from live_rate_link import link
from results_source_pilot import TR
NOW=datetime(2026,11,26,21,0,tzinfo=TR)
def row():
    return dict(league="en.1",home="A",away="B",kickoff="2026-11-26T17:00:00+00:00",quality="observation_ready",observation=dict(clock="54'",score=[1,0],metrics={"redCards":[0,0]}))
def daily():
    return dict(updatedAt="2026-11-26T15:00:00+00:00",candidates=[dict(date="2026-11-26",league="İngiltere Premier Lig",match="A – B",expectedGoals={"home":1.5,"away":1.2})])
class Tests(unittest.TestCase):
    def test_valid(self):
        reason,result=link(row(),daily(),NOW)
        self.assertEqual(reason,"conditional_scenario")
        self.assertFalse(result["predictionsEnabled"])
    def test_post_kickoff(self):
        d=daily();d["updatedAt"]=NOW.isoformat()
        self.assertEqual(link(row(),d,NOW)[0],"no_pre_kickoff_snapshot")
    def test_exact_identity(self):
        d=daily();d["candidates"][0]["match"]="B – A"
        self.assertEqual(link(row(),d,NOW)[0],"no_unique_exact_name_match")
        d=daily();d["candidates"]*=2
        self.assertEqual(link(row(),d,NOW)[0],"no_unique_exact_name_match")
    def test_unsupported(self):
        r=row();r["observation"]["clock"]="45+2'"
        self.assertEqual(link(r,daily(),NOW)[0],"unsupported_clock")
        r=row();r["observation"]["metrics"]["redCards"]=[1,0]
        self.assertEqual(link(r,daily(),NOW)[0],"red_card_effect_unmodeled")
        r=row();r["quality"]="stale_receipt"
        self.assertEqual(link(r,daily(),NOW)[0],"quality_rejected")
    def test_audited_identity(self):
        r=row();r["eventId"]="123";r["home"]="A FC"
        d=daily()
        c=dict(version="4.92",source="ESPN",mode="research_only",dailyUpdatedAt=d["updatedAt"],updatedAt="2026-11-26T15:05:00+00:00",dates=["2026-11-26"],rows=[dict(league="en.1",status="same_date",published=[dict(date="2026-11-26",league="İngiltere Premier Lig",match="A – B")],espn=[dict(date="2026-11-26",eventId="123",kickoff=r["kickoff"],match="A FC – B")])])
        self.assertEqual(link(r,d,NOW,c)[0],"conditional_scenario")
        self.assertEqual(link(dict(r,eventId="124"),d,NOW,c)[0],"no_verified_event_link")
        self.assertEqual(link(dict(r,kickoff="2026-11-26T17:01:00+00:00"),d,NOW,c)[0],"no_verified_event_link")
        self.assertEqual(link(r,d,NOW,dict(c,rows=c["rows"]*2))[0],"no_verified_event_link")
        self.assertEqual(link(r,d,NOW,dict(c,updatedAt=NOW.isoformat()))[0],"no_verified_event_link")
        self.assertEqual(link(r,d,NOW,dict(c,dailyUpdatedAt="wrong"))[0],"no_verified_event_link")
if __name__=="__main__":unittest.main()
