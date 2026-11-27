import copy,unittest
from football_context_manifest import audit,digest
from league_config import LEAGUES
def fixture():
    stamp="2026-11-27T08:00:00+03:00"
    day="2026-11-27"
    d=dict(updatedAt=stamp,upcoming=[dict(league=LEAGUES[0][0],date=day,match="A – B")])
    def report(version,mode,groups):
        return dict(version=version,mode=mode,predictionsEnabled=False,decision="PAS",cutoffExclusive=day,dailyUpdatedAt=stamp,modelCalibrated=False,groups=groups)
    c=report("5.23","descriptive_research",[dict(league=code,error=None,rows=[]) for _,code,_ in LEAGUES])
    v=report("5.31","historical_metric_coverage_only",[dict(league=code,aggregate=dict(matches=1,metrics={"goals":dict(sample=1,missing=0)}),seasons=[dict(matches=1)]) for _,code,_ in LEAGUES])
    h=report("5.28","descriptive_research",[dict(league=code,rows=[]) for _,code,_ in LEAGUES])
    return d,c,v,h
class Tests(unittest.TestCase):
    def test_valid(self):
        r=audit(*fixture())
        self.assertEqual(r["status"],"PASS")
        self.assertEqual(r["coverageMatches"],len(LEAGUES))
        self.assertNotEqual(digest(b"a"),digest(b"b"))
    def test_stale(self):
        d,c,v,h=fixture();c["dailyUpdatedAt"]="2026-11-26T08:00:00+03:00"
        with self.assertRaises(ValueError):audit(d,c,v,h)
    def test_bad_counts(self):
        d,c,v,h=fixture();v["groups"][0]["aggregate"]["metrics"]["goals"]["sample"]=2
        with self.assertRaises(ValueError):audit(d,c,v,h)
    def test_fixture_identity(self):
        d,c,v,h=fixture();h["groups"][0]["rows"]=[dict(date="2026-11-27",match="Unknown")]
        with self.assertRaises(ValueError):audit(d,c,v,h)
    def test_bad_league_or_activation(self):
        d,c,v,h=fixture();c["groups"].pop()
        with self.assertRaises(ValueError):audit(d,c,v,h)
        d,c,v,h=fixture();v["predictionsEnabled"]=True
        with self.assertRaises(ValueError):audit(d,c,v,h)
if __name__=="__main__":unittest.main()
