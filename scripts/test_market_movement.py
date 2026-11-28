import json
import tempfile
import unittest
from pathlib import Path
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

import market_movement as engine


class MovementTests(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

        self.source = Path(self.tmp.name) / "archive.json"
        self.output = Path(self.tmp.name) / "movement.json"
        self.now = datetime.now(timezone.utc)

    def record(self, book, change, age=60, single=False):
        first = {
            "lastUpdate": (
                self.now - timedelta(hours=1)
            ).isoformat(),
            "marketProbability": 0.70
        }

        latest = {
            "lastUpdate": (
                self.now - timedelta(seconds=age)
            ).isoformat(),
            "marketProbability": 0.70 + change
        }

        for h in (first,latest):
            p=h["marketProbability"]
            h["prices"]={"Over":1/p,"Under":1/(1-p)}
            h["marketProbability"]=round(p,6)
            h["capturedAt"]=h["lastUpdate"]
        return {
            "league":"soccer_epl",
            "eventId": "test-event",
            "home": "Team A",
            "away": "Team B",
            "kickoff": (
                self.now + timedelta(hours=2)
            ).isoformat(),
            "market": "over15",
            "bookmaker": book,
            "history": (
                [first] if single else [first, latest]
            )
        }

    def analyse(self, records):
        self.source.write_text(json.dumps({
            "records": {
                ("|".join(r[k] for k in ("eventId","market","bookmaker")) if i==0 or not any(x["bookmaker"]==r["bookmaker"] for x in records[:i]) else "duplicate-"+str(i)): r
                for i, r in enumerate(records)
            }
        }))

        with patch.object(engine, "SOURCE", self.source):
            with patch.object(engine, "OUTPUT", self.output):
                engine.run()

        report = json.loads(self.output.read_text())
        self.assertEqual(report["decision"], "PAS")
        return report["markets"][0]

    def test_probability_up(self):
        row = self.analyse([
            self.record(b, 0.03)
            for b in ["a", "b", "c"]
        ])
        self.assertEqual(
            row["direction"], "PROBABILITY_UP"
        )

    def test_probability_down(self):
        row = self.analyse([
            self.record(b, -0.03)
            for b in ["a", "b", "c"]
        ])
        self.assertEqual(
            row["direction"], "PROBABILITY_DOWN"
        )

    def test_mixed(self):
        row = self.analyse([
            self.record("a", 0.03),
            self.record("b", -0.03),
            self.record("c", 0.00)
        ])
        self.assertEqual(
            row["direction"], "MIXED_OR_STABLE"
        )

    def test_insufficient(self):
        row = self.analyse([
            self.record("a", 0.03),
            self.record("b", 0.03)
        ])
        self.assertEqual(
            row["direction"], "INSUFFICIENT_DATA"
        )

    def test_stale(self):
        row = self.analyse([
            self.record(b, 0.03, age=1900)
            for b in ["a", "b", "c"]
        ])
        self.assertEqual(row["movementBookmakers"], 0)

    def test_single_observation(self):
        row = self.analyse([
            self.record(b, 0.03, single=True)
            for b in ["a", "b", "c"]
        ])
        self.assertEqual(row["movementBookmakers"], 0)

    def test_tampered_probability_and_duplicate_timestamp(self):
        a,b,c=[self.record(x,.03) for x in ("a","b","c")]
        a["history"][1]["marketProbability"]=.99
        b["history"][1]["lastUpdate"]=b["history"][0]["lastUpdate"]
        row=self.analyse([a,b,c])
        self.assertEqual(row["movementBookmakers"],1)
        self.assertEqual(row["direction"],"INSUFFICIENT_DATA")
    def test_duplicate_bookmakers(self):
        row = self.analyse([
            self.record("a", 0.03),
            self.record("a", 0.03),
            self.record("b", 0.03)
        ])
        self.assertEqual(row["movementBookmakers"], 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
