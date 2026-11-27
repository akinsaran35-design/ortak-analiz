import unittest
from datetime import date
from historical_referee_coverage import season_report
class Tests(unittest.TestCase):
    def test_label_and_season_cutoff(self):
        header="Date,HomeTeam,AwayTeam,FTHG,FTAG,Referee,HY,AY,HR,AR\n"
        rows="".join(f"{i:02d}/08/2026,A,B,1,0,Ref A,2,3,0,0\n" for i in range(1,6))
        rows+="06/08/2026,A,B,1,0,,1,1,0,0\n01/08/2025,A,B,1,0,Ref A,3,4,0,0\n27/11/2026,A,B,1,0,Ref A,9,9,0,0\n"
        r=season_report((header+rows).encode(),"en.1","soccer_epl",2026,date(2026,11,27))
        self.assertEqual(r["completedMatches"],6)
        self.assertEqual(r["assignedFixtures"],5)
        self.assertEqual(r["labels"][0]["matches"],5)
        self.assertEqual(r["labels"][0]["yellowCards"]["totalAverage"],5)
    def test_missing_referee_column(self):
        r=season_report(b"Date,HomeTeam,AwayTeam,FTHG,FTAG\n01/08/2026,A,B,1,0\n","en.1","soccer_epl",2026,date(2026,11,27))
        self.assertEqual(r["assignedFixtures"],0)
        self.assertEqual(r["labels"],[])
    def test_conflicting_label(self):
        r=season_report(b"Date,HomeTeam,AwayTeam,FTHG,FTAG,Referee\n01/08/2026,A,B,1,0,Ref A\n01/08/2026,A,B,1,0,Ref B\n","en.1","soccer_epl",2026,date(2026,11,27))
        self.assertEqual(r["ambiguousFixtures"],1)
        self.assertEqual(r["assignedFixtures"],0)
if __name__=="__main__":unittest.main()
