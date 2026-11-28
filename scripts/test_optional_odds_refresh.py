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
    def test_archive_survives_outage_and_recovery(self):
        from odds_continuity import record,valid
        cwd=Path.cwd()
        with tempfile.TemporaryDirectory() as temp:
            try:
                os.chdir(temp)
                now=datetime.now(timezone.utc)
                league=list(ODDS_CODES.values())[0]
                stamp=(now-timedelta(hours=2)).isoformat()
                def snapshot(at):
                    return dict(source="The Odds API",region="uk",market="totals",errors=[],configuredLeagues=list(ODDS_CODES.values()),queriedLeagues=[league],inactiveLeagues=list(ODDS_CODES.values())[1:],updatedAt=at,eventCount=1,events=[dict(id="a",home="A",away="B",league=league,kickoff=(now+timedelta(hours=2)).isoformat(),bookmakers=[dict(key="b",lines=[dict(point=2.5,over=1.8,under=2.0,lastUpdate=at)])])])
                old=snapshot(stamp)
                self.assertTrue(valid(old,now))
                Path("odds.json").write_text(json.dumps(old))
                with patch.dict(os.environ,{"ODDS_API_KEY":"test","ODDS_OPTIONAL_REFRESH":"false"}),patch("urllib.request.urlopen",side_effect=OSError("offline")):
                    runpy.run_path(str(MODULE))
                self.assertEqual(json.loads(Path("odds_last_good.json").read_text()),old)
                self.assertEqual(json.loads(Path("odds.json").read_text())["events"],[])
                status=json.loads(Path("odds_continuity.json").read_text())
                self.assertEqual(status["mode"],"fallback")
                self.assertFalse(status["currentOddsUsable"])
                self.assertEqual(status["lastGoodAt"],stamp)
                new=snapshot(now.isoformat())
                self.assertEqual(record(new,old,now,"collected",100)["mode"],"normal")
                self.assertEqual(json.loads(Path("odds_last_good.json").read_text()),new)
                record(old,None,now,"source_error",0)
                self.assertEqual(json.loads(Path("odds_last_good.json").read_text()),new)
            finally:os.chdir(cwd)
    def test_recent_cache_requires_full_validation(self):
        cwd=Path.cwd()
        with tempfile.TemporaryDirectory() as temp:
            try:
                os.chdir(temp)
                now=datetime.now(timezone.utc)
                leagues=list(ODDS_CODES.values())
                stamp=(now-timedelta(minutes=5)).isoformat()
                snapshot=dict(source="The Odds API",region="uk",market="totals",errors=[],
                    configuredLeagues=leagues,queriedLeagues=leagues[:1],inactiveLeagues=leagues[1:],
                    updatedAt=stamp,eventCount=1,remainingCredits=50,
                    events=[dict(id="a",home="A",away="B",league=leagues[0],
                        kickoff=(now+timedelta(hours=2)).isoformat(),
                        bookmakers=[dict(key="b",lines=[dict(point=2.5,over=1.8,under=2.0,lastUpdate=stamp)])])])
                with patch.dict(os.environ,{"ODDS_API_KEY":"test","ODDS_OPTIONAL_REFRESH":"false"}):
                    Path("odds.json").write_text(json.dumps(snapshot))
                    with patch("urllib.request.urlopen",side_effect=AssertionError("unexpected request")) as mock:
                        with self.assertRaises(SystemExit) as stop:runpy.run_path(str(MODULE))
                        self.assertEqual(stop.exception.code,0)
                        mock.assert_not_called()
                    self.assertEqual(json.loads(Path("odds_continuity.json").read_text())["mode"],"normal")
                    # A recent but incomplete snapshot must not short-circuit a safe refresh.
                    for corruption in ("event_count","invalid_price","missing_coverage"):
                        with self.subTest(corruption=corruption):
                            broken=json.loads(json.dumps(snapshot))
                            if corruption=="event_count":broken["eventCount"]=99
                            elif corruption=="invalid_price":broken["events"][0]["bookmakers"][0]["lines"][0]["over"]=0
                            else:broken["inactiveLeagues"]=[]
                            Path("odds.json").write_text(json.dumps(broken))
                            with patch("urllib.request.urlopen",return_value=Response([{"key":leagues[0],"active":True}],0)) as mock:
                                runpy.run_path(str(MODULE))
                                self.assertEqual(mock.call_count,1)
                                self.assertIn("/sports/?",mock.call_args.args[0])
                            status=json.loads(Path("odds_continuity.json").read_text())
                            self.assertFalse(status["currentOddsUsable"])
                            self.assertEqual(status["mode"],"fallback")
                            self.assertEqual(json.loads(Path("odds_last_good.json").read_text()),snapshot)
            finally:os.chdir(cwd)
    def test_partial_snapshot_isolated_from_legacy_market_reports(self):
        cwd=Path.cwd()
        with tempfile.TemporaryDirectory() as temp:
            try:
                os.chdir(temp)
                now=datetime.now(timezone.utc)
                stamp=now.isoformat()
                kickoff=(now+timedelta(hours=2)).isoformat()
                event=dict(id="e",kickoff=kickoff,bookmakers=[
                    dict(key=k,lines=[dict(point=p,over=1.9,under=1.9,lastUpdate=stamp)
                        for p in (1.5,2.5)]) for k in ("a","b","c")])
                Path("daily.json").write_text(json.dumps(dict(candidates=[
                    dict(match="A – B",markets={"1.5 Üst":65,"2.5 Üst":52})])))
                Path("matching.json").write_text(json.dumps(dict(matched=[
                    dict(match="A – B",eventId="e",kickoff=kickoff)])))
                for errors in ([],["quota_guard"],["soccer_epl: HTTP 429"],["duplicate_event_identity"]):
                    Path("odds.json").write_text(json.dumps(dict(updatedAt=stamp,events=[event],errors=errors)))
                    for name in ("market_analysis","market_analysis_15"):
                        runpy.run_path(str(MODULE.with_name(name+".py")),run_name="__main__")
                        report=json.loads(Path(name+".json").read_text())
                        self.assertEqual(report["comparedCount"],0 if errors else 1)
                        self.assertEqual(report["snapshotFresh"],not errors)
                        self.assertEqual(report["decision"],"PAS")
            finally:os.chdir(cwd)
if __name__=="__main__":unittest.main()
