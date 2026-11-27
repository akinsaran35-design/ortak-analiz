import unittest
from datetime import datetime,timedelta,timezone
from live_observation_history import build,delta,minute
T=datetime(2026,11,27,15,tzinfo=timezone.utc)
def q(m,received,shots=4,score=None):
    return dict(mode="live_analysis_quality_only",predictionsEnabled=False,updatedAt=received.isoformat(),rows=[dict(quality="observation_ready",league="en.1",eventId="123",home="A",away="B",kickoff=T.isoformat(),receivedAt=received.isoformat(),observation=dict(state="in",clock=f"{m}'",score=score or [0,0],metrics=dict(corners=[1,1],shots=[shots,3],shotsOnTarget=[1,1],yellowCards=[0,0],redCards=[0,0],possession=[50,50])))])
class Tests(unittest.TestCase):
    def test_windows(self):
        a,r=build(q(10,T+timedelta(minutes=10)),{},T+timedelta(minutes=10))
        self.assertEqual(r["windowCounts"],{"5":0,"10":0,"15":0})
        for m in (15,20,25):
            a,r=build(q(m,T+timedelta(minutes=m),m),a,T+timedelta(minutes=m))
        self.assertEqual(r["windowCounts"],{"5":1,"10":1,"15":1})
        self.assertEqual(r["rows"][0]["windows"]["5"]["changes"]["shots"],[5,0])
        self.assertFalse(r["predictionsEnabled"])
    def test_halftime_gap(self):
        a,_=build(q(40,T+timedelta(minutes=40)),{},T+timedelta(minutes=40))
        _,r=build(q(50,T+timedelta(minutes=65)),a,T+timedelta(minutes=65))
        self.assertEqual(r["windowCounts"]["10"],0)
    def test_correction(self):
        a,_=build(q(10,T+timedelta(minutes=10),8),{},T+timedelta(minutes=10))
        a,_=build(q(15,T+timedelta(minutes=15),5),a,T+timedelta(minutes=15))
        _,r=build(q(20,T+timedelta(minutes=20),10),a,T+timedelta(minutes=20))
        self.assertEqual(r["windowCounts"]["10"],0)
    def test_duplicate(self):
        report=q(10,T+timedelta(minutes=10))
        a,_=build(report,{},T+timedelta(minutes=10))
        _,r=build(report,a,T+timedelta(minutes=10))
        self.assertEqual(r["accepted"],0)
        self.assertEqual(r["archivedPoints"],1)
    def test_stale_receipt(self):
        report=q(10,T+timedelta(minutes=10))
        report["updatedAt"]=(T+timedelta(minutes=15)).isoformat()
        _,r=build(report,{},T+timedelta(minutes=15))
        self.assertEqual(r["accepted"],0)
    def test_clock_and_retention(self):
        self.assertIsNone(minute("45+2'"))
        a,_=build(q(10,T+timedelta(minutes=10)),{},T+timedelta(minutes=10))
        t=T+timedelta(days=8)
        _,r=build(dict(mode="live_analysis_quality_only",predictionsEnabled=False,updatedAt=t.isoformat(),rows=[]),a,t)
        self.assertEqual(r["archivedEvents"],0)
if __name__=="__main__":unittest.main()
