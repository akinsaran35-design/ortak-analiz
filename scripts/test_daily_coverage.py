"""Exercise daily coverage without any external network or quota use."""
import io
import json
import runpy
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).with_name("daily_analysis.py").resolve()

class FixtureCoverageTest(unittest.TestCase):
    def test_complete_and_partial(self):
        tr = timezone(timedelta(hours=3))
        date = (datetime.now(tr).date()+timedelta(days=2)).isoformat()
        rows = [{"date":date,"team1":f"Home {i}","team2":f"Away {i}"} for i in range(12)]
        for partial in (False, True):
            def fake(req, timeout):
                if partial and "/de.1.json" in req.full_url:
                    raise OSError("fixture source unavailable")
                return io.BytesIO(json.dumps({"matches":rows}).encode())
            with tempfile.TemporaryDirectory() as d:
                target=Path(d)/"daily.json"
                original=Path.write_text
                def write(p, *args, **kwargs):
                    return original(target if p==Path("daily.json") else p,*args,**kwargs)
                with patch("urllib.request.urlopen", side_effect=fake), patch.object(Path,"write_text",write):
                    runpy.run_path(str(SCRIPT))
                report=json.loads(target.read_text())
            self.assertEqual(report["upcomingCount"], 60 if partial else 72)
            self.assertEqual(report["upcomingCount"],len(report["upcoming"]))
            self.assertEqual(report["upcomingCountsByDate"][date],report["upcomingCount"])
            self.assertEqual(report["fixtureCoverageComplete"],not partial)
            self.assertEqual(report["decision"],"PAS")
            self.assertEqual(report["picks"],[])

if __name__=="__main__": unittest.main()
