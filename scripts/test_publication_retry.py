import json,tempfile,unittest
from pathlib import Path
from datetime import datetime,timezone,timedelta
from publication_retry import safe_paths,fresh_reports

class RetryTests(unittest.TestCase):
    def test_paths(self):
        self.assertTrue(safe_paths({"extra_ml_prospective_ledger.json","extra_ml_frozen.cbm"}))
        self.assertFalse(safe_paths(set()))
        self.assertFalse(safe_paths({"daily.json","extra_ml_prospective_ledger.json"}))
        self.assertFalse(safe_paths({"scripts/daily_analysis.py"}))
    def test_freshness(self):
        now=datetime(2026,11,28,8,tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            def put(name,stamp,**kw):
                (root/name).write_text(json.dumps(dict(updatedAt=stamp.isoformat(),**kw)))
            put("daily.json",now)
            put("snapshot_integrity.json",now,status="PASS",errors=[])
            self.assertTrue(fresh_reports(now,root))
            self.assertFalse(fresh_reports(now+timedelta(minutes=31),root))
            self.assertFalse(fresh_reports(now-timedelta(seconds=1),root))
            put("snapshot_integrity.json",now,status="FAIL",errors=["conflict"])
            self.assertFalse(fresh_reports(now,root))
if __name__=="__main__":
    unittest.main()
