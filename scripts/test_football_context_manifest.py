import copy,unittest
from football_context_manifest import audit,digest
from league_config import LEAGUES
from chronological_statistics_research import EVENTS
def fixture():
    stamp="2026-11-27T08:00:00+03:00"
    day="2026-11-27"
    d=dict(updatedAt=stamp,upcoming=[dict(league=LEAGUES[0][0],date=day,match="A – B")])
    def report(version,mode,groups):
        return dict(version=version,mode=mode,predictionsEnabled=False,decision="PAS",cutoffExclusive=day,dailyUpdatedAt=stamp,modelCalibrated=False,groups=groups)
    c=report("5.23","descriptive_research",[dict(league=code,error=None,rows=[]) for _,code,_ in LEAGUES])
    v=report("5.31","historical_metric_coverage_only",[dict(league=code,aggregate=dict(matches=1,metrics={"goals":dict(sample=1,missing=0)}),seasons=[dict(matches=1)]) for _,code,_ in LEAGUES])
    h=report("5.28","descriptive_research",[dict(league=code,rows=[]) for _,code,_ in LEAGUES])
    def empty_metric():
        return dict(sample=0,observedEvents=0,leagueBrier=None,venueBrier=None,seasonResults=[],reliability={method:dict(sample=0,bins=[dict(sample=0) for _ in range(10)]) for method in ("league","venue")})
    a=report("5.34","chronological_research_only",[dict(league=code,matches=1,metrics={event:empty_metric() for event in EVENTS}) for _,code,_ in LEAGUES])
    a["reliabilityDiagnosticOnly"]=True
    return d,c,v,h,a
class Tests(unittest.TestCase):
    def test_valid(self):
        r=audit(*fixture())
        self.assertEqual(r["status"],"PASS")
        self.assertEqual(r["coverageMatches"],len(LEAGUES))
        self.assertNotEqual(digest(b"a"),digest(b"b"))
    def test_stale(self):
        d,c,v,h,a=fixture();c["dailyUpdatedAt"]="2026-11-26T08:00:00+03:00"
        with self.assertRaises(ValueError):audit(d,c,v,h,a)
    def test_bad_counts(self):
        d,c,v,h,a=fixture();v["groups"][0]["aggregate"]["metrics"]["goals"]["sample"]=2
        with self.assertRaises(ValueError):audit(d,c,v,h,a)
    def test_fixture_identity(self):
        d,c,v,h,a=fixture();h["groups"][0]["rows"]=[dict(date="2026-11-27",match="Unknown")]
        with self.assertRaises(ValueError):audit(d,c,v,h,a)
    def test_bad_league_or_activation(self):
        d,c,v,h,a=fixture();c["groups"].pop()
        with self.assertRaises(ValueError):audit(d,c,v,h,a)
        d,c,v,h,a=fixture();v["predictionsEnabled"]=True
        with self.assertRaises(ValueError):audit(d,c,v,h,a)
    def test_validation_binding(self):
        d,c,v,h,a=fixture()
        a["groups"][0]["matches"]=2
        with self.assertRaises(ValueError):audit(d,c,v,h,a)
    def test_validation_counts(self):
        d,c,v,h,a=fixture()
        a["groups"][0]["metrics"][EVENTS[0]]["reliability"]["venue"]["sample"]=1
        with self.assertRaises(ValueError):audit(d,c,v,h,a)
if __name__=="__main__":unittest.main()
