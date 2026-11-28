import unittest,copy
from datetime import datetime
from main_ml_calibration_review import evaluate,dual_gate
from results_source_pilot import TR
class ReviewTests(unittest.TestCase):
    def test_empty_never_approved(self):
        meta=dict(modelSha256="test",frozenAt="2026-11-28T09:00:00+03:00")
        ledger=dict(version="6.67",modelSha256="test",forecasts={},settlements={},quarantine={})
        pairs=dict(version="6.69",modelSha256="test",pairs={})
        before=copy.deepcopy((ledger,pairs))
        r=evaluate(pairs,ledger,meta,datetime(2026,11,28,12,tzinfo=TR))
        self.assertFalse(r["automaticApproval"])
        self.assertFalse(r["overall"]["reviewScreenReady"])
        self.assertEqual(len(r["leagues"]),9)
        self.assertTrue(all(v["status"]=="collecting_data" for v in r["leagues"].values()))
        self.assertEqual((ledger,pairs),before)
        self.assertTrue(all(v["gate"]["status"]=="not_evaluated" for v in r["overall"]["markets"].values()))
    def test_wrong_cohort(self):
        with self.assertRaises(ValueError):
            evaluate(dict(version="6.69",modelSha256="bad",pairs={}),dict(version="6.67",modelSha256="x",forecasts={},settlements={},quarantine={}),dict(modelSha256="x"),datetime(2026,11,28,12,tzinfo=TR))
    def test_both_baselines_required(self):
        def metric(brier,loss):
            return dict(brier=brier,logLoss=loss,ece10=.02,bins=[dict(n=100)])
        candidate=metric(.15,.4)
        row=dict(candidate=candidate,legacy=metric(.18,.5),poisson=metric(.14,.39),
            pairedBootstrap=dict(interval95=[.01,.04]),pairedPoissonBootstrap=dict(interval95=[-.02,-.001]))
        self.assertEqual(dual_gate(row,False)["status"],"not_evaluated")
        r=dual_gate(row,True)
        self.assertTrue(r["checks"]["legacyPass"])
        self.assertFalse(r["checks"]["poissonPass"])
        self.assertEqual(r["status"],"retain_baseline")
        row["poisson"]=metric(.17,.5)
        row["pairedPoissonBootstrap"]=dict(interval95=[.01,.03])
        self.assertEqual(dual_gate(row,True)["status"],"eligible_for_manual_review")
if __name__=="__main__":unittest.main()
