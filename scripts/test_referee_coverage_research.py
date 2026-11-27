import unittest
from copy import deepcopy
from referee_coverage_research import extract,build
from datetime import datetime
F=dict(eventId="123",home="A",away="B",kickoff="2026-11-22T15:00:00+00:00",score=[2,1])
def payload():
    return dict(header={"competitions":[dict(id="123",date=F["kickoff"],competitors=[dict(homeAway="home",team=dict(id="1",displayName="A"),score="2"),dict(homeAway="away",team=dict(id="2",displayName="B"),score="1")],status=dict(type=dict(state="post",name="STATUS_FULL_TIME",completed=True)))]},gameInfo={"officials":[dict(displayName="Ref A",id="99",position=dict(name="Referee")),dict(displayName="Assistant B",position=dict(name="Assistant Referee"))]},boxscore={"teams":[dict(team=dict(id="1"),statistics=[dict(name="yellowCards",displayValue="2")]),dict(team=dict(id="2"),statistics=[dict(name="yellowCards",displayValue="3")])]})
class Tests(unittest.TestCase):
    def test_referee(self):
        r=extract(payload(),F)
        self.assertEqual(r["referee"],dict(label="Ref A",sourceId="99"))
        self.assertEqual(r["cards"],{"yellowCards":[2,3]})
    def test_missing_and_ambiguous(self):
        p=payload();p["gameInfo"]["officials"]=p["gameInfo"]["officials"][1:]
        self.assertEqual(extract(p,F)["status"],"missing")
        p=payload();p["gameInfo"]["officials"].append(dict(displayName="Ref B",position=dict(name="Referee")))
        self.assertEqual(extract(p,F)["status"],"ambiguous")
    def test_wrong_event_or_score(self):
        for f in (dict(F,eventId="456"),dict(F,score=[1,1]),dict(F,home="Other")):
            with self.assertRaises(ValueError):extract(payload(),f)
    def test_not_completed(self):
        p=payload();p["header"]["competitions"][0]["status"]["type"]["completed"]=False
        with self.assertRaises(ValueError):extract(p,F)
    def test_all_leagues_even_unavailable(self):
        def fail(_):raise OSError("offline")
        r=build(datetime.fromisoformat("2026-11-27T07:00:00+03:00"),fail)
        self.assertEqual(len(r["groups"]),9)
        self.assertTrue(all(g["errors"] and not g["rows"] for g in r["groups"]))
        self.assertFalse(r["predictionsEnabled"])
if __name__=="__main__":unittest.main()
