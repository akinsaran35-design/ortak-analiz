import copy
import unittest
from datetime import datetime,timedelta
from live_analysis_quality import build,assess
from live_statistics_pilot import BASE,SOURCES
from results_source_pilot import TR

NOW=datetime(2026,11,26,21,0,tzinfo=TR)
def row():
    return dict(league="en.1",eventId="123",home="A",away="B",kickoff="2026-11-26T17:00:00+00:00",source=BASE+SOURCES["en.1"][1]+"/summary?event=123",receivedAt=NOW.isoformat(),error=None,observation=dict(state="in",score=[1,0],clock="54'",metrics=dict(corners=[4,1],shots=[8,3],shotsOnTarget=[3,1],yellowCards=[1,0],redCards=[0,0],possession=[60.2,39.8])))
def snap(rows):
    return dict(mode="live_snapshot_only",source="ESPN",updatedAt=NOW.isoformat(),rows=rows)
class Tests(unittest.TestCase):
    def test_valid_not_prediction(self):
        result=build(snap([row()]),NOW)
        self.assertEqual(result["counts"],{"observation_ready":1})
        self.assertIsNone(result["rows"][0]["prediction"])
        self.assertFalse(result["predictionsEnabled"])
    def test_stale_and_missing(self):
        r=row();r["receivedAt"]=(NOW-timedelta(seconds=121)).isoformat()
        self.assertEqual(assess(r,NOW),"stale_receipt")
        r=row();del r["observation"]["metrics"]["corners"]
        self.assertEqual(assess(r,NOW),"incomplete_metrics")
    def test_conflict(self):
        r=row();r["observation"]["metrics"]["shotsOnTarget"]=[9,0]
        self.assertEqual(assess(r,NOW),"conflicting_metrics")
        r=row();r["observation"]["metrics"]["possession"]=[80,80]
        self.assertEqual(assess(r,NOW),"conflicting_metrics")
    def test_identity_and_duplicates(self):
        r=row();r["source"]="wrong"
        self.assertEqual(assess(r,NOW),"invalid_identity")
        self.assertEqual(build(snap([row(),row()]),NOW)["counts"],{"duplicate_identity":2})
    def test_empty_and_bad(self):
        self.assertEqual(build(snap([]),NOW)["rows"],[])
        with self.assertRaises(ValueError):build(snap([row()]*13),NOW)
if __name__=="__main__":unittest.main()
