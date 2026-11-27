import unittest
from chronological_statistics_research import replay,observations
def row(day,ht=(0,0),ft=(1,0),corners=(5,5),cards=(3,2)):
    return dict(date=day,home="a",away="b",score=list(ft),stats=dict(halfTimeGoals=list(ht),corners=list(corners),yellowCards=list(cards)))
class Tests(unittest.TestCase):
    def test_observations(self):
        x=observations(row("2026-01-01",(1,1),(2,2)))
        self.assertEqual(x["bothHalvesScoreBothTeams"],1)
        self.assertEqual(x["firstHalfGoal"],1)
        self.assertEqual(x["secondHalfGoal"],1)
    def test_same_day_no_leak(self):
        r=replay([row("2026-01-01") for _ in range(120)])
        self.assertEqual(r["firstHalfGoal"]["sample"],0)
    def test_later_day(self):
        r=replay([row("2026-01-01") for _ in range(100)]+[row("2026-01-02")])
        self.assertEqual(r["firstHalfGoal"]["sample"],1)
        self.assertAlmostEqual(r["firstHalfGoal"]["leagueBrier"],(1/102)**2)
        self.assertEqual(r["secondHalfGoal"]["observedEvents"],1)
    def test_reliability_and_season_counts(self):
        rows=[row("2025-06-29") for _ in range(100)]
        rows += [row("2025-06-30"),row("2025-07-01",(1,0),(2,0))]
        result=replay(rows)["firstHalfGoal"]
        self.assertEqual(result["sample"],2)
        self.assertEqual([v["season"] for v in result["seasonResults"]],[2024,2025])
        self.assertEqual(sum(v["sample"] for v in result["seasonResults"]),2)
        for method in ("league","venue"):
            diagnostic=result["reliability"][method]
            self.assertEqual(diagnostic["sample"],2)
            self.assertEqual(len(diagnostic["bins"]),10)
            self.assertEqual(sum(v["sample"] for v in diagnostic["bins"]),2)
            self.assertTrue(0<=diagnostic["weightedAbsoluteGap"]<=1)
    def test_empty_reliability(self):
        result=replay([])["firstHalfGoal"]
        self.assertIsNone(result["reliability"]["league"]["weightedAbsoluteGap"])
        self.assertEqual(result["seasonResults"],[])
    def test_missing_not_zero(self):
        x=row("2026-01-01");del x["stats"]["corners"]
        self.assertNotIn("totalCornersAtLeast10",observations(x))
        x["stats"]["halfTimeGoals"]=[9,0]
        self.assertNotIn("firstHalfGoal",observations(x))
if __name__=="__main__":unittest.main()
