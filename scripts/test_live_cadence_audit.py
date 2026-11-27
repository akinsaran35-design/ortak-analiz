import unittest
from datetime import datetime,timedelta,timezone
from live_cadence_audit import build
T=datetime(2026,11,27,15,tzinfo=timezone.utc)
def snap(t,detected=0,requested=0,fresh=0,issues=0):
    return dict(mode="live_snapshot_only",source="ESPN",startedAt=t.isoformat(),updatedAt=(t+timedelta(seconds=5)).isoformat(),detected=detected,requested=requested,freshAtBuild=fresh,rows=[{}]*requested,sourceIssues=[{}]*issues)
class Tests(unittest.TestCase):
    def test_gaps(self):
        a=[]
        for n in (0,5,20,80,400):
            t=T+timedelta(minutes=n)
            a,r=build(snap(t),a,t+timedelta(seconds=5))
        self.assertEqual(r["runs"],5)
        self.assertEqual(r["actualGapCount"],4)
        self.assertEqual(r["gapsOver180Minutes"],1)
        self.assertEqual(r["within180Minutes"]["median"],15)
        self.assertEqual(r["within180Minutes"]["within5"],1)
        self.assertEqual(r["within180Minutes"]["within15"],2)
        self.assertFalse(r["scheduleGuaranteed"])
    def test_status(self):
        a=[]
        for i,args in enumerate(((0,0,0,0),(2,2,0,0),(3,2,1,0),(2,2,2,0),(0,0,0,1))):
            t=T+timedelta(minutes=i)
            a,r=build(snap(t,*args),a,t+timedelta(seconds=5))
        self.assertEqual(r["counts"],dict(no_live_detected=1,no_fresh_summary=1,partial_observation=1,fresh_observation=1,source_issues=1))
    def test_bad_counts(self):
        with self.assertRaises(ValueError):build(snap(T,1,2,1),[],T+timedelta(seconds=5))
    def test_duplicate_conflict(self):
        a,_=build(snap(T),[],T+timedelta(seconds=5))
        a,r=build(snap(T),a,T+timedelta(seconds=5))
        self.assertEqual(r["runs"],1)
        with self.assertRaises(ValueError):build(snap(T,1,1,1),a,T+timedelta(seconds=5))
    def test_retention(self):
        a,_=build(snap(T),[],T+timedelta(seconds=5))
        t=T+timedelta(days=8)
        _,r=build(snap(t),a,t+timedelta(seconds=5))
        self.assertEqual(r["runs"],1)
if __name__=="__main__":unittest.main()
