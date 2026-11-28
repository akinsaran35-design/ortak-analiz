import unittest
from datetime import datetime
from extra_ml_prospective import empty_ledger
from extra_ml_review_gate import assess
from results_source_pilot import TR
class GateTests(unittest.TestCase):
    def test_empty_never_approved(self):
        meta=dict(modelSha256="test")
        r=assess(empty_ledger(meta),meta,datetime(2026,11,28,12,tzinfo=TR))
        self.assertFalse(r["reviewScreenReady"])
        self.assertFalse(r["automaticApproval"])
        self.assertEqual(r["status"],"collecting_data")
        self.assertTrue(all(x["status"]=="not_evaluated" for x in r["markets"].values()))
    def test_mismatched_cohort(self):
        with self.assertRaises(ValueError):
            assess(empty_ledger(dict(modelSha256="a")),dict(modelSha256="b"),datetime(2026,11,28,12,tzinfo=TR))
if __name__=="__main__":unittest.main()
