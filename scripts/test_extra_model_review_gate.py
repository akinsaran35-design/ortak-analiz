import unittest
from extra_model_review_gate import assess,market_gate
from test_extra_prospective_reliability import ReliabilityTests

class GateTests(unittest.TestCase):
    def test_waiting(self):
        f=ReliabilityTests()
        f.setUp()
        r=assess(f.l,f.now)
        self.assertEqual(r["status"],"collecting_data")
        self.assertFalse(r["reviewScreenReady"])
        self.assertEqual(r["validPending"],1)
        self.assertFalse(r["automaticApproval"])
    def test_integrity_failure(self):
        f=ReliabilityTests()
        f.setUp()
        f.r["recordedAt"]=f.r["kickoff"]
        self.assertEqual(assess(f.l,f.now)["status"],"integrity_failure")
    def test_manual_review_only(self):
        p=dict(brier=.25,logLoss=.69,ece10=.03,bins=[dict(n=500)])
        q=dict(brier=.24,logLoss=.68,ece10=.02,bins=[dict(n=500)])
        self.assertEqual(market_gate(p,q,{"interval95":[.002,.02]})["status"],"eligible_for_manual_review")
        self.assertEqual(market_gate(p,q,{"interval95":[-.001,.02]})["status"],"retain_baseline")
        self.assertEqual(market_gate(p,p,{"interval95":[0,0]})["status"],"retain_baseline")
        self.assertEqual(market_gate(p,q,{"interval95":None})["status"],"insufficient_evidence")
        q["bins"]=[dict(n=29),dict(n=471)]
        self.assertEqual(market_gate(p,q,{"interval95":[.002,.02]})["status"],"retain_baseline")
if __name__=="__main__":
    unittest.main()
