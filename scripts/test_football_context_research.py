import unittest
from datetime import date,datetime
from football_context_research import build,league_summary,half_history,venue_context,referee_summary
from football_statistics_pilot import parse
CSV=b"Date,HomeTeam,AwayTeam,FTHG,FTAG,HC,AC,HY,AY,HR,AR,HTHG,HTAG,Referee\n20/11/2026,A,B,2,2,5,3,2,1,0,0,1,1,R One\n21/11/2026,B,A,0,1,4,6,,,0,0,0,0,R Two\n22/11/2026,A,C,2,1,6,2,3,1,0,0,1,0,R One\n26/11/2026,A,B,9,0,99,99,9,9,0,0,9,0,R One\n"
class Tests(unittest.TestCase):
    def rows(self,raw=CSV):return parse(raw,"en.1","soccer_epl",date(2026,11,26))[0]
    def test_league(self):
        r=league_summary(self.rows())
        self.assertEqual(r["goals"]["totalAverage"],8/3)
        self.assertEqual(r["yellowCards"]["sample"],2)
        self.assertEqual(r["yellowCards"]["totalAverage"],3.5)
        self.assertIsNone(league_summary([])["goals"]["totalAverage"])
    def test_halves(self):
        h=half_history(self.rows())
        self.assertEqual(h["sample"],3)
        self.assertEqual(h["counts"]["bothHalvesBtts"],1)
        self.assertEqual(h["counts"]["firstOver05"],2)
        self.assertEqual(h["counts"]["halfFull:X/2"],1)
        self.assertEqual(sum(v for k,v in h["counts"].items() if k.startswith("halfFull:")),3)
    def test_venue(self):
        h=venue_context(self.rows(),"a","home");a=venue_context(self.rows(),"a","away")
        self.assertEqual(h["goals"],dict(sample=2,forAverage=2,againstAverage=1.5))
        self.assertEqual(a["goals"],dict(sample=1,forAverage=1,againstAverage=0))
    def test_referees(self):
        r=referee_summary(CSV,self.rows(),"en.1","soccer_epl")
        self.assertEqual(r["assignedFixtures"],3)
        self.assertEqual(r["labels"],[])
        raw=CSV+b"20/11/2026,A,B,2,2,5,3,2,1,0,0,1,1,R Other\n"
        r=referee_summary(raw,self.rows(raw),"en.1","soccer_epl")
        self.assertEqual(r["ambiguousFixtures"],1)
        self.assertEqual(r["assignedFixtures"],2)
    def test_report(self):
        d=dict(updatedAt="2026-11-26T10:00:00+03:00",upcoming=[dict(date="2026-11-27",league="İngiltere Premier Lig",match="A – B")])
        r=build(d,datetime.fromisoformat("2026-11-26T18:00:00+03:00"),lambda _:CSV)
        self.assertEqual(len(r["groups"][0]["rows"]),1)
        self.assertFalse(r["predictionsEnabled"])
        self.assertFalse(r["groups"][0]["referees"]["upcomingAssignmentsVerified"])
if __name__=="__main__":unittest.main()
