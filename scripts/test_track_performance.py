import json
import runpy
import shutil
import tempfile
import unittest
from pathlib import Path
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
from io import BytesIO

class TrackingTest(unittest.TestCase):
    def test_archive_and_settlement(self):
        today = datetime.now(timezone(timedelta(hours=3))).date()
        past = (today-timedelta(days=1)).isoformat()
        future = (today+timedelta(days=1)).isoformat()
        league = "İngiltere Championship"
        probs = {"1.5 Üst":80,"2.5 Üst":60,"KG Var":50}
        def candidate(d):
            return {"date":d,"league":league,"match":"A – B","markets":dict(probs)}
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/"scripts").mkdir()
            script=root/"scripts"/"track_performance.py"
            shutil.copyfile(Path(__file__).with_name("track_performance.py"),script)
            old=dict(candidate(past),result=None,recordedAt=(today-timedelta(days=2)).isoformat()+"T12:00:00+03:00")
            k=json.dumps([past,league,"A – B"],ensure_ascii=False)
            archive=root/"prediction_archive.json"
            archive.write_text(json.dumps({k:old}),encoding="utf-8")
            daily=root/"daily.json"
            daily.write_text(json.dumps({"version":"test","candidates":[candidate(future),candidate(today.isoformat())]}),encoding="utf-8")
            payload=json.dumps([{"date":past,"team1":"C","team2":"D","score":[1,0]},{"date":past,"team1":"A","team2":"B","score":{"ft":[2,1]}}]).encode()
            with patch("urllib.request.urlopen",side_effect=lambda *a,**kw:BytesIO(payload)):
                runpy.run_path(str(script))
                report=json.loads((root/"performance.json").read_text())
                self.assertEqual(report["errors"],[])
                self.assertEqual(report["overall"]["recorded"],2)
                self.assertEqual(report["overall"]["settled"],0)
                self.assertEqual(report["overall"]["pending"],2)
                self.assertIsNone(json.loads(archive.read_text())[k]["result"])
                (root/"verified_results.json").write_text(json.dumps({"records":[{"date":past,"league":"en.2","home":"A","away":"B","result":[2,1],"sources":["https://example.org/a","https://example.net/b"]}]}),encoding="utf-8")
                runpy.run_path(str(script))
                report=json.loads((root/"performance.json").read_text())
                self.assertEqual(report["overall"]["settled"],1)
                self.assertEqual(report["overall"]["pending"],1)
                for market,expected in zip(probs,[0.04,0.16,0.25]):
                    self.assertAlmostEqual(report["overall"]["markets"][market]["brier"],expected)
                changed=candidate(future)
                changed["markets"]["1.5 Üst"]=10
                daily.write_text(json.dumps({"candidates":[changed]}))
                runpy.run_path(str(script))
                records=json.loads(archive.read_text())
                self.assertEqual(len(records),2)
                self.assertEqual(records[k]["result"],[2,1])
                self.assertEqual(next(r for r in records.values() if r["date"]==future)["markets"]["1.5 Üst"],80)

if __name__=="__main__":
    unittest.main()
