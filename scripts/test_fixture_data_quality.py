import unittest
from datetime import date
from fixture_data_quality import form_status,build,METRICS
from league_config import LEAGUES
D=date(2026,11,27)
def side(day,n=5):
    return dict(sample=n,rows=[dict(date=day)]*n)
def fixture():
    stamp="2026-11-27T07:00:00+03:00"; label,code,_=LEAGUES[0]
    f=dict(date=D.isoformat(),league=label,match="A – B",formResearch=dict(asOfExclusive=D.isoformat(),home=side("2026-11-22"),away=side("2026-09-20"),h2h=[]))
    d=dict(updatedAt=stamp,upcoming=[f])
    c=dict(dailyUpdatedAt=stamp,groups=[dict(league=c,latestCompletedDate="2026-11-22",rows=[]) for _,c,_ in LEAGUES])
    s=dict(dailyUpdatedAt=stamp,groups=[dict(league=c,rows=[]) for _,c,_ in LEAGUES])
    return d,c,s
class Tests(unittest.TestCase):
    def test_form_status(self):
        self.assertEqual(form_status(side("2026-11-22"),D)["status"],"available")
        self.assertEqual(form_status(side("2026-09-20"),D)["status"],"stale")
        self.assertEqual(form_status(side("2026-11-22",3),D)["status"],"partial")
        self.assertEqual(form_status(side("2026-11-22",0),D)["status"],"missing")
        self.assertEqual(form_status(side("2026-11-27"),D)["status"],"invalid")
    def test_report(self):
        r=build(*fixture());g=r["groups"][0]
        self.assertEqual(g["fixtures"],1)
        self.assertEqual(g["flags"]["awayForm:stale"],1)
        self.assertEqual(g["flags"]["h2h:missing"],1)
        self.assertEqual(g["flags"]["overall:home:corners:missing"],1)
        self.assertFalse(r["predictionsEnabled"])
    def test_snapshot_mismatch(self):
        d,c,s=fixture();s["dailyUpdatedAt"]="old"
        with self.assertRaises(ValueError):build(d,c,s)
    def test_samples(self):
        d,c,s=fixture()
        x=dict(date=D.isoformat(),match="A – B")
        m=dict(metrics={k:dict(sample=5) for k in METRICS})
        s["groups"][0]["rows"]=[dict(x,home=m,away=m)]
        c["groups"][0]["rows"]=[dict(x,homeVenue=m,awayVenue=m)]
        g=build(d,c,s)["groups"][0]
        self.assertEqual(set(g["flags"]),{"awayForm:stale","h2h:missing"})
if __name__=="__main__":unittest.main()
