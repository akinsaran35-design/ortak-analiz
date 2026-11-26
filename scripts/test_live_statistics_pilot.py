import unittest,copy
from live_statistics_pilot import parse_summary,select_candidates
class Tests(unittest.TestCase):
    def test_identity_and_missing(self):
        f=dict(eventId="123",kickoff="2026-11-26T15:00:00+00:00",home="A",away="B")
        c=dict(id="123",date="2026-11-26T15:00:00Z",status={"type":{"state":"in","name":"STATUS_IN_PROGRESS"},"displayClock":"54'"},competitors=[{"homeAway":"home","team":{"id":"1","displayName":"A"},"score":"2"},{"homeAway":"away","team":{"id":"2","displayName":"B"},"score":"1"}])
        p={"header":{"competitions":[c]},"boxscore":{"teams":[{"team":{"id":"2"},"statistics":[{"name":"wonCorners","displayValue":"3"}]},{"team":{"id":"1"},"statistics":[{"name":"wonCorners","displayValue":"5"},{"name":"totalShots","displayValue":"8"}]}]}}
        r=parse_summary(p,f)
        self.assertEqual(r["metrics"],{"corners":[5,3]})
        self.assertEqual(r["score"],[2,1])
        self.assertEqual(r["clock"],"54'")
        with self.assertRaises(ValueError):parse_summary(p,dict(f,eventId="124"))
        bad=copy.deepcopy(p);bad["boxscore"]["teams"][0]["team"]["id"]="3"
        with self.assertRaises(ValueError):parse_summary(bad,f)
    def test_diverse_sample(self):
        def row(league,event,state="post",kickoff="2026-11-26T15:00:00+00:00"):
            return dict(league=league,eventId=event,state=state,kickoff=kickoff)
        rows=[row("a",str(i)) for i in range(10)]+[row("b","20"),row("c","30")]
        selected=select_candidates(rows,3)
        self.assertEqual({x["league"] for x in selected},{"a","b","c"})
        self.assertEqual(len(selected),3)
        self.assertEqual(select_candidates(rows+[row("a","live","in")],1)[0]["eventId"],"live")
        duplicate=row("d","40","in")
        self.assertNotIn("40",[x["eventId"] for x in select_candidates(rows+[duplicate,duplicate],12)])
        self.assertEqual(select_candidates(rows,0),[])
if __name__=="__main__":unittest.main()
