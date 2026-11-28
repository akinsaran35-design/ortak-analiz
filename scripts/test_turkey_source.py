import unittest
from datetime import datetime, timezone, timedelta
from turkey_source import parse_results, fixtures, team_key, SPORT, fallback_fixtures, espn_fixtures
from match_odds import canonical

class TurkeySourceTest(unittest.TestCase):
    def test_results(self):
        data="Date,HomeTeam,AwayTeam,FTHG,FTAG\n15/08/2026,Galatasaray,Fenerbahce,0,0\n16/08/2026,Besiktas,Trabzonspor,,\n"
        rows=parse_results(data.encode(),"2026-27")
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["score"]["ft"],[0,0])
        self.assertEqual(rows[0]["date"],"2026-08-15")
    def test_aliases(self):
        self.assertEqual(team_key("İstanbul Başakşehir"),team_key("Basaksehir"))
        self.assertEqual(canonical("Beşiktaş JK",SPORT),canonical("Besiktas",SPORT))
        self.assertNotEqual(team_key("Galatasaray"),team_key("Fenerbahçe"))
    def test_historical_club_names(self):
        self.assertEqual(team_key("Torku Konyaspor"),team_key("Konyaspor"))
        self.assertEqual(team_key("Gazişehir Gaziantep"),team_key("Gaziantep FK"))
        self.assertEqual(team_key("Gazişehir Gaziantep FK"),team_key("Gaziantep"))
        self.assertNotEqual(team_key("Gaziantepspor"),team_key("Gaziantep FK"))
    def test_fixtures(self):
        now=datetime(2026,11,26,13,tzinfo=timezone.utc)
        snapshot=dict(updatedAt=now.isoformat(),source="The Odds API",region="uk",queriedLeagues=[SPORT],events=[
            dict(league=SPORT,kickoff="2026-11-28T22:00:00Z",home="Galatasaray",away="Fenerbahçe"),
            dict(league=SPORT,kickoff="2026-11-25T22:00:00Z",home="Galatasaray",away="Fenerbahçe")])
        self.assertEqual(fixtures(snapshot,now),[dict(date="2026-11-29",team1="galatasaray",team2="fenerbahce")])
        self.assertEqual(fixtures(snapshot,now+timedelta(minutes=31)),[])
        self.assertEqual(fixtures(dict(snapshot,queriedLeagues=[]),now),[])
    def test_independent_fixtures_and_outage(self):
        now=datetime(2026,11,26,13,tzinfo=timezone.utc)
        day=now.astimezone(timezone(timedelta(hours=3))).date()
        e=dict(id="123",date="2026-11-26T17:00:00Z",competitions=[dict(date="2026-11-26T17:00:00Z",status={"type":{"name":"STATUS_SCHEDULED","completed":False}},competitors=[{"homeAway":"home","team":{"displayName":"Galatasaray"}},{"homeAway":"away","team":{"displayName":"Fenerbahçe"}}])])
        payload={"events":[e]}
        rows=fallback_fixtures(now,lambda d:payload if d==day else {"events":[]})
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["fixtureSource"],"ESPN")
        self.assertNotIn("score",rows[0])
        self.assertEqual(fallback_fixtures(now,lambda d:{"events":[e,e]} if d==day else {"events":[]}),[])
        self.assertEqual(espn_fixtures(payload,day,now+timedelta(hours=5)),[])
        def fail(d):raise OSError("offline")
        self.assertEqual(fallback_fixtures(now,fail),[])
        e["competitions"][0]["status"]["type"]["name"]="STATUS_POSTPONED"
        self.assertEqual(espn_fixtures(payload,day,now),[])
    def test_conflicting_scores(self):
        data="Date,HomeTeam,AwayTeam,FTHG,FTAG\n15/08/2026,A,B,1,0\n15/08/2026,A,B,2,0\n16/08/2026,C,D,0,0\n"
        self.assertEqual(len(parse_results(data.encode(),"2026-27")),1)

if __name__=="__main__": unittest.main()
