import unittest
from datetime import datetime,timedelta
from live_performance_research import archive,evaluate
from live_score_scenario import scenario
from results_source_pilot import TR
NOW=datetime(2026,11,26,21,0,tzinfo=TR)
def report():
    return dict(mode="live_link_research_only",predictionsEnabled=False,updatedAt=NOW.isoformat(),prematchUpdatedAt=(NOW-timedelta(hours=2)).isoformat(),rows=[dict(league="en.1",eventId="123",home="A",away="B",kickoff=(NOW-timedelta(hours=1)).isoformat(),receivedAt=NOW.isoformat(),status="conditional_scenario",scenario=scenario([1,0],54,1.5,1.2))])
def result():
    return dict(date=NOW.date().isoformat(),league="en.1",home="A",away="B",result=[2,0],sources=["https://one.example/a","https://two.example/b"])
class Tests(unittest.TestCase):
    def test_archive_immutable(self):
        a=archive(report(),{},NOW)
        self.assertEqual(len(a),1)
        r=report();r["rows"][0]["scenario"]=scenario([2,0],70,1.5,1.2)
        self.assertEqual(archive(r,a,NOW),a)
        self.assertEqual(archive(report(),{},NOW+timedelta(seconds=121)),{})
    def test_evaluation(self):
        a=archive(report(),{},NOW)
        self.assertEqual(evaluate(a,[result()],NOW)["counts"],{"pending":1})
        x=evaluate(a,[result()],NOW+timedelta(days=1))
        self.assertEqual(x["counts"],{"evaluated":1})
        self.assertAlmostEqual(x["brier"]["homeWin"],(1-a["en.1:123"]["probabilities"]["homeWin"])**2)
    def test_conflicts(self):
        a=archive(report(),{},NOW)
        r=result();r["result"]=[0,0]
        self.assertEqual(evaluate(a,[r,result()],NOW+timedelta(days=1))["counts"],{"conflict":1})
        self.assertEqual(evaluate(a,[r],NOW+timedelta(days=1))["counts"],{"score_conflict":1})
        r=result();r["sources"]=["https://one.example/a"]
        self.assertEqual(evaluate(a,[r],NOW+timedelta(days=1))["counts"],{"pending":1})
    def test_duplicate_and_missing(self):
        r=report();r["rows"]*=2
        self.assertEqual(archive(r,{},NOW),{})
        self.assertIsNone(evaluate({},[],NOW)["brier"]["homeWin"])
if __name__=="__main__":unittest.main()
