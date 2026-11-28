
import json
import os
import runpy
import tempfile
import unittest

from pathlib import Path
from datetime import datetime, timezone, timedelta

MODULE = Path(__file__).resolve().with_name(
    "archive_extra_markets.py"
)


class ArchiveTests(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cwd = Path.cwd()

        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(os.chdir, self.cwd)

        os.chdir(self.tmp.name)

        self.now = datetime.now(timezone.utc)
        self.run = runpy.run_path(str(MODULE))["run"]

    def snapshot(self, price=1.4, offset=0, stale=False):

        stamp = self.now + timedelta(seconds=offset)

        if stale:
            stamp -= timedelta(hours=2)

        report = {
            "source": "The Odds API",
            "region": "uk",
            "mode": "research_only",
            "errors": [],
            "updatedAt": stamp.isoformat(),
            "events": [{
                "id": "test-event",
                "league": "soccer_epl",
                "home": "Team A",
                "away": "Team B",
                "kickoff": (
                    self.now + timedelta(hours=2)
                ).isoformat(),
                "over15": [{
                    "bookmaker": "testbook",
                    "prices": {
                        "Over": price,
                        "Under": 3.0
                    },
                    "lastUpdate": stamp.isoformat()
                }],
                "btts": []
            }]
        }

        Path("extra_markets.json").write_text(
            json.dumps(report),
            encoding="utf-8"
        )

    def archive(self):
        return json.loads(
            Path("extra_market_archive.json").read_text()
        )

    def test_first_observation(self):
        self.snapshot()
        self.run()

        data = self.archive()
        self.assertEqual(data["recordCount"], 1)

        record = next(iter(data["records"].values()))

        self.assertFalse(record["movementReady"])
        self.assertEqual(record["oddsChangePct"], 0)

    def test_duplicate(self):
        self.snapshot()
        self.run()
        self.run()

        record = next(
            iter(self.archive()["records"].values())
        )

        self.assertEqual(len(record["history"]), 1)

    def test_movement(self):
        self.snapshot(1.4, -60)
        self.run()

        self.snapshot(1.3, -30)
        self.run()

        record = next(
            iter(self.archive()["records"].values())
        )

        self.assertTrue(record["movementReady"])
        self.assertEqual(len(record["history"]), 2)
        self.assertAlmostEqual(
            record["oddsChangePct"], -7.1429
        )

    def test_identity_conflict(self):
        self.snapshot()
        self.run()
        before=self.archive()["records"]
        self.snapshot(offset=-20)
        p=Path("extra_markets.json")
        r=json.loads(p.read_text())
        r["events"][0]["away"]="Other Team"
        p.write_text(json.dumps(r))
        self.run()
        self.assertEqual(self.archive()["records"],before)
        self.assertEqual(self.archive()["quarantine"]["test-event"]["reason"],"event_identity_conflict")
    def test_same_timestamp_conflict(self):
        self.snapshot()
        self.run()
        before=self.archive()["records"]
        self.snapshot(price=1.6)
        self.run()
        self.assertEqual(self.archive()["records"],before)
        self.assertEqual(self.archive()["quarantine"]["test-event"]["reason"],"same_timestamp_price_conflict")
    def test_duplicate_books_ignored(self):
        self.snapshot()
        p=Path("extra_markets.json")
        r=json.loads(p.read_text())
        r["events"][0]["over15"]*=2
        p.write_text(json.dumps(r))
        self.run()
        self.assertEqual(self.archive()["recordCount"],0)
    def test_stale_report(self):
        self.snapshot(stale=True)
        self.run()

        self.assertFalse(
            Path("extra_market_archive.json").exists()
        )

    def test_research_only(self):
        self.snapshot()
        self.run()

        self.assertEqual(
            self.archive()["decision"], "PAS"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
