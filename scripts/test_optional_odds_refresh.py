import json,os,runpy,tempfile,unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path
from unittest.mock import patch
from io import BytesIO
from league_config import ODDS_CODES

MODULE=Path(__file__).resolve().with_name("fetch_odds.py")
class Response(BytesIO):
    def __init__(self,payload,remaining):
        super().__init__(json.dumps(payload).encode())
        self.headers={"x-requests-remaining":str(remaining)}

class OptionalRefreshTests(unittest.TestCase):
    def test_deferred_preserves_snapshot_and_avoids_paid_calls(self):
        cwd=Path.cwd()
        with tempfile.TemporaryDirectory() as temp:
            try:
                os.chdir(temp)
                Path(".github/workflows").mkdir(parents=True)
                Path(".github/workflows/daily.yml").write_text("    - cron: '0 5,15 * * *'\n    - cron: '10 8,11,13,18 * * 6,0'\n")
                stamp=(datetime.now(timezone.utc)-timedelta(hours=2)).isoformat()
                snapshot=dict(source="The Odds API",region="uk",market="totals",updatedAt=stamp,
                    configuredLeagues=list(ODDS_CODES.values()),errors=[],events=[{"id":"old"}],eventCount=1,remainingCredits=50)
                Path("odds.json").write_text(json.dumps(snapshot))
                with patch.dict(os.environ,{"ODDS_API_KEY":"test","ODDS_OPTIONAL_REFRESH":"true"}),patch("urllib.request.urlopen",return_value=Response([{"key":"soccer_epl","active":True}],21)) as mock:
                    with self.assertRaises(SystemExit) as stop:runpy.run_path(str(MODULE))
                    self.assertEqual(stop.exception.code,0)
                    self.assertEqual(mock.call_count,1)
                    self.assertIn("/sports/?",mock.call_args.args[0])
                self.assertEqual(json.loads(Path("odds.json").read_text()),snapshot)
                self.assertEqual(json.loads(Path("odds_source_status.json").read_text())["mode"],"fallback")
            finally:os.chdir(cwd)
    def test_core_zero_credit_no_paid_calls(self):
        cwd=Path.cwd()
        with tempfile.TemporaryDirectory() as temp:
            try:
                os.chdir(temp)
                with patch.dict(os.environ,{"ODDS_API_KEY":"test","ODDS_OPTIONAL_REFRESH":"false"}),patch("urllib.request.urlopen",return_value=Response([{"key":list(ODDS_CODES.values())[0],"active":True}],0)) as mock:
                    runpy.run_path(str(MODULE))
                    self.assertEqual(mock.call_count,1)
                report=json.loads(Path("odds.json").read_text())
                self.assertEqual(report["remainingCredits"],0)
                self.assertEqual(report["events"],[])
                self.assertIn("quota_guard",report["errors"])
            finally:os.chdir(cwd)
    def test_last_good_preserved_on_outage_and_recovery(self):
        cwd=Path.cwd()
        with tempfile.TemporaryDirectory() as temp:
            try:
                os.chdir(temp)
                league=list(ODDS_CODES.values())[0]
                old=datetime.now(timezone.utc)-timedelta(hours=2)
                event=dict(id="old",league=league,home="A",away="B",kickoff=(old+timedelta(days=1)).isoformat(),bookmakers=[dict(key="b",lines=[dict(point=2.5,over=1.9,under=2,lastUpdate=old.isoformat())])])
                snapshot=dict(source="The Odds API",region="uk",market="totals",updatedAt=old.isoformat(),configuredLeagues=list(ODDS_CODES.values()),queriedLeagues=[league],inactiveLeagues=list(ODDS_CODES.values())[1:],errors=[],events=[event],eventCount=1,remainingCredits=50)
                Path("odds.json").write_text(json.dumps(snapshot))
                with patch.dict(os.environ,{"ODDS_API_KEY":"test","ODDS_OPTIONAL_REFRESH":"false"}),patch("urllib.request.urlopen",side_effect=OSError("offline")):
                    runpy.run_path(str(MODULE))
                self.assertEqual(json.loads(Path("odds_last_good.json").read_text()),snapshot)
                status=json.loads(Path("odds_source_status.json").read_text())
                self.assertEqual(status["mode"],"fallback")
                self.assertFalse(status["currentOddsAvailable"])
                self.assertFalse(status["backupUsedAsCurrent"])
                self.assertEqual(json.loads(Path("odds.json").read_text())["events"],[])
                stamp=datetime.now(timezone.utc)
                fresh_event=dict(id="new",sport_key=league,home_team="A",away_team="B",commence_time=(stamp+timedelta(days=1)).isoformat(),bookmakers=[dict(key="b",markets=[dict(key="totals",last_update=stamp.isoformat(),outcomes=[dict(name="Over",point=2.5,price=1.9),dict(name="Under",point=2.5,price=2)])])])
                with patch.dict(os.environ,{"ODDS_API_KEY":"test","ODDS_OPTIONAL_REFRESH":"false"}),patch("urllib.request.urlopen",side_effect=[Response([{"key":league,"active":True}],50),Response([fresh_event],49)]):
                    runpy.run_path(str(MODULE))
                self.assertEqual(json.loads(Path("odds_source_status.json").read_text())["mode"],"normal")
                self.assertEqual(json.loads(Path("odds_last_good.json").read_text())["events"][0]["id"],"new")
            finally:os.chdir(cwd)
if __name__=="__main__":unittest.main()
