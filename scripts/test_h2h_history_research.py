import unittest
from datetime import date,datetime
from h2h_history_research import collect,enrich_fixture,build,SEASONS,LIMIT,refresh_form
CUT=date(2026,11,27)
def fixture(h2h=None):
    return dict(date="2026-11-28",league="İngiltere Premier Lig",match="A – B",formResearch=dict(version="5.06",asOfExclusive=CUT.isoformat(),h2h=h2h or [],home={"sample":5},away={"sample":5}))
def row(d,h="a",a="b",score=None):
    return dict(date=d,home=h,away=a,score=score or [2,1],stats={"halfTimeGoals":[1,0]})
class Tests(unittest.TestCase):
    def test_enrich_limit_orientation_and_cutoff(self):
        f=fixture()
        rows=[row(f"2025-11-{i:02d}","b","a") for i in range(1,16)]+[row("2026-11-27"),row("2025-11-16","a","c")]
        r=enrich_fixture(f,rows,"en.1","soccer_epl",CUT,[{"season":2025}],[])
        self.assertEqual(r["sample"],LIMIT)
        self.assertEqual(r["csvMatchesAvailable"],15)
        self.assertEqual(f["formResearch"]["h2h"][0]["home"],"B")
        self.assertEqual(f["formResearch"]["h2h"][0]["date"],"2025-11-15")
        self.assertEqual(f["formResearch"]["home"]["sample"],5)
    def test_conflict(self):
        f=fixture([dict(date="2025-11-01",home="A",away="B",score=[0,0])])
        r=enrich_fixture(f,[row("2025-11-01")],"en.1","soccer_epl",CUT,[],[])
        self.assertEqual(r["sample"],0)
        self.assertEqual(f["formResearch"]["h2hCoverage"]["conflictsExcluded"],1)
    def test_fallback(self):
        old=[dict(date="2025-11-01",home="A",away="B",score=[0,0])]
        f=fixture(old)
        r=enrich_fixture(f,[],"en.1","soccer_epl",CUT,[],[{"season":2026}])
        self.assertEqual(r["sample"],1)
        self.assertEqual(f["formResearch"]["h2h"],old)
    def test_season_bounds(self):
        def reader(url):
            year=2000+int(url.split("/")[-2][:2])
            return f"Date,HomeTeam,AwayTeam,FTHG,FTAG\n01/08/{year},A,B,2,1\n01/06/{year},A,B,9,9\n".encode()
        rows,sources,errors,_=collect("en.1","soccer_epl",CUT,reader)
        self.assertEqual(len(rows),SEASONS)
        self.assertEqual(len(sources),SEASONS)
        self.assertEqual(errors,[])
    def test_refresh_form(self):
        f=fixture()["formResearch"]
        f["home"]=dict(rows=[dict(date="2026-09-01",opponent="C",gf=1,ga=0,venue="home",result="W")],sample=1)
        rows=[row(f"2026-11-{i:02d}","b","a",[1,2]) for i in range(20,27)]
        rows.append(row("2026-11-27"))
        self.assertTrue(refresh_form(f,rows,"a","home","en.1","soccer_epl",CUT))
        self.assertEqual(f["home"]["sample"],5)
        self.assertEqual(f["home"]["goalsFor"],10)
        self.assertEqual(f["home"]["goalsAgainst"],5)
        self.assertEqual(f["home"]["wins"],5)
        self.assertEqual(f["home"]["rows"][0]["date"],"2026-11-26")
    def test_keep_fresher_original(self):
        f=fixture()["formResearch"]
        f["home"]=dict(rows=[dict(date="2026-11-26",opponent="C",gf=1,ga=0,venue="home",result="W")],sample=1)
        self.assertFalse(refresh_form(f,[row("2026-11-20")],"a","home","en.1","soccer_epl",CUT))
        self.assertEqual(f["home"]["rows"][0]["date"],"2026-11-26")
    def test_refresh_excludes_conflict(self):
        f=fixture()["formResearch"]
        f["home"]=dict(rows=[dict(date="2026-11-20",opponent="B",gf=1,ga=0,venue="home",result="W")],sample=1)
        self.assertTrue(refresh_form(f,[row("2026-11-20"),row("2026-11-21")],"a","home","en.1","soccer_epl",CUT))
        self.assertEqual(f["home"]["sample"],1)
        self.assertEqual(f["home"]["rows"][0]["date"],"2026-11-21")
    def test_stale(self):
        with self.assertRaises(ValueError):
            build(dict(updatedAt="2026-11-26T10:00:00+03:00"),datetime.fromisoformat("2026-11-27T07:00:00+03:00"))
if __name__=="__main__":unittest.main()
