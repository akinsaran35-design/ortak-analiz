"""Exercise daily coverage without any external network or quota use."""
import io
import os
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
        rows += [{"date":(datetime.now(tr).date()-timedelta(days=j+1)).isoformat(),"team1":f"Home {i}","team2":f"Away {i}","score":{"ft":[2,1]}} for i in range(12) for j in range(5)]
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
                cwd=Path.cwd()
                try:
                    os.chdir(d)
                    with patch("urllib.request.urlopen", side_effect=fake), patch.object(Path,"write_text",write), patch("turkey_source.fetch",return_value=rows):
                        runpy.run_path(str(SCRIPT))
                finally:os.chdir(cwd)
                report=json.loads(target.read_text())
            self.assertEqual(report["upcomingCount"], 96 if partial else 108)
            self.assertEqual(report["upcomingCount"],len(report["upcoming"]))
            self.assertEqual(report["upcomingCountsByDate"][date],report["upcomingCount"])
            self.assertFalse(report["fixtureCoverageComplete"])
            self.assertEqual(report["candidateCount"],96 if partial else 108)
            self.assertEqual(len(report["candidates"]),report["candidateCount"])
            self.assertTrue(report["candidateListComplete"])
            self.assertIsNone(report["candidateListLimit"])
            self.assertEqual(report["decision"],"PAS")
            self.assertEqual(report["picks"],[])

    def test_history_cache_only_past_scores_and_expiry(self):
        import football_history_cache as cache
        now=datetime(2026,11,28,12,tzinfo=timezone.utc)
        doc={"version":"6.96","seasons":{}}
        rows=[dict(date="2026-11-27",team1="A",team2="B",score={"ft":[2,0]}),dict(date="2026-11-28",team1="C",team2="D",score={"ft":[1,1]}),dict(date="2026-11-29",team1="E",team2="F")]
        self.assertTrue(cache.remember(doc,"en.1","2026-27",rows,now))
        recovered,stamp=cache.recover(doc,"en.1","2026-27",now+timedelta(hours=1))
        self.assertEqual(len(recovered),1)
        self.assertEqual(recovered[0]["score"]["ft"],[2,0])
        self.assertEqual(stamp,now.isoformat())
        self.assertEqual(cache.recover(doc,"en.1","2026-27",now+timedelta(hours=73)),([],None))
        self.assertEqual(cache.recover(doc,"de.1","2026-27",now),([],None))
        self.assertFalse(cache.remember(doc,"en.1","2026-27",rows[1:],now))
if __name__=="__main__": unittest.main()
