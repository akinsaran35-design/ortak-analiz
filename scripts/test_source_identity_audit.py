import unittest
from datetime import date
from source_identity_audit import inspect
class Tests(unittest.TestCase):
    def test_exact_only(self):
        raw=b"Date,HomeTeam,AwayTeam,FTHG,FTAG\n21/11/2026,Arsenal,Man City,1,0\n27/11/2026,Arsenal,Unknown,2,1\n"
        r=inspect(raw,[dict(match="Arsenal FC – Manchester City FC")],"en.1","soccer_epl",date(2026,11,27))
        self.assertEqual(r["completedMatches"],1)
        self.assertEqual(r["resolved"][0]["fixtureName"],"Arsenal FC")
        self.assertEqual(r["unresolved"][0]["fixtureName"],"Manchester City FC")
        self.assertEqual(r["unresolved"][0]["completedMatches"],0)
        self.assertEqual({x["canonicalKey"] for x in r["sourceTeams"]},{"arsenal","man city"})
    def test_empty(self):
        r=inspect(b"Date,HomeTeam,AwayTeam,FTHG,FTAG\n",[],"en.1","soccer_epl",date(2026,11,27))
        self.assertEqual(r["sourceTeams"],[])
if __name__=="__main__":unittest.main()
