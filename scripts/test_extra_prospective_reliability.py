import unittest
from datetime import datetime,timedelta
from extra_league_prospective import empty_ledger,key,TR
from extra_prospective_reliability import audit,reliability

class ReliabilityTests(unittest.TestCase):
    def setUp(self):
        self.now=datetime(2026,12,1,12,tzinfo=TR)
        p=dict(over15=.8,over25=.55,btts=.5)
        self.r=dict(league="sco.1",date="2026-11-29",home="alpha",away="beta",eventId="123",
            kickoff="2026-11-29T15:00:00+03:00",recordedAt="2026-11-28T10:00:00+03:00",
            trainingThrough="2026-11-27",trainingMatches=25,policyVersion="6.48",poisson=p,candidate=p.copy())
        self.k=key(self.r)
        self.l=empty_ledger()
        self.l["forecasts"][self.k]=self.r
    def test_no_outcomes_no_metrics(self):
        r=audit(self.l,self.now)
        self.assertTrue(r["integrityPassed"])
        self.assertEqual(r["validPending"],1)
        self.assertIsNone(r["markets"]["over15"]["candidate"]["brier"])
        self.assertFalse(r["productionModelValidated"])
    def test_settlement_and_quarantine(self):
        self.l["settlements"][self.k]=dict(score=[2,1],settledAt="2026-11-30T10:00:00+03:00",sources=["football-data","espn"])
        r=audit(self.l,self.now)
        self.assertEqual(r["validSettled"],1)
        self.assertAlmostEqual(r["markets"]["over15"]["candidate"]["brier"],.04)
        self.assertFalse(r["sampleTargetReached"])
        self.l["quarantine"][self.k]={}
        self.assertEqual(audit(self.l,self.now)["validSettled"],0)
    def test_invalid_evidence(self):
        self.r["recordedAt"]="2026-11-29T10:00:00+03:00"
        self.assertFalse(audit(self.l,self.now)["integrityPassed"])
        self.r["recordedAt"]="2026-11-28T10:00:00+03:00"
        self.r["candidate"]["over25"]=.95
        self.assertFalse(audit(self.l,self.now)["integrityPassed"])
        self.r["candidate"]["over25"]=.55
        self.l["settlements"][self.k]=dict(score=[2,1],settledAt="2026-11-30T10:00:00+03:00",sources=["espn"])
        self.assertFalse(audit(self.l,self.now)["integrityPassed"])
    def test_bins(self):
        r=reliability([(.2,0),(.8,1),(1,1)])
        self.assertEqual(sum(x["n"] for x in r["bins"]),3)
        self.assertFalse(any(x["descriptiveSampleAdequate"] for x in r["bins"]))
        self.assertAlmostEqual(r["ece10"],.4/3)
if __name__=="__main__":
    unittest.main()
