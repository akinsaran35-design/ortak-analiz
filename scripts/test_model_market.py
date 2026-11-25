import unittest
from datetime import datetime, timezone, timedelta
from model_market import compare_market

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
