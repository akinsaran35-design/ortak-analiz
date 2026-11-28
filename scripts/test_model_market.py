import unittest
from datetime import datetime, timezone, timedelta
from model_market import compare_market,unique_events,identity_matches,extra_bound,quotes_for

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

    def test_mixed_duplicate_rejected(self):
        self.assertIsNone(compare_market(.8,self.quotes+[dict(self.quotes[0])],self.now))
        self.assertIsNone(compare_market(True,self.quotes,self.now))
    def test_bound_extra_identity(self):
        stamp=self.now.isoformat()
        base=dict(id="a",league="soccer_epl",home="A",away="B",kickoff=(self.now+timedelta(hours=1)).isoformat())
        self.assertTrue(identity_matches(base,dict(base)))
        self.assertFalse(identity_matches(base,dict(base,away="C")))
        self.assertEqual(unique_events([base,base]),{})
        odds=dict(updatedAt=stamp)
        extra=dict(quotaPolicyVersion="6.89",integrityVersion="6.84",source="The Odds API",region="uk",mode="research_only",decision="PAS",errors=[],updatedAt=stamp,oddsSnapshotAt=stamp)
        archive=dict(integrityVersion="6.85",mode="research_only",quarantine={})
        self.assertTrue(extra_bound(extra,odds,archive,self.now))
        self.assertFalse(extra_bound(dict(extra,oddsSnapshotAt="wrong"),odds,archive,self.now))
        self.assertFalse(extra_bound(extra,odds,{},self.now))
    def test_base_over15_and_future_quote(self):
        stamp=self.now.isoformat()
        event=dict(bookmakers=[dict(key=q["bookmaker"],lines=[dict(point=1.5,over=q["positive"],under=q["negative"],lastUpdate=stamp)]) for q in self.quotes])
        self.assertEqual(len(quotes_for(event,"over15",stamp)),3)
        self.assertEqual(quotes_for(event,"over25",stamp),[])
        event["bookmakers"][0]["lines"][0]["lastUpdate"]=(self.now+timedelta(seconds=1)).isoformat()
        self.assertEqual(len(quotes_for(event,"over15",stamp)),2)
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
