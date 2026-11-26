import unittest
from datetime import datetime
from nine_league_results_pilot import SOURCES,compare_day,probe,TR
from league_config import LEAGUES
import json

class NineLeagueTests(unittest.TestCase):
    def test_coverage(self):
        self.assertEqual(set(SOURCES),{code for _,code,_ in LEAGUES})
    def test_comparison(self):
        d="2026-11-25"
        k=(d,"a","b"); k2=(d,"c","d"); k3=(d,"e","f")
        rows=compare_day({k:[1,0],k2:[2,0]},{k:[1,0],k2:[0,2],k3:[0,0]},d)
        self.assertEqual([r["status"] for r in rows],["corroborated","conflict","espn_only"])
    def test_probe(self):
        now=datetime(2026,11,26,17,tzinfo=TR)
        event={"date":"2026-11-25T18:00:00Z","competitions":[{"status":{"type":{"completed":True,"name":"STATUS_FULL_TIME"}},"competitors":[{"homeAway":"home","team":{"displayName":"A"},"score":"1"},{"homeAway":"away","team":{"displayName":"B"},"score":"0"}]}]}
        def read(url):
            if url.endswith("/D1.csv"): return b"Date,HomeTeam,AwayTeam,FTHG,FTAG\n25/11/26,A,B,1,0\n"
            self.assertIn("/ger.1/scoreboard?dates=20261125",url)
            return json.dumps({"events":[event]}).encode()
        report=probe("de.1","soccer_germany_bundesliga",now,read)
        self.assertEqual(report["rows"][0]["status"],"corroborated")
        self.assertEqual(report["errors"],[])
        self.assertEqual(probe("de.1","soccer_germany_bundesliga",now,lambda url:b"bad")["rows"],[])
if __name__=="__main__": unittest.main()
