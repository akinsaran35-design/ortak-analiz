import unittest,json,copy
from datetime import datetime
from public_summary_coverage import inspect,probe,PILOT,lineup_quality
EVENT=dict(eventId="123",home="Alpha",away="Beta",kickoff="2026-11-28T12:00:00+00:00",state="pre",status="STATUS_SCHEDULED")
def sample():
    return dict(header=dict(id="123",competitions=[dict(id="123",date=EVENT["kickoff"],competitors=[
        dict(homeAway="home",team=dict(displayName="Alpha")),dict(homeAway="away",team=dict(displayName="Beta"))])]),
        rosters=[{"team":"private example"}],injuries=[],boxscore=dict(teams=[dict(statistics=[dict(name="expectedGoals",displayValue="0")])]))
class CoverageTests(unittest.TestCase):
    def test_shapes_and_privacy(self):
        doc=sample()
        r=inspect(doc,EVENT)
        self.assertEqual({k:v for k,v in r.items() if k!="lineupQuality"},dict(rosters="nonempty",injuries="empty",teamStatistics="nonempty",explicitXgFieldTeams=1))
        self.assertEqual(r["lineupQuality"]["status"],"unverified")
        del doc["injuries"]
        doc["rosters"]={}
        r=inspect(doc,EVENT)
        self.assertEqual(r["injuries"],"missing")
        self.assertEqual(r["rosters"],"unexpected_shape")
        self.assertNotIn("private example",str(r))
    def test_lineup_quality(self):
        teams=[dict(homeAway="home",team=dict(id="10")),dict(homeAway="away",team=dict(id="20"))]
        rosters=[dict(team=dict(id=tid),roster=[dict(athlete=dict(id=str(i+base)),starter=i<11) for i in range(15)])
                 for tid,base in (("10",100),("20",200))]
        r=lineup_quality(rosters,teams)
        self.assertEqual(r["status"],"source_reported_eleven")
        self.assertEqual(r["starterCounts"],[11,11])
        rosters[0]["roster"][0]["starter"]=None
        self.assertEqual(lineup_quality(rosters,teams)["starterCounts"],[None,11])
        rosters[1]["roster"][1]["athlete"]["id"]=rosters[1]["roster"][0]["athlete"]["id"]
        self.assertEqual(lineup_quality(rosters,teams)["teamsWithEleven"],0)
        rosters[1]["team"]["id"]="10"
        self.assertEqual(lineup_quality(rosters,teams)["status"],"unverified")
    def test_mismatch(self):
        for field,value in (("id","999"),("date","2026-11-28T12:01:00Z")):
            d=sample();d["header"]["competitions"][0][field]=value
            with self.assertRaises(ValueError):inspect(d,EVENT)
        d=sample();d["header"]["competitions"][0]["competitors"][0]["team"]["displayName"]="Other"
        with self.assertRaises(ValueError):inspect(d,EVENT)
    def test_budget(self):
        paths=[]
        def fixtures(day,reader,codes):
            self.assertEqual(codes,PILOT)
            row=dict(EVENT)
            if day=="2026-11-27":row.update(state="post",status="STATUS_FULL_TIME")
            return [dict(league=c,rows=[row,dict(row,eventId="456")]) for c in PILOT]
        def read(url):
            paths.append(url)
            return json.dumps(sample())
        r=probe(datetime.fromisoformat("2026-11-28T10:00:00+03:00"),read,fixtures)
        self.assertEqual(len(paths),6)
        self.assertEqual(r["requestsAttempted"],6)
        self.assertTrue(all(g["status"]=="checked" for g in r["groups"]))
        self.assertFalse(r["predictionsEnabled"])
        self.assertNotIn("private example",str(r))
if __name__=="__main__":unittest.main()
