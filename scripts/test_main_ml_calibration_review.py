import unittest,copy
from datetime import datetime
from main_ml_calibration_review import evaluate
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
if __name__=="__main__":unittest.main()
