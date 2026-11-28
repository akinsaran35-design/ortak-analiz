import unittest,copy
from datetime import datetime
from main_ml_timing_audit import audit,band,cutoff_class
from results_source_pilot import TR
class TimingTests(unittest.TestCase):
    def test_bounds(self):
        for h,b in [(0,"within_24h"),(-24,"within_24h"),(24.01,"24_to_48h"),(-48,"24_to_48h"),(48.01,"over_48h")]:
            self.assertEqual(band(h),b)
    def test_cutoff_classes(self):
        pair=dict(legacyRecordedAt="2026-11-28T10:00:00+03:00")
        f=dict(date="2026-11-29",recordedAt="2026-11-28T12:00:00+03:00")
        self.assertEqual(cutoff_class(pair,f),"legacy_cutoff_not_recorded")
        pair["legacyTiming"]=dict(version="6.82",generationStartedAt="2026-11-28T08:00:00+03:00",generationCompletedAt="2026-11-28T09:00:00+03:00",historyCutoffExclusive="2026-11-28",historyThrough="2026-11-27",sameSourceDataEstablished=False)
        self.assertEqual(cutoff_class(pair,f),"same_calendar_cutoff")
        self.assertEqual(cutoff_class(pair,dict(f,recordedAt="2026-11-27T12:00:00+03:00")),"different_calendar_cutoff")
        pair["legacyTiming"]["historyThrough"]="2026-11-28"
        self.assertEqual(cutoff_class(pair,f),"legacy_cutoff_invalid")
    def test_empty(self):
        ledger=dict(version="6.67",modelSha256="x",forecasts={},settlements={},quarantine={})
        pairs=dict(version="6.69",modelSha256="x",pairs={})
        meta=dict(modelSha256="x")
        before=copy.deepcopy((ledger,pairs))
        r=audit(pairs,ledger,meta,datetime(2026,11,28,12,tzinfo=TR))
        self.assertEqual(r["paired"],0)
        self.assertEqual(r["sameCalendarCutoff"]["paired"],0)
        self.assertFalse(r["sameCalendarCutoff"]["sameSourceDataEstablished"])
        self.assertFalse(r["automaticApproval"])
        self.assertFalse(r["sameInformationCutoffEstablished"])
        self.assertEqual(sum(x["paired"] for x in r["bands"].values()),0)
        self.assertEqual((ledger,pairs),before)
if __name__=="__main__":unittest.main()
