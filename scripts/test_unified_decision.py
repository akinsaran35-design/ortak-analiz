import unittest
from datetime import datetime, timezone, timedelta
from unified_decision import build_report


class UnifiedDecisionTests(unittest.TestCase):

    def setUp(self):
        self.now = datetime(
            2026, 11, 25, 12, 0,
            tzinfo=timezone.utc
        )

        self.row = {
            "eventId": "event1",
            "match": "Team A – Team B",
            "kickoff": (
                self.now + timedelta(hours=2)
            ).isoformat(),
            "market": "over15",
            "modelProbabilityUncalibrated": 0.80,
            "marketProbability": 0.70,
            "bestOdds": 1.40,
            "bookCount": 4,
            "movementPP": 1.0,
            "movementBookmakers": 4
        }

        self.model = {
            "version": "4.12",
            "updatedAt": self.now.isoformat(),
            "modelCalibrated": False,
            "errors": [],
            "rows": [self.row]
        }

        self.quality = {
            "updatedAt": self.now.isoformat(),
            "qualityGate": "PASS",
            "status": "healthy",
            "errors": [],
            "warnings": []
        }

        self.validation = {
            "tested": 0,
            "liveEnabled": False,
            "errors": []
        }

    def report(self):
        return build_report(
            self.model,
            self.quality,
            self.validation,
            self.now
        )

    def test_research_candidate(self):
        r = self.report()
        self.assertEqual(
            len(r["researchCandidates"]), 1
        )
        self.assertEqual(r["decision"], "PAS")
        self.assertFalse(r["realBettingEnabled"])
        self.assertEqual(r["selections"], [])

    def test_low_probability(self):
        self.row["modelProbabilityUncalibrated"] = 0.60
        r = self.report()
        self.assertEqual(r["researchCandidates"], [])
        self.assertEqual(
            r["rejected"]["low_probability"], 1
        )

    def test_low_ev(self):
        self.row["bestOdds"] = 1.20
        r = self.report()
        self.assertEqual(
            r["rejected"]["low_ev"], 1
        )

    def test_insufficient_bookmakers(self):
        self.row["bookCount"] = 2
        r = self.report()
        self.assertEqual(
            r["rejected"]["insufficient_bookmakers"], 1
        )

    def test_negative_movement(self):
        self.row["movementPP"] = -4.0
        r = self.report()
        self.assertEqual(
            r["rejected"]["negative_market_movement"], 1
        )

    def test_stale_report(self):
        self.model["updatedAt"] = (
            self.now - timedelta(hours=1)
        ).isoformat()

        r = self.report()
        self.assertEqual(r["researchCandidates"], [])

    def test_quality_gate(self):
        self.quality["qualityGate"] = "PAS"
        r = self.report()
        self.assertEqual(r["researchCandidates"], [])

    def test_started_match(self):
        self.row["kickoff"] = (
            self.now - timedelta(minutes=1)
        ).isoformat()

        r = self.report()
        self.assertEqual(
            r["rejected"]["already_started"], 1
        )

    def test_duplicate_event(self):
        self.model["rows"].append(dict(self.row))
        r = self.report()
        self.assertEqual(
            len(r["researchCandidates"]), 1
        )

    def test_maximum_selections(self):
        self.model["rows"] = [
            dict(
                self.row,
                eventId=str(i),
                match=f"Home {i} – Away {i}"
            )
            for i in range(5)
        ]

        r = self.report()
        self.assertEqual(
            len(r["researchCandidates"]), 3
        )

    def test_real_betting_lock(self):
        self.validation["tested"] = 500
        self.validation["liveEnabled"] = True
        self.model["modelCalibrated"] = True

        r = self.report()
        self.assertFalse(r["realBettingEnabled"])
        self.assertEqual(r["decision"], "PAS")
        self.assertEqual(r["selections"], [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
