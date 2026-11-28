import unittest
from datetime import date,datetime
from referee_coverage import observations,describe,build
HEADER="Date,HomeTeam,AwayTeam,FTHG,FTAG,HY,AY,HR,AR,Referee\n"
class RefereeTests(unittest.TestCase):
    def test_conflicting_missing_and_future_assignments(self):
        raw=(HEADER+"01/08/2026,A,B,1,0,2,3,0,1,Ref A\n"
             "02/08/2026,C,D,0,0,0,0,0,0,Ref B\n"
             "02/08/2026,C,D,0,0,0,0,0,0,Ref C\n"
             "03/08/2026,E,F,0,0,,,,,\n"
             "04/08/2026,G,H,1,1,,,,,Ref A\n"
             "29/11/2026,A,B,1,0,2,3,0,0,Ref Future\n").encode()
        total,rows,field,bad,_=observations(raw,"en.1","soccer_epl",date(2026,11,28),2026)
        self.assertEqual((total,len(rows),field,bad),(4,2,True,1))
        self.assertEqual(describe(rows)["yellowCards"],{"sample":1,"mean":5})
        self.assertEqual(describe(rows)["redCards"],{"sample":1,"mean":1})
    def test_missing_referee_column(self):
        raw=b"Date,HomeTeam,AwayTeam,FTHG,FTAG\n01/08/2026,A,B,0,0\n"
        n,rows,field,bad,_=observations(raw,"en.1","soccer_epl",date(2026,11,28),2026)
        self.assertEqual((n,rows,field,bad),(1,[],False,0))
    def test_scope_and_source_failure(self):
        def reader(url):
            y=2000+int(url.split("/")[-2][:2])
            return (HEADER+f"01/08/{y},A,B,1,0,0,0,0,0,Ref A\n").encode()
        report=build(datetime.fromisoformat("2026-11-28T14:00:00+03:00"),reader)
        self.assertEqual((len(report["groups"]),report["assignedMatches"],report["leaguesWithAssignments"]),(15,30,15))
        self.assertFalse(report["futureAssignmentsVerified"])
        self.assertEqual(report["groups"][0]["referees"][0]["yellowCards"]["mean"],0)
        def fail(url):raise OSError("unavailable")
        self.assertEqual(build(datetime.fromisoformat("2026-11-28T14:00:00+03:00"),fail)["assignedMatches"],0)

if __name__=="__main__":unittest.main()
