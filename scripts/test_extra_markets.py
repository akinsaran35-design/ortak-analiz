
import json
import os
import runpy
import tempfile
import unittest
from pathlib import Path
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

MODULE = Path(__file__).resolve().with_name(
    "fetch_extra_markets.py"
)


class ExtraMarketsTests(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cwd = Path.cwd()
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(os.chdir, self.cwd)
        os.chdir(self.tmp.name)

        with patch.dict(os.environ, {"ODDS_API_KEY": ""}):
            self.module = runpy.run_path(str(MODULE))

        self.extract = self.module["extract_market"]
        self.now = datetime.now(timezone.utc)

    def book(self, key, age=0):
        stamp = (
            self.now - timedelta(seconds=age)
        ).isoformat()

        return {
            "key": key,
            "last_update": stamp,
            "markets": [
                {
                    "key": "alternate_totals",
                    "outcomes": [
                        {"name": "Over", "point": 1.5, "price": 1.4},
                        {"name": "Under", "point": 1.5, "price": 3.0},
                        {"name": "Over", "point": 2.5, "price": 2.1},
                        {"name": "Under", "point": 2.5, "price": 1.8}
                    ]
                },
                {
                    "key": "btts",
                    "outcomes": [
                        {"name": "Yes", "price": 1.9},
                        {"name": "No", "price": 1.9}
                    ]
                }
            ]
        }

    def test_over15(self):
        event = {"bookmakers": [self.book("a")]}
        rows = self.extract(
            event, "alternate_totals", ("Over", "Under")
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["prices"]["Over"], 1.4)
        self.assertEqual(rows[0]["prices"]["Under"], 3.0)

    def test_btts(self):
        event = {"bookmakers": [self.book("a")]}
        rows = self.extract(event, "btts", ("Yes", "No"))
        self.assertEqual(len(rows), 1)
        self.assertAlmostEqual(
            rows[0]["marketProbability"], 0.5
        )

    def test_stale_odds(self):
        event = {"bookmakers": [self.book("a", 1900)]}
        self.assertEqual(
            self.extract(event, "btts", ("Yes", "No")), []
        )

    def test_duplicate_bookmakers(self):
        event = {
            "bookmakers": [
                self.book("a"),
                self.book("a"),
                self.book("b"),
                self.book("c")
            ]
        }
        rows = self.extract(event, "btts", ("Yes", "No"))
        self.assertEqual(len(rows), 3)

    def test_missing_outcome(self):
        book = self.book("a")
        book["markets"][1]["outcomes"].pop()
        self.assertEqual(
            self.extract(
                {"bookmakers": [book]},
                "btts", ("Yes", "No")
            ), []
        )

    def test_quota_guard(self):
        run = self.module["run"]
        scope = run.__globals__

        snapshot = {
            "updatedAt": (
                scope["now"] - timedelta(seconds=1)
            ).isoformat(),
            "source": "The Odds API",
            "region": "uk",
            "errors": [],
            "events": [{
                "id": "test",
                "league": "soccer_epl",
                "home": "Team A",
                "away": "Team B",
                "kickoff": (
                    self.now + timedelta(hours=1)
                ).isoformat()
            }]
        }

        Path("odds.json").write_text(
            json.dumps(snapshot),
            encoding="utf-8"
        )

        scope["report"]["errors"] = []
        calls = []

        def fake_request(path, params):
            calls.append(path)
            scope["report"]["remainingCredits"] = 21
            return []

        with patch.dict(scope, {
            "key": "fake-test-key",
            "request": fake_request
        }):
            run()

        self.assertEqual(calls, ["sports/"])
        self.assertIn(
            "quota_guard", scope["report"]["errors"]
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
