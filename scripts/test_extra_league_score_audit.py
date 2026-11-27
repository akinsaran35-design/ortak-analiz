import unittest,json
from datetime import datetime
from extra_league_score_audit import audit_league,build,TR,team_key,unmatched_names,REVIEWED_ALIASES
class AuditTests(unittest.TestCase):
    def test_names_require_explicit_review_and_league_scope(self):
        from unittest.mock import patch
        with patch.dict(REVIEWED_ALIASES,{"sco.1":{"example town":"example town united"}},clear=True):
            self.assertEqual(team_key("sco.1","Example Town"),"example town united")
            self.assertEqual(team_key("bel.1","Example Town"),"example town")
            self.assertEqual(team_key("sco.1","Unrelated Town"),"unrelated town")
        rows=[dict(home="a",away="b",status="csv_only"),dict(home="a",away="c",status="espn_only"),dict(home="d",away="e",status="corroborated")]
        self.assertEqual(unmatched_names(rows),{"csv_only":["a","b"],"espn_only":["a","c"]})
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
        self.assertFalse(all_reports["archivesModified"])
        self.assertFalse(all_reports["predictionsEnabled"])
        self.assertFalse(all_reports["realBettingEnabled"])
        self.assertEqual(audit_league("bel.1","B1",now,lambda url:b"bad")["rows"],[])
if __name__=="__main__":unittest.main()
