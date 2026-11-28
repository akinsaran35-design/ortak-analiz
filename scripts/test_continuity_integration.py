"""Offline multi-stage continuity regression. All providers simulated; no paid requests."""
import io,json,os,runpy,tempfile,unittest
from datetime import datetime,timedelta,timezone,date
from pathlib import Path
from unittest.mock import patch
from league_config import ODDS_CODES,FIXTURE_CODES
from test_optional_odds_refresh import Response
from results_source_pilot import TR
import turkey_source
import football_history_cache as cache

SCRIPTS=Path(__file__).resolve().parent
def run(name):runpy.run_path(str(SCRIPTS/(name+".py")),run_name="__main__")
def load(name):return json.loads(Path(name+".json").read_text())

class ContinuityIntegration(unittest.TestCase):
    def test_zero_credit_independent_fixtures_history_and_recovery(self):
        now=datetime.now(TR)
        today=now.date()
        year=today.year if today.month>=7 else today.year-1
        season=f"{year}-{(year+1)%100:02d}"
        previous=f"{year-1}-{year%100:02d}"
        target=today+timedelta(days=1)
        kickoff=datetime.combine(target,datetime.min.time(),tzinfo=TR)+timedelta(hours=18)
        sport=list(ODDS_CODES.values())[0]
        leagues=list(ODDS_CODES.values())
        at=(now-timedelta(hours=2)).isoformat()
        old=dict(source="The Odds API",region="uk",market="totals",configuredLeagues=leagues,
            queriedLeagues=[sport],inactiveLeagues=leagues[1:],errors=[],updatedAt=at,
            eventCount=1,remainingCredits=30,events=[dict(id="old",league=sport,home="A en.1",away="B en.1",
                kickoff=kickoff.isoformat(),bookmakers=[dict(key="archive",lines=[dict(point=2.5,over=1.8,under=2,lastUpdate=at)])])])
        def scores(code,dates):
            return [dict(date=d.isoformat(),team1="A "+code,team2="B "+code,score={"ft":[2,1]}) for d in dates]
        prior=[date(year,6,20)-timedelta(days=i) for i in range(5)]
        current=[today-timedelta(days=i) for i in range(1,6) if today-timedelta(days=i)>=date(year,7,1)]
        event=dict(id="123",date=kickoff.isoformat(),competitions=[dict(date=kickoff.isoformat(),
            status={"type":{"name":"STATUS_SCHEDULED","completed":False}},
            competitors=[dict(homeAway="home",team={"displayName":"Galatasaray"}),dict(homeAway="away",team={"displayName":"Fenerbahce"})])])
        def openfootball(req,timeout):
            url=req.full_url
            code=url.split("/")[-1].removesuffix(".json")
            if code=="en.1" and "/"+previous+"/" in url:raise OSError("simulated previous season outage")
            rows=scores(code,current if "/"+season+"/" in url else prior)
            if "/"+season+"/" in url:rows.append(dict(date=target.isoformat(),team1="A "+code,team2="B "+code))
            return io.BytesIO(json.dumps({"matches":rows}).encode())
        def turkey_reader(url,timeout):
            if "football-data.co.uk" in url:
                dates=current if "/"+str(year%100).zfill(2)+str((year+1)%100).zfill(2)+"/" in url else prior
                # Turkey CSV requires at least one completed result in its season.
                if not dates:raise OSError("no current historical results")
                body="Date,HomeTeam,AwayTeam,FTHG,FTAG\n"+"".join(f"{d:%d/%m/%Y},Galatasaray,Fenerbahce,2,1\n" for d in dates)
                return io.BytesIO(body.encode())
            if "site.api.espn.com" in url:
                return io.BytesIO(json.dumps({"events":[event] if url.endswith(target.strftime("%Y%m%d")) else []}).encode())
            raise AssertionError("unexpected Turkey URL")
        cwd=Path.cwd()
        with tempfile.TemporaryDirectory() as temp:
            try:
                os.chdir(temp)
                Path("odds.json").write_text(json.dumps(old))
                archive=cache.read()
                self.assertTrue(cache.remember(archive,"en.1",previous,scores("en.1",prior),now))
                cache.write(archive,now,FIXTURE_CODES.values(),[season,previous])
                with patch.dict(os.environ,{"ODDS_API_KEY":"offline-test","ODDS_OPTIONAL_REFRESH":"false"}):
                    with patch("urllib.request.urlopen",return_value=Response([{"key":sport,"active":True}],0)) as mocked:
                        run("fetch_odds")
                        self.assertEqual(mocked.call_count,1)
                        self.assertIn("/sports/?",mocked.call_args.args[0])
                    self.assertEqual(load("odds_continuity")["mode"],"fallback")
                    self.assertEqual(load("odds_last_good"),old)
                    with patch("urllib.request.urlopen",side_effect=AssertionError("extra requests forbidden")) as blocked:
                        run("fetch_extra_markets")
                        blocked.assert_not_called()
                    self.assertEqual(load("extra_markets")["paidRequestsAttempted"],0)
                    with patch("urllib.request.urlopen",side_effect=openfootball),patch.object(turkey_source,"urlopen",side_effect=turkey_reader),patch.object(turkey_source,"ROOT",Path(temp)):
                        run("daily_analysis")
                    daily=load("daily")
                    self.assertGreater(daily["candidateCount"],0)
                    self.assertEqual(daily["picks"],[])
                    epl=next(d for d in daily["leagueDiagnostics"] if d["league"]=="İngiltere Premier Lig")
                    self.assertIn(previous,epl["cachedHistoricalSeasons"])
                    self.assertTrue(any(c["historyCacheUsed"] for c in daily["candidates"] if c["league"]=="İngiltere Premier Lig"))
                    if current:
                        turkey=next(d for d in daily["leagueDiagnostics"] if d["league"]=="Türkiye Süper Lig")
                        self.assertEqual(turkey["fixtureScope"],"independent_espn_fallback")
                        self.assertTrue(any(c["league"]=="Türkiye Süper Lig" and c["date"]==target.isoformat() for c in daily["upcoming"]))
                    for name in ("match_odds","market_analysis","market_analysis_15","market_movement","model_market"):
                        run(name)
                    self.assertEqual(load("matching")["matchedCount"],0)
                    for name in ("market_analysis","market_analysis_15","model_market"):
                        self.assertEqual(load(name)["comparedCount"],0)
                        self.assertEqual(load(name)["decision"],"PAS")
                    self.assertEqual(load("model_market")["errors"],[])
                    self.assertFalse(load("model_market")["realBettingEnabled"])
                    def recovered(url,timeout):
                        if "/sports/?" in url:return Response([{"key":sport,"active":True}],100)
                        stamp=datetime.now(timezone.utc).isoformat()
                        raw=dict(id="new",sport_key=sport,home_team="A en.1",away_team="B en.1",commence_time=kickoff.isoformat(),
                            bookmakers=[dict(key=k,title=k,markets=[dict(key="totals",last_update=stamp,outcomes=[dict(name="Over",point=2.5,price=1.9),dict(name="Under",point=2.5,price=1.9)])]) for k in ("a","b","c")])
                        return Response([raw],99)
                    with patch("urllib.request.urlopen",side_effect=recovered) as recovered_calls:
                        run("fetch_odds")
                        self.assertEqual(recovered_calls.call_count,2)
                    self.assertEqual(load("odds_continuity")["mode"],"normal")
                    self.assertTrue(load("odds_continuity")["currentOddsUsable"])
                    self.assertEqual(load("odds_last_good")["events"][0]["id"],"new")
                    run("match_odds")
                    self.assertEqual(load("matching")["matchedCount"],1)
                    self.assertEqual(load("matching")["matched"][0]["eventId"],"new")
                    run("model_market")
                    self.assertEqual(load("model_market")["decision"],"PAS")
            finally:os.chdir(cwd)

if __name__=="__main__":unittest.main()
