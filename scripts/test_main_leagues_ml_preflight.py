import unittest
from datetime import datetime,date
from unittest.mock import patch
import main_leagues_ml_preflight as engine
from results_source_pilot import TR
from main_leagues_ml_preflight import fixtures,identity
class MainPreflightTests(unittest.TestCase):
    def test_alias_and_schedule(self):
        self.assertEqual(identity("en.1","Man United"),identity("en.1","Manchester United"))
        e=dict(id="123",date="2026-11-29T12:00:00Z",competitions=[dict(date="2026-11-29T12:00:00Z",
            status=dict(type=dict(name="STATUS_SCHEDULED",completed=False)),
            competitors=[dict(homeAway="home",team=dict(displayName="Manchester United")),dict(homeAway="away",team=dict(displayName="Liverpool"))])])
        now=datetime(2026,11,28,12,tzinfo=TR)
        f=fixtures(dict(events=[e]),"en.1",date(2026,11,29),now)
        self.assertEqual(len(f),1)
        self.assertEqual(f[0]["eventId"],"123")
        e["competitions"][0]["status"]["type"]["name"]="STATUS_FULL_TIME"
        self.assertEqual(fixtures(dict(events=[e]),"en.1",date(2026,11,29),now),[])
    def test_isolated_source_failure(self):
        now=datetime.now(TR)
        def fake_fetch(job,reader,end):
            code,_,year=job
            failed=code=="en.1" and year==2023
            return [],dict(league=code,season=year,error="OSError" if failed else None)
        def fake_fixture(code,day,now,reader):
            if code=="de.1":return [],dict(league=code,date=day.isoformat(),error="OSError")
            return [dict(league=code,date=day.isoformat())],None
        with patch.object(engine,"fetch_season",side_effect=fake_fetch),patch.object(engine,"fixture_batch",side_effect=fake_fixture):
            with self.assertRaises(ValueError):engine.collect(now)
            history,training,keys,games,diag=engine.collect(now,allow_partial=True)
        self.assertEqual(diag["excludedHistoricalLeagues"],["en.1"])
        self.assertEqual(diag["sourceSuccessful"],35)
        self.assertEqual(len(diag["fixtureSourceFailures"]),3)
        self.assertTrue(diag["partial"])
        self.assertTrue(games)
        self.assertFalse(any(f["league"] in ("en.1","de.1") for f in games))
    def test_fixture_batch_failure(self):
        now=datetime.now(TR)
        def fail(url):raise OSError("offline")
        games,error=engine.fixture_batch("en.1",now.date(),now,fail)
        self.assertEqual(games,[])
        self.assertEqual(error["league"],"en.1")
if __name__=="__main__":unittest.main()
