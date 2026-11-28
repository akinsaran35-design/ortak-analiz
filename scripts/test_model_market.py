import unittest
from datetime import datetime, timezone, timedelta
from model_market import compare_market,bound_extra,candidate_matches,unique_events

class ModelMarketTests(unittest.TestCase):

    def setUp(self):
        self.now = datetime.now(timezone.utc)

        self.quotes = [
            {
                "bookmaker": name,
                "positive": 1.50,
                "negative": 2.70,
                "lastUpdate": self.now.isoformat()
            }
            for name in ["book1", "book2", "book3"]
        ]

    def test_valid_market(self):
        result = compare_market(
            0.80, self.quotes, self.now
        )
        self.assertIsNotNone(result)
        self.assertEqual(result["bookCount"], 3)
        self.assertAlmostEqual(
            result["estimatedEV"], 0.20
        )
        self.assertEqual(result["decision"], "PAS")

    def test_market_probability(self):
        result = compare_market(
            0.80, self.quotes, self.now
        )
        expected = (1 / 1.50) / (
            1 / 1.50 + 1 / 2.70
        )
        self.assertAlmostEqual(
            result["marketProbability"],
            expected,
            places=6
        )

    def test_insufficient_books(self):
        self.assertIsNone(
            compare_market(
                0.80, self.quotes[:2], self.now
            )
        )

    def test_duplicate_books(self):
        quotes = [self.quotes[0]] * 3
        self.assertIsNone(
            compare_market(0.80, quotes, self.now)
        )

    def test_conflicting_duplicate_book(self):
        self.assertIsNone(compare_market(.8,self.quotes+[dict(self.quotes[0],positive=1.6)],self.now))
    def test_extra_source_binding(self):
        stamp=self.now.isoformat()
        event=dict(id="e",league="soccer_epl",home="A",away="B",kickoff=(self.now+timedelta(hours=1)).isoformat())
        odds=dict(source="The Odds API",region="uk",market="totals",errors=[],updatedAt=stamp,events=[event])
        extra=dict(source="The Odds API",region="uk",mode="research_only",quotaPolicyVersion="6.89",oddsSnapshotAt=stamp,errors=[],updatedAt=stamp,events=[event])
        archive=dict(mode="research_only",integrityVersion="6.85",quarantine={},updatedAt=stamp)
        self.assertEqual(bound_extra(odds,extra,archive,self.now),{"e":event})
        self.assertEqual(bound_extra(odds,dict(extra,events=[dict(event,away="C")]),archive,self.now),{})
        self.assertEqual(bound_extra(odds,dict(extra,oddsSnapshotAt="old"),archive,self.now),{})
        self.assertEqual(bound_extra(odds,extra,dict(archive,quarantine={"e":{}}),self.now),{})
        self.assertEqual(unique_events([event,event]),{})
        c=dict(match="A – B",league="İngiltere Premier Lig",date=(self.now+timedelta(hours=4)).date().isoformat())
        self.assertTrue(candidate_matches(c,event))
        self.assertFalse(candidate_matches(dict(c,league="İngiltere Championship"),event))
    def test_stale_odds(self):
        self.quotes[0]["lastUpdate"] = (
            self.now - timedelta(minutes=31)
        ).isoformat()
        self.assertIsNone(
            compare_market(
                0.80, self.quotes, self.now
            )
        )

    def test_future_timestamp(self):
        self.quotes[0]["lastUpdate"] = (
            self.now + timedelta(minutes=1)
        ).isoformat()
        self.assertIsNone(
            compare_market(
                0.80, self.quotes, self.now
            )
        )

    def test_invalid_probability(self):
        for probability in [-0.1, 1.1, float("nan")]:
            self.assertIsNone(
                compare_market(
                    probability, self.quotes, self.now
                )
            )

    def test_invalid_odds(self):
        self.quotes[0]["positive"] = 1.0
        self.assertIsNone(
            compare_market(
                0.80, self.quotes, self.now
            )
        )

    def test_excessive_margin(self):
        self.quotes[0]["negative"] = 1.50
        self.assertIsNone(
            compare_market(
                0.80, self.quotes, self.now
            )
        )

if __name__ == "__main__":
    unittest.main(verbosity=2)
