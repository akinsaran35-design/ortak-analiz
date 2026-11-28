import unittest,copy
from datetime import datetime
from main_ml_timing_audit import audit,band
from results_source_pilot import TR
class TimingTests(unittest.TestCase):
    def test_bounds(self):
        for h,b in [(0,"within_24h"),(-24,"within_24h"),(24.01,"24_to_48h"),(-48,"24_to_48h"),(48.01,"over_48h")]:
            self.assertEqual(band(h),b)
    def test_empty(self):
        ledger=dict(version="6.67",modelSha256="x",forecasts={},settlements={},quarantine={})
        pairs=dict(version="6.69",modelSha256="x",pairs={})
        meta=dict(modelSha256="x")
        before=copy.deepcopy((ledger,pairs))
        r=audit(pairs,ledger,meta,datetime(2026,11,28,12,tzinfo=TR))
        self.assertEqual(r["paired"],0)
        self.assertFalse(r["automaticApproval"])
        self.assertFalse(r["sameInformationCutoffEstablished"])
        self.assertEqual(sum(x["paired"] for x in r["bands"].values()),0)
        self.assertEqual((ledger,pairs),before)
if __name__=="__main__":unittest.main()
