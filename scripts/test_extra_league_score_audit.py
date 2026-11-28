import unittest,json
from datetime import datetime,timedelta
from extra_league_score_audit import audit_league,build,TR,team_key,unmatched_names,REVIEWED_ALIASES,HISTORY_WINDOW_DAYS,SAMPLE_DATE_LIMIT,outcome_baseline,chronological_backtest
class AuditTests(unittest.TestCase):
    def test_names_require_explicit_review_and_league_scope(self):
        from unittest.mock import patch
        with patch.dict(REVIEWED_ALIASES,{"sco.1":{"example town":"example town united"}},clear=True):
            self.assertEqual(team_key("sco.1","Example Town"),"example town united")
            self.assertEqual(team_key("bel.1","Example Town"),"example town")
            self.assertEqual(team_key("sco.1","Unrelated Town"),"unrelated town")
        rows=[dict(home="a",away="b",status="csv_only"),dict(home="a",away="c",status="espn_only"),dict(home="d",away="e",status="corroborated")]
        self.assertEqual(unmatched_names(rows),{"csv_only":["a","b"],"espn_only":["a","c"]})
    def test_reviewed_names(self):
        for code,names in REVIEWED_ALIASES.items():
            for short,full in names.items():
                self.assertEqual(team_key(code,short),team_key(code,full))
                self.assertEqual(team_key("unrelated",short),short)
                self.assertNotEqual(short,full)
        self.assertNotEqual(team_key("esp.2","celta"),team_key("esp.2","celta b"))
        self.assertNotEqual(team_key("sco.1","dundee"),team_key("sco.1","dundee united"))
    def test_extended_history_window(self):
        now=datetime(2026,11,27,22,tzinfo=TR)
        self.assertEqual(HISTORY_WINDOW_DAYS,90)
        self.assertEqual(SAMPLE_DATE_LIMIT,90)
        dates=[now.date()-timedelta(days=d) for d in range(-1,92)]
        csv=("Date,HomeTeam,AwayTeam,FTHG,FTAG\n"+"".join(f"{d:%d/%m/%y},A,B,2,1\n" for d in dates)).encode()
        urls=[]
        def reader(url):
            urls.append(url)
            return csv if url.endswith(".csv") else b'{"events":[]}'
        report=audit_league("sco.1","SC0",now,reader)
        self.assertEqual(report["days"],[(now.date()-timedelta(days=d)).isoformat() for d in range(1,91)])
        self.assertEqual(len(urls),91)
        self.assertEqual(len(report["rows"]),90)
        self.assertTrue(all(r["status"]=="csv_only" for r in report["rows"]))
    def test_cross_season_history(self):
        now=datetime(2026,7,15,22,tzinfo=TR)
        def reader(url):
            if "/2526/" in url:
                return b"Date,HomeTeam,AwayTeam,FTHG,FTAG\n20/06/26,A,B,2,1\n"
            if "/2627/" in url:
                return b"Date,HomeTeam,AwayTeam,FTHG,FTAG\n10/07/26,C,D,1,0\n"
            return b'{"events":[]}'
        report=audit_league("sco.1","SC0",now,reader)
        self.assertEqual(report["days"],["2026-07-10","2026-06-20"])
        self.assertEqual(len(report["sourceUrls"]),4)
        self.assertFalse(report["errors"])
    def test_outcome_baseline(self):
        def row(home,score,status="corroborated",league="sco.1"):
            return dict(league=league,date="2026-11-25",home=home,away="z",csv=score,espn=score,status=status)
        rows=[row("a",[1,1]),row("b",[3,0]),row("c",[0,0]),row("d",[9,9],"conflict"),row("e",[2,2]),row("e",[2,2]),row("a",[0,1],league="bel.1"),row("f",[True,2])]
        result=outcome_baseline(rows)
        self.assertEqual(result["matches"],4)
        self.assertEqual(result["excludedRows"],4)
        self.assertEqual(result["markets"]["over15"],dict(occurred=2,ratePct=50.0))
        self.assertEqual(result["markets"]["over25"]["ratePct"],25.0)
        self.assertEqual(result["markets"]["btts"]["ratePct"],25.0)
        self.assertIsNone(result["predictionAccuracy"])
        self.assertIsNone(outcome_baseline([])["markets"]["btts"]["ratePct"])
    def test_chronological_backtest(self):
        def row(day,home,score,league="sco.1",status="corroborated"):
            return dict(league=league,date=day,home=home,away="z",csv=score,espn=score,status=status)
        rows=[row("2026-11-01",str(i),[0,0]) for i in range(19)]
        rows.extend([row("2026-11-02","a",[0,0]),row("2026-11-02","b",[0,0]),row("2026-11-03","c",[3,2]),row("2026-11-03","d",[0,0]),row("2026-11-03","e",[5,5],league="bel.1"),row("2026-11-03","f",[5,5],status="conflict")])
        result=chronological_backtest(rows)
        self.assertEqual(result["evaluatedMatches"],2)
        self.assertEqual(result["warmupMatches"],22)
        self.assertEqual(result["markets"]["over15"]["accuracyPct"],50.0)
        self.assertEqual(result["markets"]["over15"]["brier"],0.5)
        self.assertEqual(result["markets"]["btts"]["calibrationBins"][0]["meanProbability"],0.0)
        self.assertEqual(result,chronological_backtest(list(reversed(rows))))
        self.assertFalse(result["productionModelValidated"])
        self.assertIsNone(chronological_backtest([])["markets"]["btts"]["brier"])
    def test_scope_and_score_comparison(self):
        now=datetime(2026,11,27,22,tzinfo=TR)
        csv=b"Date,HomeTeam,AwayTeam,FTHG,FTAG\n25/11/26,A,B,2,1\n25/11/26,C,D,0,0\n25/11/26,E,F,1,0\n27/11/26,G,H,1,0\n"
        def event(h,a,score):
            return {"date":"2026-11-25T18:00:00Z","competitions":[{"status":{"type":{"completed":True,"name":"STATUS_FULL_TIME"}},"competitors":[{"homeAway":"home","team":{"displayName":h},"score":str(score[0])},{"homeAway":"away","team":{"displayName":a},"score":str(score[1])}]}]}
        def reader(url):
            if url.endswith(".csv"):return csv
            return json.dumps({"events":[event("A","B",[2,1]),event("C","D",[1,0]),event("X","Y",[3,0])]}).encode()
        report=audit_league("sco.1","SC0",now,reader)
        self.assertEqual(report["days"],["2026-11-25"])
        self.assertEqual([r["status"] for r in report["rows"]],["corroborated","conflict","csv_only","espn_only"])
        all_reports=build(now,reader)
        self.assertEqual(all_reports["corroborated"],6)
        self.assertEqual(all_reports["outcomeBaseline"]["matches"],6)
        self.assertEqual(all_reports["outcomeBaseline"]["markets"]["btts"]["ratePct"],100.0)
        self.assertFalse(all_reports["archivesModified"])
        self.assertFalse(all_reports["predictionsEnabled"])
        self.assertFalse(all_reports["realBettingEnabled"])
        self.assertEqual(audit_league("bel.1","B1",now,lambda url:b"bad")["rows"],[])
if __name__=="__main__":unittest.main()
