import unittest,json
from datetime import datetime
from extra_league_score_audit import audit_league,build,TR
class AuditTests(unittest.TestCase):
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
